#!/usr/bin/env python3
"""
MTF Scalper: Gem Trade Visualizer
Extracts and displays detailed historical examples of "Gem" trades.
"""
import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
import os
import sys

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'training'))
from training.label_generator_fast import generate_labels_vectorized

MODEL_DIR = 'training/models/'
DATA_PFX = 'training/data/BTC_5m_mtf_features.csv'

def load_ensemble(prefix):
    xgb_model = xgb.XGBClassifier()
    xgb_model.load_model(f'{prefix}xgb.json')
    lgb_model = lgb.Booster(model_file=f'{prefix}lgb.json')
    cat_model = CatBoostClassifier()
    cat_model.load_model(f'{prefix}cat.json')
    return xgb_model, lgb_model, cat_model

def get_ensemble_proba(models, X):
    xgb_m, lgb_m, cat_m = models
    p1 = xgb_m.predict_proba(X)[:,1]
    p2 = lgb_m.predict(X) 
    p3 = cat_m.predict_proba(X)[:,1]
    return (p1 + p2 + p3) / 3

def main():
    print("💎 GEM TRADE VISUALIZER: EXTRACTING HISTORICAL WINS")
    print("="*70)
    
    # 1. Load Data
    print("📊 Loading data...")
    df = pd.read_csv(DATA_PFX)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    exclude = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    feature_cols = [c for c in df.columns if c not in exclude]
    
    # 2. Use Test Set (last 15%)
    test_start_idx = int(len(df) * 0.85)
    test_df = df.iloc[test_start_idx:].reset_index(drop=True)
    X_test = test_df[feature_cols].values
    X_test = np.nan_to_num(X_test, nan=0.0, posinf=0.0, neginf=0.0)
    
    # 3. Get Probabilities
    print("🤖 Analyzing market with Trio Ensemble...")
    models = load_ensemble(os.path.join(MODEL_DIR, 'mtf_scalper_5m_trio_'))
    probs = get_ensemble_proba(models, X_test)
    
    # 4. Gem Configuration (0.3% TP / 0.5% SL / 0.90 Threshold)
    tp_pct = 0.003
    sl_pct = 0.005
    threshold = 0.90
    
    signals_idx = np.where(probs >= threshold)[0]
    print(f"🎯 Found {len(signals_idx)} signals at {threshold:.2f} threshold")
    
    # 5. Simulate Outcomes & Log Detail
    trades = []
    
    # Take a few representative examples from the test set
    for idx in signals_idx[:10]: # First 10 examples
        entry_price = test_df.iloc[idx]['close']
        entry_time = test_df.iloc[idx]['timestamp']
        tp_price = entry_price * (1 + tp_pct)
        sl_price = entry_price * (1 - sl_pct)
        
        # Lookahead search
        outcome = "OPEN"
        exit_time = None
        exit_price = None
        
        # Look ahead up to 288 bars (24 hours)
        for j in range(idx + 1, min(idx + 288, len(test_df))):
            high = test_df.iloc[j]['high']
            low = test_df.iloc[j]['low']
            
            # Check TP first
            if high >= tp_price:
                outcome = "WIN"
                exit_price = tp_price
                exit_time = test_df.iloc[j]['timestamp']
                break
            # Check SL
            if low <= sl_price:
                outcome = "LOSS"
                exit_price = sl_price
                exit_time = test_df.iloc[j]['timestamp']
                break
        
        duration = (exit_time - entry_time).total_seconds() / 60 if exit_time else 0
        
        trades.append({
            'Entry Time': entry_time,
            'Entry Price': entry_price,
            'TP Level': tp_price,
            'SL Level': sl_price,
            'Outcome': outcome,
            'Exit Price': exit_price,
            'Duration (m)': duration,
            'Confidence': probs[idx]
        })
    
    # 6. Display Results
    print("\n🏆 GEM TRADE EXAMPLES (0.3% TP / 0.5% SL / 0.90 Threshold)")
    print("="*70)
    
    for i, t in enumerate(trades):
        emoji = "✅" if t['Outcome'] == "WIN" else "❌" if t['Outcome'] == "LOSS" else "⏳"
        print(f"\n{emoji} TRADE #{i+1}:")
        print(f"   📅 Entry: {t['Entry Time']}")
        print(f"   🎯 Entry Price: ${t['Entry Price']:,.2f}")
        print(f"   ✅ Take Profit: ${t['TP Level']:,.2f} (+0.3%)")
        print(f"   ❌ Stop Loss:   ${t['SL Level']:,.2f} (-0.5%)")
        print(f"   🏁 Exit Price:  ${t['Exit Price']:,.2f}")
        print(f"   ⏱️  Duration:   {t['Duration (m)']:.1f} minutes")
        print(f"   📊 Confidence: {t['Confidence']:.2%}")

if __name__ == '__main__':
    main()
