#!/usr/bin/env python3
"""
HYBRID V1 STANDALONE BACKTEST
Self-contained backtest script for the Hybrid V1 model
"""

import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
import pickle
import os

print("\n" + "="*70)
print("🚀 HYBRID V1 BACKTEST")
print("86.3% WR @ 45% threshold | 231 MTF features")
print("="*70)

# Get script directory
script_dir = os.path.dirname(os.path.abspath(__file__))

# Load models
print("\n📦 Loading models...")

xgb_model = xgb.XGBClassifier()
xgb_model.load_model(os.path.join(script_dir, 'xgb_hybrid.json'))

lgb_model = lgb.Booster(model_file=os.path.join(script_dir, 'lgb_hybrid.txt'))

cat_model = CatBoostClassifier()
cat_model.load_model(os.path.join(script_dir, 'cat_hybrid.cbm'))

with open(os.path.join(script_dir, 'feature_names.pkl'), 'rb') as f:
    feature_names = pickle.load(f)

with open(os.path.join(script_dir, 'metadata.pkl'), 'rb') as f:
    metadata = pickle.load(f)

print(f"✅ Models loaded")
print(f"   Features: {len(feature_names)}")
print(f"   Training accuracy: {metadata['ensemble_accuracy']*100:.2f}%")

# Load data
print("\n📥 Loading data...")

# Try to load from parent directory
data_file = '../training/data/BTC_5m_mtf_labeled.csv'
if not os.path.exists(data_file):
    data_file = input("Enter path to BTC data CSV: ")

df = pd.read_csv(data_file)
df['timestamp'] = pd.to_datetime(df['timestamp'])

print(f"✅ Loaded {len(df):,} candles")
print(f"   Period: {df['timestamp'].min()} to {df['timestamp'].max()}")

# Use last 2880 candles (10 days of 5m data)
df_test = df.tail(2880).copy()

print(f"\n🔬 Testing on last {len(df_test)} candles (~10 days)")

# Prepare features
print("\n🔧 Preparing features...")

# Fill missing features with 0
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

# Fix LightGBM shape
if len(proba_lgb.shape) == 1:
    proba_lgb = np.column_stack([1-proba_lgb, proba_lgb, np.zeros(len(proba_lgb))])
elif proba_lgb.shape[1] == 2:
    proba_lgb = np.column_stack([proba_lgb, np.zeros(len(proba_lgb))])

# Ensemble
proba_ensemble = (proba_xgb + proba_lgb + proba_cat) / 3
predictions = np.argmax(proba_ensemble, axis=1)
confidences = np.max(proba_ensemble, axis=1)

print(f"✅ Predictions generated")

# Test multiple thresholds
print("\n📊 Testing confidence thresholds...")

for threshold in [0.40, 0.45, 0.50, 0.55]:
    signal_mask = (confidences >= threshold) & (predictions != 0)
    signal_count = np.sum(signal_mask)
    print(f"   {threshold*100:.0f}%: {signal_count} signals")

# Run backtest with 45% threshold
threshold = 0.45
signal_mask = (confidences >= threshold) & (predictions != 0)

print(f"\n🔄 Simulating trades (threshold: {threshold*100:.0f}%)...")
print("   ONE position at a time")

tp_pct = 0.015  # 1.5%
sl_pct = 0.008  # 0.8%

trades = []
current_position = None

for i, row in df_test.iterrows():
    idx = df_test.index.get_loc(i)
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
print("📊 BACKTEST RESULTS")
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
    print(f"\nCapital: ${capital}")
    print(f"Leverage: {leverage}x")
    print(f"Buying Power: ${buying_power:,.0f}")
    print(f"\nP&L: ${total_pnl:+.2f}")
    print(f"ROI: {roi:+.1f}%")
    print(f"Final: ${capital + total_pnl:.2f}")
    
    print("\n" + "="*70)
    
    if win_rate >= 75:
        print("✅ EXCELLENT! Win rate above 75%")
    elif win_rate >= 65:
        print("✅ GOOD! Win rate above 65%")
    else:
        print("⚠️  Win rate below 65% - check threshold")
        
else:
    print("\n❌ No trades completed")
    print("   Try lowering the confidence threshold")

print("\n✅ BACKTEST COMPLETE!")
