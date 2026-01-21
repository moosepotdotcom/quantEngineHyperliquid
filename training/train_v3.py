
import os
import sys
import pandas as pd
import numpy as np
import joblib
import xgboost as xgb
from datetime import datetime
from sklearn.metrics import accuracy_score, precision_score, classification_report

# Add root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.fetch_data import fetch_live_data
from utils.mtf_feature_engineer import MTFFeatureGenerator

# CONFIG
START_DATE = "2026-01-02"
END_DATE = "2026-01-14"
SPLIT_DATE = "2026-01-09" # Train on 2-8, Test on 9-14

TP_PCT = 0.015  # 1.5%
SL_PCT = 0.008  # 0.8%

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                         'model_engines', 'mtf_scalper_v2', 'weights')

def label_data(df):
    """
    Triple Barrier Method: 
    1 = Long Win (Hit TP before SL)
    2 = Short Win (Hit TP before SL)
    0 = Neutral (Hit SL first or Time Limit)
    """
    labels = []
    prices = df['close'].values
    timestamps = df['timestamp'].values
    
    # Vectorized lookahead is hard with variable horizon. 
    # Using window loop for precision.
    
    lookahead = 288 # 24 hours max holding (5m bars)
    
    print(f"🏷️ Labeling {len(df)} rows (TP={TP_PCT}, SL={SL_PCT})...")
    
    for i in range(len(prices)):
        if i % 1000 == 0: print(f"   Row {i}...", end='\r')
            
        current_price = prices[i]
        label = 0 # Default Neutral
        
        # Window
        end_idx = min(i + lookahead, len(prices))
        window = prices[i+1 : end_idx]
        
        if len(window) == 0:
            labels.append(0)
            continue
            
        # Check Long
        # Hit TP?
        tp_price = current_price * (1 + TP_PCT)
        sl_price = current_price * (1 - SL_PCT)
        
        # First index where price >= tp
        hit_tp_idx = np.where(window >= tp_price)[0]
        hit_sl_idx = np.where(window <= sl_price)[0]
        
        first_tp = hit_tp_idx[0] if len(hit_tp_idx) > 0 else 99999
        first_sl = hit_sl_idx[0] if len(hit_sl_idx) > 0 else 99999
        
        if first_tp < first_sl:
            label = 1 # Long Win
        else:
            # Check Short
            # Short TP is Lower, SL is Higher
            tp_short = current_price * (1 - TP_PCT)
            sl_short = current_price * (1 + SL_PCT)
            
            hit_tp_s = np.where(window <= tp_short)[0]
            hit_sl_s = np.where(window >= sl_short)[0]
            
            first_tp_s = hit_tp_s[0] if len(hit_tp_s) > 0 else 99999
            first_sl_s = hit_sl_s[0] if len(hit_sl_s) > 0 else 99999
            
            if first_tp_s < first_sl_s:
                label = 2 # Short Win
                
        labels.append(label)
        
    df['label'] = labels
    return df

def train():
    print("🚀 Starting V3 Training Pipeline...")
    
    # 1. Fetch Data
    print("📥 Fetching Data...")
    df_store = {}
    timeframes = ['5m', '15m', '30m']
    limit = 6000 # Cover Jan 2-14
    
    for tf in timeframes:
        df = fetch_live_data("BTC", tf, limit=limit)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        # Filter Date range
        start_ts = pd.Timestamp(START_DATE).tz_localize('UTC')
        end_ts = pd.Timestamp(END_DATE).tz_localize('UTC') + pd.Timedelta(days=1)
        df = df[(df['timestamp'] >= start_ts) & (df['timestamp'] <= end_ts)]
        df_store[tf] = df.sort_values('timestamp').reset_index(drop=True)
        print(f"   ✅ {tf}: {len(df)} rows")
        
    # 2. Features
    print("🛠️ Generating MTF Features (231 cols)...")
    gen = MTFFeatureGenerator(df_store['5m'], df_store['15m'], df_store['30m'])
    X, price_df = gen.generate()
    
    # Align indices (Reset both to RangeIndex)
    X = X.reset_index(drop=True)
    price_df = price_df.reset_index() # Keep timestamp as column

    # Sanitize Features (Remove Inf)
    print("   Cleaning features (Inf/NaN)...")
    X = X.replace([np.inf, -np.inf], np.nan).fillna(0)
    # Or strict numpy
    # X_vals = np.nan_to_num(X.values, nan=0.0, posinf=0.0, neginf=0.0)
    # X = pd.DataFrame(X_vals, columns=X.columns)
    # Keeping it as DataFrame for column names in XGBoost importance?
    pass # pandas replace is safer for maintaining structure

    
    # 3. Labels
    # price_df already aligned (RangeIndex)
    labeled_df = label_data(price_df)
    y = labeled_df['label']
    
    # Align X and y (drop NaNs from feature gen)
    # X and price_df are already aligned by Generator (it handles dropna)
    # But label_data returns same length.
    
    # 4. Split Train/Test
    split_ts = pd.Timestamp(SPLIT_DATE).tz_localize('UTC')
    
    train_mask = labeled_df['timestamp'] < split_ts
    test_mask = labeled_df['timestamp'] >= split_ts
    
    X_train = X[train_mask]
    y_train = y[train_mask]
    X_test = X[test_mask]
    y_test = y[test_mask]
    
    print(f"\n📊 Split: Train={len(X_train)}, Test={len(X_test)}")
    print(f"   Train Dist: {y_train.value_counts().to_dict()}")
    
    # 5. Train
    print("🧠 Training XGBoost...")
    # Scale pos weight?
    # Class 0 dominating? Yes usually.
    # XGBClassifier handles multiclass.
    
    model = xgb.XGBClassifier(
        n_estimators=500,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        objective='multi:softprob',
        num_class=3,
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train, y_train, verbose=True)
    
    # 6. Evaluate
    print("\n🔍 Evaluation (Test Set):")
    preds = model.predict(X_test)
    print(classification_report(y_test, preds))
    
    # Check Precision of Class 1 and 2
    probs = model.predict_proba(X_test)
    
    # Threshold check
    thresh = 0.6
    print(f"\nExample High Conf Check (> {thresh}):")
    long_hits = (probs[:, 1] > thresh)
    short_hits = (probs[:, 2] > thresh)
    
    real_longs = y_test[long_hits]
    if len(real_longs) > 0:
        acc_l = (real_longs == 1).sum() / len(real_longs)
        print(f"   Longs > {thresh}: {len(real_longs)} trades, Acc: {acc_l:.2%}")
    else:
        print("   Longs: No trades")
        
    real_shorts = y_test[short_hits]
    if len(real_shorts) > 0:
        acc_s = (real_shorts == 2).sum() / len(real_shorts)
        print(f"   Shorts > {thresh}: {len(real_shorts)} trades, Acc: {acc_s:.2%}")
    else:
        print("   Shorts: No trades")

    # 7. Save
    save_path = os.path.join(MODEL_DIR, "mtf_scalper_v3.pkl")
    joblib.dump(model, save_path)
    print(f"\n💾 Model saved to: {save_path}")

if __name__ == "__main__":
    train()
