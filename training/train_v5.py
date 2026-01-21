
import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
import os
import sys
from datetime import datetime

# Add root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.v5_feature_engineer import generate_v5_features

def train_v5_model():
    print("🚀 Starting V5 (Order Flow) Training Pipeline...")
    
    # 1. Load Enriched Data
    data_path = 'training/data/BTC_5m_2025_enriched.csv'
    if not os.path.exists(data_path):
        print(f"❌ Data file not found: {data_path}")
        print("   Please wait for fetch_v5_history.py to finish.")
        return

    print("   📂 Loading Data...")
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # 2. Generate Features (V5)
    print("   🧠 Generating V5 Features (Volume Delta, CVD, Imbalance)...")
    df = generate_v5_features(df)
    
    # 3. Labeling (Method: Micro-Scalping 0.4% TP / 0.2% SL)
    print("   🏷️  Labeling Data (Micro-Scalp: 0.4% TP / 0.2% SL)...")
    lookahead = 36 # 3 hours max to hit target
    
    targets = []
    
    close_vals = df['close'].values
    high_vals = df['high'].values
    low_vals = df['low'].values
    
    for i in range(len(df) - lookahead):
        curr_p = close_vals[i]
        
        # Micro-Scalp Targets
        tp_long = curr_p * 1.004  # 0.4%
        sl_long = curr_p * 0.998  # 0.2%
        tp_short = curr_p * 0.996 # 0.4%
        sl_short = curr_p * 1.002 # 0.2%
        
        outcome = 0 # Neutral
        
        # Check Long
        for j in range(i+1, i+lookahead):
            if low_vals[j] <= sl_long:
                break # Hit SL
            if high_vals[j] >= tp_long:
                outcome = 1 # Long Win
                break
                
        # Check Short (if not Long win)
        if outcome == 0:
            for j in range(i+1, i+lookahead):
                if high_vals[j] >= sl_short:
                    break
                if low_vals[j] <= tp_short:
                    outcome = 2 # Short Win
                    break
        
        targets.append(outcome)
        
    # Pad end
    targets.extend([0] * lookahead)
    df['target'] = targets
    
    # Drop last rows
    df = df.iloc[:-lookahead]
    
    # DEBUG: Check Target Balance
    print("\n   🧐 Target Distribution:")
    print(df['target'].value_counts(normalize=True))
    print(f"   Total Long Wins (1): {sum(df['target'] == 1)}")
    print(f"   Total Short Wins (2): {sum(df['target'] == 2)}")
    print(f"   Total Neutral (0):   {sum(df['target'] == 0)}")
    
    if sum(df['target'] != 0) < 100:
        print("   ❌ CRITICAL WARNING: Almost no winning trades found. Check Labeling Logic!")
        return

    # 4. Train/Test Split (Time based)
    # Train: 2025-01-01 -> 2025-12-31
    # Test: 2026-01-01 -> Present
    split_date = '2026-01-01'
    train_df = df[df['timestamp'] < split_date]
    test_df = df[df['timestamp'] >= split_date]
    
    print(f"   📊 Train Set: {len(train_df)} rows")
    print(f"   📊 Test Set:  {len(test_df)} rows")
    
    # 5. Prepare XGBoost
    features = [c for c in df.columns if c not in ['timestamp', 'target', 'open', 'high', 'low', 'close', 'taker_buy_base', 'taker_sell_base']]
    # Note: excluding raw price/volume, keeping derivatives
    
    X_train = train_df[features]
    y_train = train_df['target']
    X_test = test_df[features]
    y_test = test_df['target']
    
    model = xgb.XGBClassifier(
        n_estimators=1000,
        learning_rate=0.03, # Lower LR for noisy micro-data
        max_depth=6,        # Slightly deeper to catch micro-patterns
        subsample=0.8,
        colsample_bytree=0.8,
        objective='multi:softprob',
        num_class=3,
        n_jobs=-1,
        early_stopping_rounds=50,
        eval_metric='mlogloss'
    )
    
    print("   🏋️  Training XGBoost (Micro-Scalper)...")
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=100
    )
    
    # 6. Evaluate
    print("\n   🔍 Evaluation (Jan 2026):")
    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)
    
    from sklearn.metrics import classification_report
    print(classification_report(y_test, preds))
    
    # Check High Confidence
    test_df = test_df.copy()
    test_df['conf_long'] = probs[:, 1]
    test_df['conf_short'] = probs[:, 2]
    
    # Check multiple thresholds
    for thresh in [0.5, 0.6, 0.7]:
        high_conf = test_df[ (test_df['conf_long'] > thresh) | (test_df['conf_short'] > thresh) ]
        
        wins = 0
        for _, row in high_conf.iterrows():
            if row['conf_long'] > thresh and row['target'] == 1: wins += 1
            elif row['conf_short'] > thresh and row['target'] == 2: wins += 1
        
        total = len(high_conf)
        wr = wins/total if total > 0 else 0
        print(f"   ✨ Thresh > {thresh}: {wr:.1%} ({wins}/{total} trades)")
    
    # 7. Save
    os.makedirs('model_engines/v5_orderflow/weights', exist_ok=True)
    joblib.dump(model, 'model_engines/v5_orderflow/weights/v5_micro_scalper.pkl')
    print("   💾 Model Saved: model_engines/v5_orderflow/weights/v5_micro_scalper.pkl")

if __name__ == "__main__":
    train_v5_model()
