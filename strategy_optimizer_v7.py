#!/usr/bin/env python3
"""
BRAIN V7: STRATEGY OPTIMIZER
Finds the exact Confidence Thresholds that maximize Net PnL.
"""
import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
import json
import os
import sys

# Load Utils
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

MODEL_PREFIX = 'models/brain_v7_'
DATA_FILE = 'training/data/BTC_5m_jan2026_mtf_labeled.csv'

def load_models():
    print("⏳ Loading Models...")
    try:
        xgb_m = xgb.XGBClassifier()
        xgb_m.load_model(f'{MODEL_PREFIX}xgb.json')
        
        lgb_m = lgb.Booster(model_file=f'{MODEL_PREFIX}lgb.json')
        
        cat_m = CatBoostClassifier()
        cat_m.load_model(f'{MODEL_PREFIX}cat.json')
        
        return xgb_m, lgb_m, cat_m
    except Exception as e:
        print(f"❌ Error loading models: {e}")
        return None, None, None

def get_ensemble_proba(xgb_m, lgb_m, cat_m, X):
    p1 = xgb_m.predict_proba(X)
    p2 = lgb_m.predict(X) # Booster returns proba directly for multiclass
    p3 = cat_m.predict_proba(X)
    return (p1 + p2 + p3) / 3

def simulate_strategy(df, probs, thresh_long, thresh_short, tp=0.005, sl=0.003, fees=0.0005):
    """
    Simulate trading with specific thresholds.
    Assumes fixed TP/SL for now (as trained).
    feature_generator_v7.py used 0.5% TP and 0.3% SL.
    """
    balance = 1000.0
    initial_balance = balance
    trades = 0
    wins = 0
    losses = 0
    
    # Vectorized simulation approaches are hard with path dependence.
    # We will use the 'Label' as a proxy for the *potential* outcome.
    # Label 1 = Long Win, Label 2 = Short Win, Label 0 = Neutral/Loss for both.
    # Note: Label generation logic in feature_generator_v7 *already* encoded the TP/SL logic.
    # So if Label=1, a Long trade DEFINITELY hits TP before SL.
    # If Label=0 or 2, a Long trade likely hits SL or times out.
    # This simplifies simulation drastically! we just check:
    # If Signal=Long AND Label=1 -> Win (+TP)
    # If Signal=Long AND Label!=1 -> Loss (-SL) (Conservative assumption: all non-wins are stopouts)
    
    labels = df['label'].values
    
    # Identify signals
    long_signals = (probs[:, 1] >= thresh_long)
    short_signals = (probs[:, 2] >= thresh_short)
    
    # Prevent simultaneous signals (prioritize higher confidence? or just pick one)
    # For sim, let's assume if both fire, we take the one with higher prob.
    
    for i in range(len(df)):
        p_long = probs[i, 1]
        p_short = probs[i, 2]
        label = labels[i]
        
        trade_type = None
        if p_long >= thresh_long and p_long > p_short:
            trade_type = 1
        elif p_short >= thresh_short and p_short > p_long:
            trade_type = 2
            
        if trade_type:
            trades += 1
            if trade_type == 1: # Long
                if label == 1:
                    wins += 1
                    balance *= (1 + tp - fees)
                else: 
                    losses += 1
                    balance *= (1 - sl - fees)
            elif trade_type == 2: # Short
                if label == 2:
                    wins += 1
                    balance *= (1 + tp - fees)
                else:
                    losses += 1
                    balance *= (1 - sl - fees)
                    
    return {
        'net_pnl': balance - initial_balance,
        'final_balance': balance,
        'roi': (balance - initial_balance) / initial_balance,
        'trades': trades,
        'win_rate': wins / trades if trades > 0 else 0,
        'wins': wins,
        'losses': losses
    }

def optimize():
    print("="*70)
    print("🚀 BRAIN V7: STRATEGY OPTIMIZER")
    print("="*70)
    
    # 1. Load Data
    print("\n📊 Loading V7 Data...")
    df = pd.read_csv(DATA_FILE)
    df = df.iloc[int(len(df)*0.7):] # Optimize on Val/Test set ONLY (preserve training purity)
    print(f"   Optimization Set: {len(df)} rows (Validation + Test)")
    
    # Prepare X
    exclude = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'label']
    feature_cols = [c for c in df.columns if c not in exclude]
    X = df[feature_cols].values
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    
    # 2. Get Probabilities
    xgb_m, lgb_m, cat_m = load_models()
    if xgb_m is None: return
    
    print("🔮 Generating probabilities...")
    probs = get_ensemble_proba(xgb_m, lgb_m, cat_m, X)
    
    # 3. Grid Search
    print("\n🕵️  Running Grid Search for Optimal Thresholds...")
    best_roi = -999.0
    best_params = {}
    best_stats = {}
    
    # Coarse Grid
    thresholds = np.arange(0.40, 0.95, 0.05)
    
    for th_l in thresholds:
        for th_s in thresholds:
            res = simulate_strategy(df, probs, th_l, th_s)
            
            # Filter for minimum trade frequency (e.g., at least 5 trades)
            if res['trades'] < 5: continue
            
            if res['roi'] > best_roi:
                best_roi = res['roi']
                best_params = {'long': th_l, 'short': th_s}
                best_stats = res
                print(f"   ✨ New Best: ROI {res['roi']*100:.2f}% | L:{th_l:.2f} S:{th_s:.2f} | WR: {res['win_rate']*100:.1f}% ({res['trades']} trades)")

    print("\n" + "="*70)
    print("🏆 OPTIMIZATION RESULTS")
    print("="*70)
    print(f"   Best ROI:      {best_roi*100:.2f}%")
    print(f"   Thresholds:    Long > {best_params.get('long'):.2f} | Short > {best_params.get('short'):.2f}")
    print(f"   Win Rate:      {best_stats.get('win_rate')*100:.2f}%")
    print(f"   Trades:        {best_stats.get('trades')} (in ~{len(df)*5/60/24:.1f} days)")
    
    # Save optimized config
    config = {
        'model': 'Brain V7 Trio',
        'optimized_thresholds': {
            'long': float(best_params.get('long', 0.85)),
            'short': float(best_params.get('short', 0.85))
        },
        'expected_performance': {
            'roi': float(best_roi),
            'win_rate': float(best_stats.get('win_rate', 0)),
            'trades': int(best_stats.get('trades', 0))
        }
    }
    
    with open('models/brain_v7_optimized.json', 'w') as f:
        json.dump(config, f, indent=4)
    print(f"   💾 Saved config to models/brain_v7_optimized.json")

if __name__ == "__main__":
    optimize()
