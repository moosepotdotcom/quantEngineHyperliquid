#!/usr/bin/env python3
import pandas as pd
from datetime import timedelta
import re

# Parse whales
whales = []
with open('live_system.log') as f:
    for line in f:
        if 'WHALE' in line:
            m = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),(\d+).*WHALE (\w): \$([0-9,]+)', line)
            if m:
                dt_str, ms, direction, usd_str = m.groups()
                dt = pd.to_datetime(dt_str) + timedelta(milliseconds=int(ms))
                whales.append(dt)

# Load candles
c = pd.read_csv('data/btc_5m_jan16_2026.csv')
c['dt'] = pd.to_datetime(c['timestamp'], unit='ms')

print("WHALE TIMES:")
for i, w in enumerate(sorted(whales)[:5]):
    print(f"  {i}: {w}")

print(f"\nCANDLE TIMES:")
for i, row in c.iterrows():
    print(f"  {i}: {row['dt']}")

print(f"\nTesting overlap...")
for idx, row in c.iterrows():
    dt_start = row['dt'] - timedelta(minutes=5)
    dt_end = row['dt'] + timedelta(minutes=5)
    w_in_window = [w for w in whales if w >= dt_start and w < dt_end]
    print(f"Candle {idx} ({row['dt']}): {len(w_in_window)} whales in [{dt_start} to {dt_end}]")
