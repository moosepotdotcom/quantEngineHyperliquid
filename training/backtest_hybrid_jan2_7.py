#!/usr/bin/env python3
"""
HYBRID V1 BACKTEST - Jan 2-7, 2026
Fetches LIVE data from Hyperliquid API
ONE position at a time (proper position management)
"""

import pandas as pd
import numpy as np
from datetime import datetime
import requests
import warnings
warnings.filterwarnings('ignore')

print("\n" + "="*70)
print("🚀 HYBRID V1 BACKTEST - JAN 2-7, 2026")
print("Data: Hyperliquid API | ONE position at a time")
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

# Fetch Jan 2-7 data from Hyperliquid
print("\n📡 Fetching Jan 2-7 data from Hyperliquid API...")

url = 'https://api.hyperliquid.xyz/info'

start_dt = datetime(2026, 1, 2)
end_dt = datetime(2026, 1, 8)  # Up to Jan 7 23:59

start_time = int(start_dt.timestamp() * 1000)
end_time = int(end_dt.timestamp() * 1000)

payload = {
    'type': 'candleSnapshot',
    'req': {
        'coin': 'BTC',
        'interval': '5m',
        'startTime': start_time,
        'endTime': end_time
    }
}

try:
    resp = requests.post(url, json=payload, timeout=30)
    data = resp.json()
    
    df_data = []
    for candle in data:
        df_data.append({
            'timestamp': pd.to_datetime(candle['t'], unit='ms'),
            'open': float(candle['o']),
            'high': float(candle['h']),
            'low': float(candle['l']),
            'close': float(candle['c']),
            'volume': float(candle['v'])
        })
    
    df = pd.DataFrame(df_data)
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    print(f"✅ Fetched {len(df)} candles")
    print(f"   Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
except Exception as e:
    print(f"❌ API Error: {e}")
    import sys
    sys.exit(1)

# Add simple indicators (match training features as much as possible)
print("\n🔧 Adding indicators...")

# Basic indicators
df['sma_10'] = df['close'].rolling(10).mean()
df['sma_20'] = df['close'].rolling(20).mean()
df['sma_50'] = df['close'].rolling(50).mean()
df['ema_10'] = df['close'].ewm(span=10).mean()
df['ema_20'] = df['close'].ewm(span=20).mean()

# RSI
delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
df['rsi_14'] = 100 - (100 / (1 + rs))

# More indicators
df['atr_14'] = (df['high'] - df['low']).rolling(14).mean()
df['volatility'] = df['close'].pct_change().rolling(20).std()
df['price_change'] = df['close'].pct_change()
df['volume_sma'] = df['volume'].rolling(20).mean()
df['volume_ratio'] = df['volume'] / df['volume_sma']
df['momentum_5'] = df['close'] / df['close'].shift(5) - 1
df['momentum_10'] = df['close'] / df['close'].shift(10) - 1

# Fill missing features with zeros
for feat in feature_names:
    if feat not in df.columns:
        df[feat] = 0

df = df.dropna()

print(f"✅ Indicators added ({len(df)} clean candles)")

# Prepare features
print("\n🤖 Generating predictions...")

X = df[feature_names].values
X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

proba_xgb = xgb_model.predict_proba(X)
proba_lgb = lgb_model.predict(X)  # Booster uses predict, not predict_proba
proba_cat = cat_model.predict_proba(X)

# Fix LightGBM output shape if needed
if len(proba_lgb.shape) == 2 and proba_lgb.shape[1] == 3:
    pass  # Already correct shape
else:
    # Reshape to match XGB/CAT output
    proba_lgb = np.column_stack([1-proba_lgb, proba_lgb, np.zeros(len(proba_lgb))])

proba_ensemble = (proba_xgb + proba_lgb + proba_cat) / 3
predictions = np.argmax(proba_ensemble, axis=1)
confidences = np.max(proba_ensemble, axis=1)

print(f"✅ Predictions generated")

# Find signals at 45% threshold
threshold = 0.45
signal_mask = (confidences >= threshold) & (predictions != 0)
signal_count = np.sum(signal_mask)

print(f"\n📊 Signals found: {signal_count} (threshold: {threshold*100:.0f}%)")

# Simulate trades - ONE POSITION AT A TIME
print("\n🔄 Simulating trades (ONE position at a time)...")

tp_pct = 0.015  # 1.5%
sl_pct = 0.008  # 0.8%

trades = []
current_position = None

for i, row in df.iterrows():
    timestamp = row['timestamp']
    
    # Check if we have an open position
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
    
    # No position - check for signals
    idx = df.index.get_loc(i)
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
