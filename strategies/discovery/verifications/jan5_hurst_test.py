import pandas as pd
import numpy as np
import requests
from datetime import datetime, timezone, timedelta
import sys
import os

sys.path.append(os.getcwd())
from utils.advanced_features import get_rolling_hurst, detect_regime

def get_data(start_time, end_time):
    url = "https://api.hyperliquid.xyz/info"
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": "BTC",
            "interval": "5m",
            "startTime": int(start_time.timestamp() * 1000),
            "endTime": int(end_time.timestamp() * 1000)
        }
    }
    resp = requests.post(url, json=payload)
    df = pd.DataFrame(resp.json())
    df['t'] = pd.to_datetime(df['t'], unit='ms', utc=True)
    df['close'] = df['c'].astype(float)
    df['rsi'] = 50.0 # Dummy, we know Jan 5 had RSI < 30
    return df

print("🧪 TESTING HURST FILTER ON JAN 5")
print("-" * 60)

# Jan 5 Full Day
start = datetime(2026, 1, 5, 0, 0, 0, tzinfo=timezone.utc)
end = datetime(2026, 1, 5, 23, 59, 0, tzinfo=timezone.utc)

# Need buffer for calculations
buffer_start = start - timedelta(hours=12)

df = get_data(buffer_start, end)
print(f"Loaded {len(df)} candles")

# Apply Advanced Features
print("Calculating Hurst Exponent...")
hursts = get_rolling_hurst(df, window=100)
df['hurst'] = hursts

print("Calculating Volatility Regime...")
vol_z = detect_regime(df.copy(), window=100)
df['vol_z'] = vol_z

# Analysis Points
# 1. Morning Wins (e.g. 14:00 - 14:30)
# 2. Evening Losses (17:00 - 18:00)

checkpoints = [
    ("Morning Win", "14:00"),
    ("Morning Win", "14:30"),
    ("Evening Loss", "17:00"),
    ("Evening Loss", "17:15"),
    ("Evening Loss", "17:30"),
]

print(f"\n{'Time':<20} | {'Type':<15} | {'Hurst':<8} | {'Vol Z':<8} | {'Action'}")
print("-" * 75)

for label, time_str in checkpoints:
    target_dt = datetime.strptime(f"2026-01-05 {time_str}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    
    # Find row
    row = df[df['t'] == target_dt]
    if not row.empty:
        h = row.iloc[0]['hurst']
        v = row.iloc[0]['vol_z']
        
        # LOGIC:
        # If buying dip (Long), we want Mean Reversion (H < 0.5)
        # If H > 0.5, it means "Trending" (Falling Knife in this case)
        
        action = "✅ ALLOW"
        if h > 0.55: # Strict trend
            action = "🛑 BLOCK (Knife)"
        elif v > 2.0:
            action = "🛑 BLOCK (Vol)"
            
        print(f"{time_str:<20} | {label:<15} | {h:.3f}    | {v:.2f}     | {action}")
    else:
        print(f"{time_str} not found")

print("-" * 75)
print("INTERPRETATION:")
print("- H > 0.55 implies strong trend (Falling Knife risk for dip buys)")
print("- Vol Z > 2.0 implies Crash Regime")
