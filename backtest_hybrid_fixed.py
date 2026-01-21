#!/usr/bin/env python3
"""
Step 3: Proper Backtest with Fixed Pipeline
Uses last 6 days of training data with all 231 features
"""

import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
import pickle

print("="*70)
print("🚀 HYBRID V1 BACKTEST - FIXED")
print("Using proper training data with 231 features")
print("="*70)

model_dir = '/Users/alifiyaa/Downloads/quantEngineHyperliquid/HYBRID_V1_EXPORT'

# Load models
print("\n📦 Loading models...")
xgb_model = xgb.XGBClassifier()
xgb_model.load_model(f'{model_dir}/xgb_hybrid.json')

lgb_model = lgb.Booster(model_file=f'{model_dir}/lgb_hybrid.txt')

cat_model = CatBoostClassifier()
cat_model.load_model(f'{model_dir}/cat_hybrid.cbm')

with open(f'{model_dir}/feature_names.pkl', 'rb') as f:
    features = pickle.load(f)

print(f"✅ Models loaded ({len(features)} features)")

# Load training data - last 1728 candles (6 days of 5m data)
print("\n📥 Loading training data...")
print("   Reading file (this may take a minute)...")

# Use chunksize to load efficiently
chunks = []
for chunk in pd.read_csv('/Users/alifiyaa/Downloads/quantEngineHyperliquid/training/data/BTC_5m_mtf_labeled.csv',
                          chunksize=50000):
    chunks.append(chunk)

df = pd.concat(chunks, ignore_index=True)

print(f"✅ Loaded {len(df):,} total candles")

# Get last 1728 candles
df_test = df.tail(1728).copy()
df_test['timestamp'] = pd.to_datetime(df_test['timestamp'])

print(f"\n🔬 Testing on last {len(df_test)} candles (~6 days)")
print(f"   From: {df_test['timestamp'].min()}")
print(f"   To: {df_test['timestamp'].max()}")

# Prepare features
print("\n🔧 Preparing features...")
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

# Find signals at 45% threshold
threshold = 0.45
signal_mask = (confidences >= threshold) & (predictions != 0)
signal_count = np.sum(signal_mask)

print(f"\n📊 Signals found: {signal_count} @ {threshold*100:.0f}% threshold")
print(f"   Signal rate: {signal_count/len(df_test)*100:.1f}%")

# Simulate trades - ONE position at a time
print("\n🔄 Simulating trades (ONE position at a time)...")

tp_pct = 0.015  # 1.5%
sl_pct = 0.008  # 0.8%

trades = []
current_position = None

for idx, row in df_test.iterrows():
    i = df_test.index.get_loc(idx)
    timestamp = row['timestamp']
    
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
        elif direction == 'SHORT':
            if l <= current_position['tp']:
                hold_hours = (timestamp - current_position['time']).total_seconds() / 3600
                trades.append({**current_position, 'outcome': 'WIN', 'hold_hours': hold_hours})
                print(f"   ✅ WIN: {current_position['time'].strftime('%m-%d %H:%M')} ({hold_hours:.1f}h)")
                current_position = None
                continue
            elif h >= current_position['sl']:
                hold_hours = (timestamp - current_position['time']).total_seconds() / 3600
                trades.append({**current_position, 'outcome': 'LOSS', 'hold_hours': hold_hours})
                print(f"   ❌ LOSS: {current_position['time'].strftime('%m-%d %H:%M')} ({hold_hours:.1f}h)")
                current_position = None
                continue
        continue
    
    # Check for signals
    if signal_mask[i]:
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
print("📊 BACKTEST RESULTS - HYBRID V1 (FIXED)")
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
    
    if win_rate >= 75:
        print("\n🎉 EXCELLENT! Hybrid V1 works!")
    elif win_rate >= 65:
        print("\n✅ GOOD! Hybrid V1 is viable")
    else:
        print("\n⚠️  Needs improvement")
        
else:
    print("\n❌ No trades completed")

print("\n✅ BACKTEST COMPLETE!")
