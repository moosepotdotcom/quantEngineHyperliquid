
import os
import sys
import time
import pandas as pd
import numpy as np
import requests
import joblib
import xgboost as xgb
from datetime import datetime, timedelta
from sklearn.metrics import classification_report

# Add root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.mtf_feature_engineer import MTFFeatureGenerator
from utils.fetch_data import fetch_live_data

# CONFIG
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                         'model_engines', 'mtf_scalper_v3', 'weights') # Save to same dir for now or new?
                         # Plan said mtf_scalper_v4.pkl. Let's put it in V3 folder or create V4?
                         # Plan Phase 5 doesn't explicitly say create new engine folder, just model.
                         # I will save as mtf_scalper_v4.pkl in V3 folder for easy swapping.

START_DATE_TRAIN = "2025-01-01"
END_DATE_TRAIN = "2025-12-31"
START_DATE_TEST = "2026-01-02"
END_DATE_TEST = "2026-01-14"



# CONFIG
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                         'model_engines', 'mtf_scalper_v3', 'weights')

# Local Training Data (2022-2025)
TRAIN_DATA_PATH = os.path.join(os.path.dirname(__file__), 'data', 'BTC_5m_mtf_labeled.csv')

# Test Data period (Jan 2026)
START_DATE_TEST = "2026-01-01"
END_DATE_TEST = "2026-01-14"

def fetch_test_data(symbol="BTC", start_str=START_DATE_TEST, end_str=END_DATE_TEST):
    """Fetch Jan 2026 data for Out-of-Sample Testing"""
    print(f"   📥 Fetching Test Data ({start_str} to {end_str}) via API...")
    
    # We use simple fetch for this small period
    # Need 5m, 15m, 30m to generate features
    timeframes = ['5m', '15m', '30m']
    df_store = {}
    
    # Calculate limit roughly: 14 days * 24h * 12 (5m) = 4032 candles
    limit = 5000 
    
    from utils.fetch_data import fetch_live_data
    
    for tf in timeframes:
        df = fetch_live_data(symbol, tf, limit=limit)
        # Filter exact range
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        start_ts = pd.Timestamp(start_str).tz_localize('UTC')
        end_ts = pd.Timestamp(end_str).tz_localize('UTC') + pd.Timedelta(days=1)
        df = df[(df['timestamp'] >= start_ts) & (df['timestamp'] <= end_ts)]
        df_store[tf] = df.sort_values('timestamp').reset_index(drop=True)
        
    # Generate Features
    print("   🛠️ Generating Features for Test Set...")
    gen = MTFFeatureGenerator(df_store['5m'], df_store['15m'], df_store['30m'])
    X_test, price_df = gen.generate()
    
    # Sanitize
    X_test = X_test.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    # Label (Triple Barrier)
    # We need to implement label_data or import it.
    # Re-implementing simplified version
    y_test = label_data(price_df)['label']
        
    return X_test, y_test

def label_data(df):
    """Triple Barrier Labeling (TP=1.5%, SL=0.8%)"""
    labels = []
    prices = df['close'].values
    lookahead = 288 # 24h
    TP_PCT = 0.015
    SL_PCT = 0.008
    
    for i in range(len(prices)):
        current_price = prices[i]
        label = 0
        end_idx = min(i + lookahead, len(prices))
        window = prices[i+1 : end_idx]
        
        if len(window) == 0:
            labels.append(0)
            continue
            
        tp_price = current_price * (1 + TP_PCT)
        sl_price = current_price * (1 - SL_PCT)
        hit_tp = np.where(window >= tp_price)[0]
        hit_sl = np.where(window <= sl_price)[0]
        f_tp = hit_tp[0] if len(hit_tp)>0 else 99999
        f_sl = hit_sl[0] if len(hit_sl)>0 else 99999
        
        if f_tp < f_sl:
            label = 1
        else:
            tp_s = current_price * (1 - TP_PCT)
            sl_s = current_price * (1 + SL_PCT)
            hit_tp_s = np.where(window <= tp_s)[0]
            hit_sl_s = np.where(window >= sl_s)[0]
            f_tp_s = hit_tp_s[0] if len(hit_tp_s)>0 else 99999
            f_sl_s = hit_sl_s[0] if len(hit_sl_s)>0 else 99999
            if f_tp_s < f_sl_s:
                label = 2
        labels.append(label)
    df['label'] = labels
    return df

def load_local_training_data(path):
    print(f"   📂 Loading Local Data: {path} (1.5GB)...")
    
    # Use chunksize to avoid OOM and track progress
    chunk_size = 50000
    X_list = []
    y_list = []
    total_rows = 0
    
    try:
        print(f"      🔄 Processing in chunks of {chunk_size}...")
        label_col_idx = 237
        
        for i, chunk in enumerate(pd.read_csv(path, header=None, na_values=['inf', '-inf'], chunksize=chunk_size, low_memory=False)):
            
            # CLEANUP per chunk
            chunk = chunk[pd.to_numeric(chunk.iloc[:, label_col_idx], errors='coerce').notnull()]
            if chunk.empty: continue
            
            # Extract
            X_chunk = chunk.iloc[:, 6:237].astype(float)
            y_chunk = chunk.iloc[:, label_col_idx].astype(int)
            
            X_list.append(X_chunk)
            y_list.append(y_chunk)
            
            total_rows += len(chunk)
            print(f"         Chunk {i+1}: {total_rows} rows accumulated...", end='\\r')
            
        print(f"\n      ✅ Loaded & Cleaned Total: {total_rows} rows.")
        
        if not X_list: return None, None
        
        X = pd.concat(X_list, ignore_index=True)
        y = pd.concat(y_list, ignore_index=True)
              
        print(f"      X shape: {X.shape}, y shape: {y.shape}")
        
        # Sanitize just in case
        X = X.replace([np.inf, -np.inf], np.nan).fillna(0)
        
        return X, y
        
    except Exception as e:
        print(f"   ❌ Error loading local data: {e}")
        return None, None

def train_v4():
    print("🚀 Starting V4 (2025) Training Pipeline...")
    
    # 1. LOAD TRAIN (2022-2025)
    X_train, y_train = load_local_training_data(TRAIN_DATA_PATH)
    if X_train is None: return

    # 2. FETCH TEST (Jan 2026)
    X_test, y_test = fetch_test_data()
    
    # 3. ALIGN FEATURE NAMES
    print("   🔗 Aligning Feature Names...")
    if X_train.shape[1] == X_test.shape[1]:
        X_train.columns = X_test.columns
        print("      ✅ Applied feature names from Test Set to Train Set")
    else:
        print(f"      ❌ Feature count mismatch! Train: {X_train.shape[1]}, Test: {X_test.shape[1]}")
        return

    # 4. SAMPLE WEIGHTS
    print("⚖️ Calculating Sample Weights...")
    # Weigh good trades higher
    sample_weights = np.ones(len(y_train))
    sample_weights[y_train == 0] = 1.0
    sample_weights[y_train == 1] = 3.0 # Boost Longs
    sample_weights[y_train == 2] = 3.0 # Boost Shorts
    
    # 5. TRAINING
    print("🧠 Training V4 Model (XGBoost)...")
    # Using eval_set to show progress (Status Bar)
    print("      👉 Progress will be printed every 50 trees...")
    
    model = xgb.XGBClassifier(
        n_estimators=1000,
        max_depth=8,
        learning_rate=0.01,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        eval_metric='mlogloss'
    )
    
    model.fit(
        X_train, y_train, 
        sample_weight=sample_weights,
        eval_set=[(X_train, y_train), (X_test, y_test)],
        verbose=50
    )
    
    # 5. EVALUATION
    print("\n🔍 Evaluation (Jan 2026 Out-of-Sample):")
    preds = model.predict(X_test)
    print(classification_report(y_test, preds))
    
    # High Conf Check
    probs = model.predict_proba(X_test)
    thresh = 0.7
    print(f"   High Conf Check (> {thresh}):")
    
    longs = (probs[:,1] > thresh)
    if longs.sum() > 0:
        acc = (y_test[longs] == 1).sum() / longs.sum()
        print(f"      Longs: {longs.sum()} trades, Acc: {acc:.2%}")
    else: print("      Longs: 0 trades")
        
    shorts = (probs[:,2] > thresh)
    if shorts.sum() > 0:
        acc = (y_test[shorts] == 2).sum() / shorts.sum()
        print(f"      Shorts: {shorts.sum()} trades, Acc: {acc:.2%}")
    else: print("      Shorts: 0 trades")

    # 6. SAVE
    save_path = os.path.join(MODEL_DIR, "mtf_scalper_v4.pkl")
    joblib.dump(model, save_path)
    print(f"\n💾 Saved V4 Model to: {save_path}")

if __name__ == "__main__":
    train_v4()
