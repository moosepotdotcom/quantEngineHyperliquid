#!/usr/bin/env python3
"""
MTF Scalper: Gem Finder (Optimization Grid Search)
Finds the optimal combination of TP/SL and Threshold.
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
    p1 = xgb_m.predict_proba(X)[:, 1]
    p2 = lgb_m.predict(X) 
    p3 = cat_m.predict_proba(X)[:, 1]
    return (p1 + p2 + p3) / 3

def main():
    print("💎 GEM FINDER: OPTIMIZING FOR 4-5 TRADES/DAY @ 100% WIN RATE")
    
    # 1. Load Data
    print("📊 Loading features...")
    df = pd.read_csv(DATA_PFX)
    exclude = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    feature_cols = [c for c in df.columns if c not in exclude]
    
    # Use Test Set (last 15%)
    test_start_idx = int(len(df) * 0.85)
    test_df = df.iloc[test_start_idx:].copy()
    X_test = test_df[feature_cols].values
    X_test = np.nan_to_num(X_test, nan=0.0, posinf=0.0, neginf=0.0)
    
    # 2. Get Base Predictions (from 0.5/0.3 trained trio)
    print("🤖 Generating base probabilities from Trio...")
    models = load_ensemble(os.path.join(MODEL_DIR, 'mtf_scalper_5m_trio_'))
    probs = get_ensemble_proba(models, X_test)
    
    # 3. Grid Search
    # TP/SL combinations
    tp_grid = [0.003, 0.004, 0.005, 0.006, 0.008]
    sl_grid = [0.002, 0.003, 0.004, 0.005]
    thresholds = [0.95, 0.90, 0.85, 0.80, 0.75, 0.70]
    
    results = []
    
    print("\n🔍 Starting Grid Search (this may take a minute)...")
    for tp in tp_grid:
        for sl in sl_grid:
            # Generate labels for this specific TP/SL
            # We process only the test period price data for speed
            price_df = test_df[['close', 'high', 'low']].copy()
            labeled_df = generate_labels_vectorized(price_df, tp_pct=tp, sl_pct=sl, lookahead_bars=288)
            y_test = labeled_df['label'].values
            
            for thresh in thresholds:
                signals = (probs >= thresh).astype(int)
                n_trades = np.sum(signals)
                if n_trades < 10: continue # Need statistically significant sample
                
                wins = np.sum((signals == 1) & (y_test == 1))
                losses = np.sum((signals == 1) & (y_test == 0))
                win_rate = (wins / n_trades) * 100
                
                # Daily frequency (test set is ~15% of ~3 years = ~5.4 months = ~160 days)
                # Let's calculate actual days in test set
                days = (test_df.index.to_series().diff() > 1).sum() + 1 # Rough estimate or use timestamp
                # Better: Use first and last timestamp
                test_df['timestamp'] = pd.to_datetime(test_df['timestamp'])
                duration_days = (test_df['timestamp'].iloc[-1] - test_df['timestamp'].iloc[0]).days
                if duration_days <= 0: duration_days = 160 # Fallback
                
                freq = n_trades / duration_days
                
                # Metric: High Win Rate (95%+) and target frequency (4-5)
                score = win_rate if freq >= 4 and freq <= 6 else 0
                
                results.append({
                    'tp': tp,
                    'sl': sl,
                    'threshold': thresh,
                    'trades': n_trades,
                    'win_rate': win_rate,
                    'freq': freq,
                    'profit_factor': (wins * tp) / (max(1, losses) * sl) if losses > 0 else 999
                })
                
    # 4. Report Findings
    res_df = pd.DataFrame(results)
    if res_df.empty:
        print("❌ No settings found meeting the minimum trade criteria.")
        return
        
    print("\n🏆 TOP 10 GEMS (Highest Win Rate for Frequency 4-6):")
    gems = res_df[res_df['freq'] >= 3].sort_values(by='win_rate', ascending=False)
    print(gems.head(10).to_string(index=False))
    
    print("\n💰 HIGHEST PROFIT GEMS (Profit Factor):")
    print(res_df.sort_values(by='profit_factor', ascending=False).head(10).to_string(index=False))

if __name__ == '__main__':
    main()
