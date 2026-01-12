#!/usr/bin/env python3
"""
Feature Comparison: Live Logs vs Historical Data
Diagnose why live model gave 70% confidence but historical reconstruction gives 43%
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
from utils.feature_engineer import add_all_indicators

# 1. Get Live Features being used at 00:32:31
print("=" * 70)
print("🔍 COMPARING LIVE VS HISTORICAL FEATURES")
print("=" * 70)

target_time_str = "2026-01-08T00:32:31"
live_features = None

with open('logs/trades/predictions_20260108.jsonl', 'r') as f:
    for line in f:
        if target_time_str in line and "MTF Scalper" in line:
            data = json.loads(line)
            live_features = data['features']
            print(f"✅ Found live log entry for {target_time_str}")
            print(f"   Live Confidence: {data['confidence']:.4%}")
            break

if not live_features:
    print("❌ Could not find log entry")
    exit(1)

# 2. Calculate Historical Features for the same period
print("\n📥 Loading & Processing Historical Data...")

def load_data(interval):
    with open(f'jan8_historical_{interval}.json', 'r') as f:
        candles = json.load(f)
    df = pd.DataFrame(candles)
    df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
    df['open'] = df['o'].astype(float)
    df['high'] = df['h'].astype(float)
    df['low'] = df['l'].astype(float)
    df['close'] = df['c'].astype(float)
    df['volume'] = df['v'].astype(float)
    return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

# Load 1m and resample to mimic 5m
df_1m = load_data('1m')
df_1m.set_index('timestamp', inplace=True)

# The live prediction was at 00:32:31
# This falls into the 00:30:00 - 00:35:00 candle
# In real-time, at 00:32:31, the 5m candle is "forming"
# The bot likely uses the "latest" available data. 

# Let's verify what "latest" means.
# If we resample 1m data up to 00:32:00, that might be what the bot saw?
# Or did it see the partial 5m candle?

# Let's try Standard 5M Resampling (00:30 bucket)
df_5m_resampled = df_1m.resample('5T').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}).dropna() 
df_5m_resampled.reset_index(inplace=True)

# Engineer features
df_5m_feat = add_all_indicators(df_5m_resampled.copy())

# Find the 00:30 candle features
hist_row = df_5m_feat[df_5m_feat['timestamp'] == pd.Timestamp('2026-01-08 00:30:00')]

if len(hist_row) == 0:
    print("❌ Could not find historical 00:30 candle")
    exit(1)

hist_features = hist_row.iloc[0].to_dict()

# 3. Compare Key Features
print("\n📊 FEATURE COMPARISON (Live vs Historical)")
print(f"{'Feature':<20} | {'Live':<15} | {'Historical':<15} | {'Diff':<10}")
print("-" * 70)

key_features = [
    'close', 'rsi_14', 'macd', 'bb_width', 
    'ema_5', 'ema_20', 'volume', 'atr_14'
]

for feat in key_features:
    live_val = live_features.get(feat, 0)
    hist_val = hist_features.get(feat, 0)
    
    # Handle NaN
    if pd.isna(hist_val): hist_val = 0
    
    diff = abs(live_val - hist_val)
    diff_pct = (diff / live_val) * 100 if live_val != 0 else 0
    
    print(f"{feat:<20} | {live_val:<15.4f} | {hist_val:<15.4f} | {diff_pct:>8.2f}%")

print("-" * 70)
print("\n💡 Analysis:")
print("If 'close' price is significantly different, the source data doesn't match.")
print("If 'close' is close but indicators differ, feature engineering logic differs.")
