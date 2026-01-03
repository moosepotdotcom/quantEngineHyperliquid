#!/usr/bin/env python3
"""
Quick diagnostic to check model predictions on current live data
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "utils"))

import pandas as pd
import numpy as np
import xgboost as xgb
from feature_engineer import add_all_indicators
import requests
from datetime import datetime, timedelta

def fetch_hyperliquid_data(interval='1h', limit=500):
    """Fetch data from Hyperliquid"""
    url = 'https://api.hyperliquid.xyz/info'
    
    interval_minutes = {
        '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
        '1h': 60, '2h': 120, '4h': 240, '1d': 1440
    }
    
    minutes = interval_minutes.get(interval, 60)
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(minutes=minutes * limit)).timestamp() * 1000)
    
    payload = {
        'type': 'candleSnapshot',
        'req': {
            'coin': 'BTC',
            'interval': interval,
            'startTime': start_time,
            'endTime': end_time
        }
    }
    
    resp = requests.post(url, json=payload, timeout=10)
    data = resp.json()
    
    df_data = []
    for candle in data:
        df_data.append([
            candle['t'],
            float(candle['o']),
            float(candle['h']),
            float(candle['l']),
            float(candle['c']),
            float(candle['v'])
        ])
    
    df = pd.DataFrame(df_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    return df

print("🔍 DIAGNOSTIC: Checking model predictions on live data")
print("="*70)

# Load Winner Hunter model
print("\n📦 Loading Winner Hunter model...")
model = xgb.XGBClassifier()
model.load_model('models/winner_hunter_1h.json')
print("✅ Model loaded")

# Fetch live data
print("\n📊 Fetching live 1H data from Hyperliquid...")
df = fetch_hyperliquid_data('1h', 500)
print(f"✅ Fetched {len(df)} bars")

# Add indicators
print("\n🔧 Adding indicators...")
df = add_all_indicators(df)
print(f"✅ Generated {len(df.columns)} columns")

# Prepare features
exclude = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
features = [c for c in df.columns if c not in exclude]
print(f"✅ Using {len(features)} features")

# Get predictions for last 100 bars
print("\n📈 Analyzing last 100 predictions...")
recent_df = df.tail(100).copy()

predictions = []
for idx in range(len(recent_df)):
    row = recent_df.iloc[idx]
    X = row[features].values.reshape(1, -1)
    prob = model.predict_proba(X)[0][1]
    predictions.append({
        'timestamp': row['timestamp'],
        'close': row['close'],
        'confidence': prob,
        'rsi': row['rsi_14'],
        'macd': row['macd_hist']
    })

pred_df = pd.DataFrame(predictions)

print("\n" + "="*70)
print("📊 CONFIDENCE DISTRIBUTION (Last 100 bars)")
print("="*70)
print(f"Mean:    {pred_df['confidence'].mean():.4%}")
print(f"Median:  {pred_df['confidence'].median():.4%}")
print(f"Min:     {pred_df['confidence'].min():.4%}")
print(f"Max:     {pred_df['confidence'].max():.4%}")
print(f"Std Dev: {pred_df['confidence'].std():.4%}")

print("\n📊 PERCENTILES:")
for p in [25, 50, 75, 90, 95, 99]:
    val = np.percentile(pred_df['confidence'], p)
    print(f"  {p}th percentile: {val:.4%}")

print("\n📊 CONFIDENCE RANGES:")
ranges = [
    (0, 0.01, "0-1%"),
    (0.01, 0.05, "1-5%"),
    (0.05, 0.10, "5-10%"),
    (0.10, 0.50, "10-50%"),
    (0.50, 0.95, "50-95%"),
    (0.95, 1.00, "95-100% (TRADE ZONE)")
]

for low, high, label in ranges:
    count = len(pred_df[(pred_df['confidence'] >= low) & (pred_df['confidence'] < high)])
    pct = (count / len(pred_df)) * 100
    print(f"  {label:20s}: {count:3d} bars ({pct:5.1f}%)")

print("\n📊 TOP 10 HIGHEST CONFIDENCE PREDICTIONS:")
top10 = pred_df.nlargest(10, 'confidence')
for idx, row in top10.iterrows():
    print(f"  {row['timestamp']}: {row['confidence']:.4%} (Close: ${row['close']:,.2f}, RSI: {row['rsi']:.1f})")

print("\n" + "="*70)
print("✅ DIAGNOSTIC COMPLETE")
print("="*70)
