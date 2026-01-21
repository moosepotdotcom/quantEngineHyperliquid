#!/usr/bin/env python3
"""
Hybrid V1 Backtest on Jan 2-7 Hyperliquid Data
Fetches live data, calculates 231 MTF features, tests Hybrid V1 model
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
from feature_engineer import add_all_indicators

print("="*70)
print("🚀 HYBRID V1 - JAN 2-11 HYPERLIQUID BACKTEST")
print("With 231 MTF Features")
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

# Fetch 5m data (3000 candles = ~10 days)
print("   Fetching 5m data...")
df_5m_raw = engine.fetch_data('5m', 3000)

# Fetch 15m data  
print("   Fetching 15m data...")
df_15m_raw = engine.fetch_data('15m', 1000)

# Fetch 1h data
print("   Fetching 1h data...")
df_1h_raw = engine.fetch_data('1h', 300)

print(f"✅ Fetched: 5m={len(df_5m_raw)}, 15m={len(df_15m_raw)}, 1h={len(df_1h_raw)}")

# Calculate features for each timeframe
print("\n🔧 Calculating MTF features...")

print("   5m indicators...")
df_5m = add_all_indicators(df_5m_raw.copy())
if 'timestamp' in df_5m.columns:
    df_5m.set_index('timestamp', inplace=True)

print("   15m indicators...")
df_15m = add_all_indicators(df_15m_raw.copy())
if 'timestamp' in df_15m.columns:
    df_15m.set_index('timestamp', inplace=True)

print("   1h indicators...")
df_1h = add_all_indicators(df_1h_raw.copy())
if 'timestamp' in df_1h.columns:
    df_1h.set_index('timestamp', inplace=True)

# Merge MTF features
print("\n🔗 Merging timeframes...")

exclude = ['open', 'high', 'low', 'close', 'volume']

# 15m context
ctx_cols_15m = [c for c in df_15m.columns if c not in exclude]
df_15m_ctx = df_15m[ctx_cols_15m].copy()
df_15m_ctx.columns = [f"{c}_15m" for c in ctx_cols_15m]
df_15m_resampled = df_15m_ctx.reindex(df_5m.index, method='ffill')

# 1h context
ctx_cols_1h = [c for c in df_1h.columns if c not in exclude]
df_1h_ctx = df_1h[ctx_cols_1h].copy()
df_1h_ctx.columns = [f"{c}_1h" for c in ctx_cols_1h]
df_1h_resampled = df_1h_ctx.reindex(df_5m.index, method='ffill')

# Combine
df_mtf = pd.concat([df_5m, df_15m_resampled, df_1h_resampled], axis=1)
df_mtf.dropna(inplace=True)

print(f"✅ MTF features created: {len(df_mtf)} candles, {len(df_mtf.columns)} columns")

# Filter to Jan 2-11
df_mtf.reset_index(inplace=True)
mask = (df_mtf['timestamp'] >= '2026-01-02') & (df_mtf['timestamp'] <= '2026-01-11 23:59:59')
df_test = df_mtf[mask].copy()

print(f"\n📅 Jan 2-11 data: {len(df_test)} candles")

if len(df_test) == 0:
    print("⚠️  No Jan 2-11 data, using last 1728 candles")
    df_test = df_mtf.tail(1728).copy()

# Prepare features
print("\n🔧 Preparing features for prediction...")

# Fill missing features with 0
for f in features:
    if f not in df_test.columns:
        df_test[f] = 0

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

# Simulate trades
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
print("📊 RESULTS - HYBRID V1 ON JAN 2-11 LIVE DATA")
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
    
    if wr >= 75:
        print("\n🎉 EXCELLENT! Hybrid V1 works on live data!")
    elif wr >= 65:
        print("\n✅ GOOD! Hybrid V1 is viable")
    else:
        print("\n⚠️  Below target")
else:
    print("\n❌ No trades")

print("\n✅ BACKTEST COMPLETE!")
