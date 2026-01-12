
import sys
import os
import pandas as pd
import numpy as np
import xgboost as xgb
import backtrader as bt

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from research.mtf_feature_engineer import MTFFeatureGenerator

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
MODELS_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')

def load_data(timeframe):
    path = os.path.join(DATA_DIR, f'BTC_{timeframe}.csv')
    if not os.path.exists(path):
        print(f"❌ Missing {path}")
        return None
    df = pd.read_csv(path)
    if 'timestamp' in df.columns:
        df['datetime'] = pd.to_datetime(df['timestamp'])
        df.set_index('datetime', inplace=True)
    return df

def train_mtf_scalper():
    print("🧠 Training MTF AI Scalper Model...")
    
    # 1. Load Data
    df_15m = load_data('15m') # Base
    df_1h = load_data('1h')   # Context 1
    df_4h = load_data('4h')   # Context 2
    
    if df_15m is None or df_1h is None or df_4h is None:
        print("❌ Data missing. Run fetch_mtf_data.py")
        return

    # 2. Feature Engineering (Merge Timeframes)
    print("⚙️ Generating MTF Features...")
    # Use 1h and 4h as context for 15m
    # The generator expects 5m, 15m, 30m but we will map:
    # 5m input -> 15m (Base)
    # 15m input -> 1h (Context 1)
    # 30m input -> 4h (Context 2)
    # We cheat the class naming convention slightly
    
    generator = MTFFeatureGenerator(
        df_5m=df_15m,
        df_15m=df_1h,
        df_30m=df_4h
    )
    
    # This returns columns like rsi_5m (actually 15m), rsi_15m (actually 1h), etc.
    # We will rename them later for clarity if needed, but for model training, names don't matter as long as consistent.
    df_final = generator.generate()
    
    # 3. Create Targets (Labels)
    # Definition of a Good Scalp: +1.5% gain within 12 bars (3 hours) without hitting -1.0% loss
    
    print("🏷️ Labeling Data...")
    lookahead = 12
    tp_pct = 0.015
    sl_pct = 0.010
    
    labels = []
    
    # Vectorized labeling (faster) would be better, but loop is clearer logic
    closes = df_final['close'].values
    highs = df_final['high'].values
    lows = df_final['low'].values
    
    for i in range(len(df_final) - lookahead):
        current_close = closes[i]
        target_price = current_close * (1 + tp_pct)
        stop_price = current_close * (1 - sl_pct)
        
        outcome = 0 # default fail
        
        for j in range(1, lookahead + 1):
            future_high = highs[i+j]
            future_low = lows[i+j]
            
            if future_low <= stop_price:
                outcome = 0 # Hit SL first
                break
            if future_high >= target_price:
                outcome = 1 # Hit TP
                break
                
        labels.append(outcome)
        
    # Trim dataframe to match labels
    df_train = df_final.iloc[:-lookahead].copy()
    df_train['target'] = labels
    
    # 4. Train Model
    features = [c for c in df_train.columns if c not in ['open','high','low','close','volume','target','datetime','timestamp']]
    X = df_train[features]
    y = df_train['target']
    
    print(f"📊 Dataset: {len(X)} rows. Win Rate: {y.mean():.2%}")
    
    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric='logloss'
    )
    
    # Time-series split manually (train on first 80%, test on last 20%)
    split = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]
    
    model.fit(X_train, y_train)
    
    # Eval
    score_train = model.score(X_train, y_train)
    score_test = model.score(X_test, y_test)
    print(f"🎯 Train Acc: {score_train:.2%} | Test Acc: {score_test:.2%}")
    
    # Save
    model_path = os.path.join(MODELS_DIR, 'scalp_mtf_v2_xgb.json')
    model.save_model(model_path)
    print(f"✅ Model saved to {model_path}")

if __name__ == '__main__':
    train_mtf_scalper()
