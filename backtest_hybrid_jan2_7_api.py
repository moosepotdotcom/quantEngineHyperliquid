#!/usr/bin/env python3
"""
HYBRID V1 BACKTEST - Jan 2-7 from Hyperliquid API
Uses EXPORT engine to fetch data, then applies Hybrid V1 model
"""

import sys
sys.path.insert(0, '/Users/alifiyaa/Downloads/quantEngineHyperliquid/EXPORT')

import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
import pickle

print("\n" + "="*70)
print("🚀 HYBRID V1 BACKTEST - JAN 2-7, 2026")
print("Data: Hyperliquid API via EXPORT engine")
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
    feature_names = pickle.load(f)

print(f"✅ Models loaded ({len(feature_names)} features)")

# Fetch data using EXPORT engine
print("\n📡 Fetching Jan 2-7 data from Hyperliquid...")

from quant_engine import TradingEngine, add_all_indicators

engine = TradingEngine()

# Fetch 5m data
df_5m_raw = engine.fetch_data('5m', 2000)

if df_5m_raw is None:
    print("❌ Failed to fetch data from API")
    sys.exit(1)

print(f"✅ Fetched {len(df_5m_raw)} candles")

# Add indicators
print("\n🔧 Adding indicators...")
df_5m = add_all_indicators(df_5m_raw)

if 'timestamp' in df_5m.columns:
    df_5m.set_index('timestamp', inplace=True)

# Filter to Jan 2-7
mask = (df_5m.index >= '2026-01-02') & (df_5m.index <= '2026-01-07 23:59:59')
df_test = df_5m[mask].copy()

print(f"✅ Jan 2-7 data: {len(df_test)} candles")

if len(df_test) == 0:
    print("⚠️  No Jan 2-7 data available")
    print("   Using last 1728 candles instead (6 days)")
    df_test = df_5m.tail(1728).copy()

# Prepare features - fill missing with 0
print("\n🔧 Preparing features...")

for feat in feature_names:
    if feat not in df_test.columns:
        df_test[feat] = 0

X = df_test[feature_names].values
X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

print(f"   Shape: {X.shape}")

# Generate predictions
print("\n🤖 Generating predictions...")

proba_xgb = xgb_model.predict_proba(X)
proba_lgb = lgb_model.predict(X)
proba_cat = cat_model.predict_proba(X)

# Fix LGB shape
if len(proba_lgb.shape) == 1:
    proba_lgb = np.column_stack([1-proba_lgb, proba_lgb, np.zeros(len(proba_lgb))])

proba_ensemble = (proba_xgb + proba_lgb + proba_cat) / 3
predictions = np.argmax(proba_ensemble, axis=1)
confidences = np.max(proba_ensemble, axis=1)

print(f"✅ Predictions generated")

# Find signals at 45% threshold
threshold = 0.45
signal_mask = (confidences >= threshold) & (predictions != 0)
signal_count = np.sum(signal_mask)

print(f"\n📊 Signals found: {signal_count} @ {threshold*100:.0f}% threshold")

# Simulate trades - ONE position at a time
print("\n🔄 Simulating trades (ONE position at a time)...")

tp_pct = 0.015  # 1.5%
sl_pct = 0.008  # 0.8%

trades = []
current_position = None

for timestamp, row in df_test.iterrows():
    idx = df_test.index.get_loc(timestamp)
    
    # Check open position
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
    if signal_mask[idx]:
        entry_price = row['close']
        direction = 'LONG' if predictions[idx] == 1 else 'SHORT'
        
        tp_p = entry_price * (1+tp_pct) if direction == 'LONG' else entry_price * (1-tp_pct)
        sl_p = entry_price * (1-sl_pct) if direction == 'LONG' else entry_price * (1+sl_pct)
        
        current_position = {
            'time': timestamp,
            'dir': direction,
            'conf': confidences[idx],
            'price': entry_price,
            'tp': tp_p,
            'sl': sl_p
        }
        
        print(f"\n   📍 {direction} @ ${entry_price:,.0f} | Conf: {confidences[idx]:.1%}")

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
    print(f"{'Metric':<15} {'Current':<15} {'Hybrid V1':<15}")
    print("-"*70)
    print(f"{'Trades':<15} {'7':<15} {total:<15}")
    print(f"{'Win Rate':<15} {'71.4%':<15} {f'{win_rate:.1f}%':<15}")
    print(f"{'ROI':<15} {'+159%':<15} {f'{roi:+.1f}%':<15}")
    print("="*70)
    
else:
    print("\n❌ No trades completed")

print("\n✅ BACKTEST COMPLETE!")
