#!/usr/bin/env python3
"""Quick verification of whale + imbalance signal logic"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re

# Parse whale events
print("Parsing whale events...")
events = []
with open('live_system.log', 'r') as f:
    for line in f:
        if 'WHALE' in line:
            match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),(\d+).*WHALE (\w): \$([0-9,]+)', line)
            if match:
                dt_str, ms, direction, usd_str = match.groups()
                dt = pd.to_datetime(dt_str) + timedelta(milliseconds=int(ms))
                side = 'BUY' if direction == 'A' else 'SELL'
                usd = float(usd_str.replace(',', ''))
                events.append({'dt': dt, 'side': side, 'usd': usd})

whales = pd.DataFrame(events)
print(f"Parsed {len(whales)} whale events")
print(whales.head())

# Load synthetic candles
print("\nLoading candles...")
candles = pd.read_csv('data/btc_5m_jan16_2026.csv')
candles['dt'] = pd.to_datetime(candles['timestamp'], unit='ms')
print(f"Loaded {len(candles)} candles")
print(candles[['dt', 'close']].head())

# Load synthetic Phase4 features
print("\nLoading Phase4 features...")
p4 = pd.read_csv('data/phase4_features_jan16.csv')
p4['dt'] = pd.to_datetime(p4['timestamp'])
print(f"Loaded {len(p4)} Phase4 features")
print(p4.head())

# Merge whales to candles
print("\nMerging whales to candles...")
candles['whale_count'] = 0
candles['whale_usd'] = 0.0
candles['whale_bias'] = 0

for idx, row in candles.iterrows():
    candle_start = row['dt']
    candle_end = candle_start + timedelta(minutes=5)
    mask = (whales['dt'] >= candle_start) & (whales['dt'] < candle_end)
    whales_in = whales[mask]
    if not whales_in.empty:
        candles.at[idx, 'whale_count'] = len(whales_in)
        candles.at[idx, 'whale_usd'] = whales_in['usd'].sum()
        buy_cnt = (whales_in['side'] == 'BUY').sum()
        sell_cnt = (whales_in['side'] == 'SELL').sum()
        candles.at[idx, 'whale_bias'] = 1 if buy_cnt > sell_cnt else (-1 if sell_cnt > buy_cnt else 0)

print("Whales per candle:")
print(candles[['dt', 'whale_count', 'whale_usd', 'whale_bias']])

# Generate signals
print("\nGenerating signals...")
candles['imbalance'] = p4['ob_imbalance'].values
candles['funding'] = p4['funding_pct'].values
candles['signal'] = 0.0

for idx in range(len(candles)):
    row = candles.iloc[idx]
    
    # Scoring logic
    whale_score = row['whale_bias'] * min(1.0, row['whale_usd'] / 400000.0) * 0.6 if row['whale_count'] >= 3 else 0
    imbalance_score = np.sign(row['imbalance']) * min(1.0, abs(row['imbalance']) / 0.08) * 0.25 if abs(row['imbalance']) > 0.015 else 0
    funding_score = -np.sign(row['funding']) * min(1.0, abs(row['funding']) / 0.08) * 0.15 if abs(row['funding']) > 0.02 else 0
    
    composite = whale_score + imbalance_score + funding_score
    if abs(composite) > 0.25:
        candles.at[idx, 'signal'] = np.sign(composite)

print("\nSignal distribution:")
print(candles[['dt', 'whale_count', 'imbalance', 'funding', 'signal']])

print(f"\nBUY signals: {(candles['signal'] == 1.0).sum()}")
print(f"SELL signals: {(candles['signal'] == -1.0).sum()}")
