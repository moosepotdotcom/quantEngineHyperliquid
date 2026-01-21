#!/usr/bin/env python3
"""
PHASE 5: BACKTEST HYBRID MODEL V1
Tests new 86.3% WR model on Jan 2-11, 2026
Compares with current 71.4% WR model
"""

import sys
import os
sys.path.insert(0, '/Users/alifiyaa/Downloads/quantEngineHyperliquid/EXPORT')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("\n" + "="*70)
print("🚀 PHASE 5: BACKTEST HYBRID MODEL V1")
print("Period: Jan 2-11, 2026 | Threshold: 45% (86.3% WR)")
print("="*70)

# Load hybrid models
print("\n📦 Loading Hybrid V1 models...")

import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
import pickle

model_dir = '/Users/alifiyaa/Downloads/quantEngineHyperliquid/training/models/hybrid_v1'

xgb_model = xgb.XGBClassifier()
xgb_model.load_model(f'{model_dir}/xgb_hybrid.json')

lgb_model = lgb.Booster(model_file=f'{model_dir}/lgb_hybrid.txt')

cat_model = CatBoostClassifier()
cat_model.load_model(f'{model_dir}/cat_hybrid.cbm')

with open(f'{model_dir}/feature_names.pkl', 'rb') as f:
    feature_names = pickle.load(f)

print(f"✅ Models loaded ({len(feature_names)} features)")

# Load test data
print("\n📥 Loading Jan 2-11 data...")

from quant_engine import TradingEngine, add_all_indicators

engine = TradingEngine()
df_raw = engine.fetch_data('5m', 4000)

if df_raw is None:
    print("❌ Failed to fetch data")
    sys.exit(1)

df_raw.sort_values('timestamp', inplace=True)
df_5m = add_all_indicators(df_raw)

if 'timestamp' in df_5m.columns:
    df_5m.set_index('timestamp', inplace=True)

# Filter to Jan 2-11
mask = (df_5m.index >= '2026-01-02') & (df_5m.index <= '2026-01-11 23:59:59')
df_test = df_5m[mask].copy()

print(f"✅ Loaded {len(df_test)} candles")

# Prepare features
print("\n🔧 Preparing features...")

# Match training features
available_features = [f for f in feature_names if f in df_test.columns]
missing_features = [f for f in feature_names if f not in df_test.columns]

print(f"   Available: {len(available_features)}/{len(feature_names)}")
if missing_features:
    print(f"   Missing: {len(missing_features)} features")
    # Fill missing with zeros
    for f in missing_features:
        df_test[f] = 0

# Get features in correct order
X = df_test[feature_names].values
X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

print(f"   Shape: {X.shape}")

# Generate predictions
print("\n🤖 Generating predictions...")

proba_xgb = xgb_model.predict_proba(X)
proba_lgb = lgb_model.predict(X)

# Fix LightGBM shape if needed
if len(proba_lgb.shape) == 1:
    proba_lgb = proba_lgb.reshape(-1, 1)
    proba_lgb = np.hstack([1-proba_lgb, proba_lgb, np.zeros((len(proba_lgb), 1))])

proba_cat = cat_model.predict_proba(X)

# Ensemble
proba_ensemble = (proba_xgb + proba_lgb + proba_cat) / 3
predictions = np.argmax(proba_ensemble, axis=1)
confidences = np.max(proba_ensemble, axis=1)

print(f"✅ Predictions generated")

# Find signals at 45% threshold
threshold = 0.45
signal_mask = (confidences >= threshold) & (predictions != 0)
signal_indices = np.where(signal_mask)[0]

print(f"\n📊 Signals found: {len(signal_indices)} (threshold: {threshold*100:.0f}%)")

# Simulate trades
print("\n🔄 Simulating trades...")

tp_pct = 0.015  # 1.5%
sl_pct = 0.008  # 0.8%

trades = []
current_position = None

for i, (timestamp, row) in enumerate(df_test.iterrows()):
    # Check position
    if current_position is not None:
        h, l = row['high'], row['low']
        direction = current_position['dir']
        
        if direction == 'LONG':
            if h >= current_position['tp']:
                hold_hours = (timestamp - current_position['time']).total_seconds() / 3600
                trades.append({**current_position, 'outcome': 'WIN', 'hold_hours': hold_hours})
                print(f"   ✅ WIN: {current_position['time'].strftime('%m-%d %H:%M')} ({hold_hours:.1f}h)")
                current_position = None
                continue
            elif l <= current_position['sl']:
                hold_hours = (timestamp - current_position['time']).total_seconds() / 3600
                trades.append({**current_position, 'outcome': 'LOSS', 'hold_hours': hold_hours})
                print(f"   ❌ LOSS: {current_position['time'].strftime('%m-%d %H:%M')} ({hold_hours:.1f}h)")
                current_position = None
                continue
        continue
    
    # Check for signals
    if i in signal_indices:
        entry_price = row['close']
        direction = 'LONG' if predictions[i] == 1 else 'SHORT'
        
        tp_p = entry_price * (1+tp_pct) if direction == 'LONG' else entry_price * (1-tp_pct)
        sl_p = entry_price * (1-sl_pct) if direction == 'LONG' else entry_price * (1+sl_pct)
        
        current_position = {
            'time': timestamp,
            'dir': direction,
            'conf': confidences[i],
            'price': entry_price,
            'tp': tp_p,
            'sl': sl_p
        }
        
        print(f"\n   📍 {direction} @ ${entry_price:,.0f} | Conf: {confidences[i]:.1%}")

# Results
print("\n" + "="*70)
print("📊 BACKTEST RESULTS - HYBRID V1")
print("="*70)

if trades:
    wins = len([t for t in trades if t['outcome'] == 'WIN'])
    losses = len([t for t in trades if t['outcome'] == 'LOSS'])
    total = len(trades)
    win_rate = wins / total * 100
    avg_hold = sum([t['hold_hours'] for t in trades]) / total
    
    capital = 53
    leverage = 27
    buying_power = capital * leverage
    
    pnl_per_win = buying_power * tp_pct
    pnl_per_loss = buying_power * sl_pct
    
    total_pnl = (wins * pnl_per_win) - (losses * pnl_per_loss)
    roi = (total_pnl / capital) * 100
    
    print(f"\nTrades: {total}")
    print(f"Wins: {wins} | Losses: {losses}")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"Avg Hold: {avg_hold:.1f}h")
    print(f"\nP&L: ${total_pnl:+.2f}")
    print(f"ROI: {roi:+.1f}%")
    print(f"Final: ${capital + total_pnl:.2f}")
    
    print("\n" + "="*70)
    print("COMPARISON")
    print("="*70)
    print(f"{'Metric':<15} {'Current':<15} {'Hybrid V1':<15} {'Change':<15}")
    print("-"*70)
    print(f"{'Trades':<15} {'7':<15} {total:<15} {f'{total-7:+d}':<15}")
    print(f"{'Win Rate':<15} {'71.4%':<15} {f'{win_rate:.1f}%':<15} {f'{win_rate-71.4:+.1f}%':<15}")
    print(f"{'Avg Hold':<15} {'10h':<15} {f'{avg_hold:.1f}h':<15} {f'{avg_hold-10:.1f}h':<15}")
    print(f"{'ROI':<15} {'+159%':<15} {f'{roi:+.1f}%':<15} {f'{roi-159:+.1f}%':<15}")
    print(f"{'Final $':<15} {'$137':<15} {f'${capital+total_pnl:.0f}':<15} {f'${total_pnl-84:+.0f}':<15}")
    print("="*70)
    
    # Verdict
    if win_rate > 71.4 and total >= 7:
        print("\n🎉 HYBRID V1 IS BETTER!")
        print(f"   ✅ Higher win rate ({win_rate:.1f}% vs 71.4%)")
        if total > 7:
            print(f"   ✅ More trades ({total} vs 7)")
        if roi > 159:
            print(f"   ✅ Higher ROI ({roi:.1f}% vs 159%)")
        print("\n🚀 RECOMMENDATION: DEPLOY HYBRID V1!")
    elif win_rate > 71.4:
        print("\n✅ HYBRID V1 HAS BETTER WIN RATE")
        print(f"   But fewer trades ({total} vs 7)")
        print("\n💡 RECOMMENDATION: Test with lower threshold (40%)")
    else:
        print("\n⚠️  CURRENT MODEL STILL BETTER")
        print(f"   Stick with 71.4% WR model")
        
else:
    print("\n❌ No trades completed")

print("\n✅ PHASE 5 COMPLETE!")
