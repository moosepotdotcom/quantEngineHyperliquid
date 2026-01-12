#!/usr/bin/env python3
"""
Analyze the tradeoff between Win Rate and Trade Frequency
"""
import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
import json

def load_ensemble(prefix):
    xgb_model = xgb.XGBClassifier()
    xgb_model.load_model(f'{prefix}xgb.json')
    lgb_model = lgb.Booster(model_file=f'{prefix}lgb.json')
    cat_model = CatBoostClassifier()
    cat_model.load_model(f'{prefix}cat.json')
    return xgb_model, lgb_model, cat_model

def get_ensemble_proba(models, X):
    xgb_m, lgb_m, cat_m = models
    p1 = xgb_m.predict_proba(X)[:, 1]
    p2 = lgb_m.predict(X) 
    p3 = cat_m.predict_proba(X)[:, 1]
    return (p1 + p2 + p3) / 3

def main():
    print("📊 TRADEOFF ANALYSIS: WIN RATE VS FREQUENCY")
    
    # Load data
    df = pd.read_csv('training/data/BTC_5m_mtf_labeled.csv')
    exclude = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'label']
    feature_cols = [c for c in df.columns if c not in exclude]
    
    # Use Test Set
    test_start_idx = int(len(df) * 0.85)
    test_df = df.iloc[test_start_idx:].copy()
    X_test = test_df[feature_cols].values
    X_test = np.nan_to_num(X_test, nan=0.0, posinf=0.0, neginf=0.0)
    y_test = test_df['label'].values
    
    models = load_ensemble('training/models/mtf_scalper_5m_trio_')
    probs = get_ensemble_proba(models, X_test)
    
    # Sweep thresholds
    print("\n| Threshold | Trades | Win Rate | Est. Profit ($) |")
    print("| :--- | :--- | :--- | :--- |")
    
    for thresh in [0.95, 0.90, 0.85, 0.80, 0.75, 0.70, 0.65, 0.60, 0.55, 0.50, 0.45, 0.40]:
        signals = (probs >= thresh).astype(int)
        n_trades = np.sum(signals)
        if n_trades == 0: continue
        
        wins = np.sum((signals == 1) & (y_test == 1))
        losses = np.sum((signals == 1) & (y_test == 0))
        win_rate = (wins / n_trades) * 100
        
        # Estimate profit: 1.27 BTC pos, 0.5% TP, 0.3% SL, $95k BTC
        profit = (wins * 0.005 - losses * 0.003) * 1.27 * 95000
        
        # Format as bold if win rate is highlightable
        wr_str = f"**{win_rate:.1f}%**" if win_rate >= 90 else f"{win_rate:.1f}%"
        print(f"| {thresh:.2f} | {n_trades} | {wr_str} | ${profit:,.0f} |")

if __name__ == '__main__':
    main()
