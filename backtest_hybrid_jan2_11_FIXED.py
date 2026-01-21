#!/usr/bin/env python3
"""
FIXED: Hybrid V1 Backtest on Jan 2-11
Uses proper MTF feature calculation (231 features)
"""

import sys
sys.path.insert(0, '/Users/alifiyaa/Downloads/quantEngineHyperliquid/EXPORT')
sys.path.insert(0, '/Users/alifiyaa/Downloads/quantEngineHyperliquid/utils')

import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
import pickle
from quant_engine import TradingEngine
from mtf_features import calculate_mtf_features_proper

print("="*70)
print("🚀 HYBRID V1 - JAN 2-11 BACKTEST (FIXED)")
print("With PROPER 231 MTF Features")
print("="*70)

# Load Hybrid V1 models
print("\n📦 Loading Hybrid V1 models...")
model_dir = '/Users/alifiyaa/Downloads/quantEngineHyperliquid/HYBRID_V1_EXPORT'

xgb_model = xgb.XGBClassifier()
xgb_model.load_model(f'{model_dir}/xgb_hybrid.json')

lgb_model = lgb.Booster(model_file=f'{model_dir}/lgb_hybrid.txt')

cat_model = CatBoostClassifier()
cat_model.load_model(f'{model_dir}/cat_hybrid.cbm')

with open(f'{model_dir}/feature_names.pkl', 'rb') as f:
    features = pickle.load(f)

print(f"✅ Models loaded ({len(features)} features)")

# Fetch data from Hyperliquid
print("\n📡 Fetching data from Hyperliquid...")

engine = TradingEngine()

df_5m = engine.fetch_data('5m', 5000)
df_15m = engine.fetch_data('15m', 2000)
df_1h = engine.fetch_data('1h', 600)

print(f"✅ Fetched: 5m={len(df_5m)}, 15m={len(df_15m)}, 1h={len(df_1h)}")

# Calculate MTF features properly
df_mtf = calculate_mtf_features_proper(df_5m, df_15m, df_1h)

# Filter to Jan 2-11
df_mtf.reset_index(inplace=True)
mask = (df_mtf['timestamp'] >= '2026-01-02') & (df_mtf['timestamp'] <= '2026-01-11 23:59:59')
df_test = df_mtf[mask].copy()

print(f"\n📅 Jan 2-11 data: {len(df_test)} candles")

# Prepare features
print("\n🔧 Preparing features...")

# Check for zero features
print("   Checking feature quality...")
exclude = ['open', 'high', 'low', 'close', 'volume']
cols = [c for c in df_test.columns if c not in exclude]
zeros = []
for c in cols:
    if (df_test[c] == 0).all():
        zeros.append(c)

if zeros:
    print(f"❌ WARNING: {len(zeros)} features are all zeros: {zeros}")
else:
    print("✅ Feature quality check passed: No zero-filled features")

X = df_test[features].values
X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

print(f"   Shape: {X.shape}")

# Generate predictions
print("\n🤖 Generating predictions...")

proba_xgb = xgb_model.predict_proba(X)
proba_lgb = lgb_model.predict(X)
proba_cat = cat_model.predict_proba(X)

proba_ensemble = (proba_xgb + proba_lgb + proba_cat) / 3
predictions = np.argmax(proba_ensemble, axis=1)
confidences = np.max(proba_ensemble, axis=1)

print(f"✅ Predictions generated")

# Find signals
threshold = 0.45
signal_mask = (confidences >= threshold) & (predictions != 0)
signal_count = np.sum(signal_mask)

print(f"\n📊 Signals: {signal_count} @ {threshold*100:.0f}% threshold ({signal_count/len(df_test)*100:.1f}%)")

# Simulate trades - ONE position at a time
print("\n🔄 Simulating trades (ONE position at a time)...")

tp_pct, sl_pct = 0.015, 0.008
trades, pos = [], None

for idx, row in df_test.iterrows():
    i = df_test.index.get_loc(idx)
    ts = row['timestamp']
    
    if pos:
        h, l = row['high'], row['low']
        if pos['dir'] == 'LONG':
            if h >= pos['tp']:
                ht = (ts - pos['time']).total_seconds() / 3600
                trades.append({'outcome': 'WIN', 'hold_hours': ht})
                print(f"   ✅ WIN: {pos['time'].strftime('%m-%d %H:%M')} ({ht:.1f}h)")
                pos = None
                continue
            elif l <= pos['sl']:
                ht = (ts - pos['time']).total_seconds() / 3600
                trades.append({'outcome': 'LOSS', 'hold_hours': ht})
                print(f"   ❌ LOSS: {pos['time'].strftime('%m-%d %H:%M')} ({ht:.1f}h)")
                pos = None
                continue
        elif pos['dir'] == 'SHORT':
            if l <= pos['tp']:
                ht = (ts - pos['time']).total_seconds() / 3600
                trades.append({'outcome': 'WIN', 'hold_hours': ht})
                print(f"   ✅ WIN: {pos['time'].strftime('%m-%d %H:%M')} ({ht:.1f}h)")
                pos = None
                continue
            elif h >= pos['sl']:
                ht = (ts - pos['time']).total_seconds() / 3600
                trades.append({'outcome': 'LOSS', 'hold_hours': ht})
                print(f"   ❌ LOSS: {pos['time'].strftime('%m-%d %H:%M')} ({ht:.1f}h)")
                pos = None
                continue
        continue
    
    if signal_mask[i]:
        ep = row['close']
        d = 'LONG' if predictions[i] == 1 else 'SHORT'
        tp_p = ep * (1+tp_pct) if d=='LONG' else ep * (1-tp_pct)
        sl_p = ep * (1-sl_pct) if d=='LONG' else ep * (1+sl_pct)
        pos = {'time': ts, 'dir': d, 'price': ep, 'tp': tp_p, 'sl': sl_p}
        print(f"\n   📍 {d} @ ${ep:,.0f} | Conf: {confidences[i]:.1%}")

# Results
print("\n" + "="*70)
print("📊 RESULTS - HYBRID V1 ON JAN 2-11 (FIXED)")
print("="*70)

if trades:
    w = len([t for t in trades if t['outcome']=='WIN'])
    l = len(trades) - w
    wr = w/len(trades)*100
    ah = sum([t['hold_hours'] for t in trades])/len(trades)
    
    cap, lev = 53, 27
    bp = cap * lev
    pnl = (w * bp * tp_pct) - (l * bp * sl_pct)
    roi = pnl/cap*100
    
    print(f"\nTrades: {len(trades)}")
    print(f"Wins: {w} | Losses: {l}")
    print(f"Win Rate: {wr:.1f}%")
    print(f"Avg Hold: {ah:.1f}h")
    print(f"\nP&L: ${pnl:+.2f}")
    print(f"ROI: {roi:+.1f}%")
    print(f"Final: ${cap+pnl:.2f}")
    
    print("\n" + "="*70)
    print("COMPARISON")
    print("="*70)
    print(f"{'Metric':<15} {'Current':<15} {'Hybrid V1':<15}")
    print("-"*70)
    print(f"{'Trades':<15} {'7':<15} {len(trades):<15}")
    print(f"{'Win Rate':<15} {'71.4%':<15} {f'{wr:.1f}%':<15}")
    print(f"{'ROI':<15} {'+159%':<15} {f'{roi:+.1f}%':<15}")
    print("="*70)
    
    if wr >= 70:
        print("\n🎉 EXCELLENT! Hybrid V1 works!")
    elif wr >= 60:
        print("\n✅ GOOD! Hybrid V1 is viable")
    else:
        print("\n⚠️  Below target")
else:
    print("\n❌ No trades")

print("\n✅ BACKTEST COMPLETE!")
