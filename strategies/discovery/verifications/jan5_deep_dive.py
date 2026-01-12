import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone

def get_candles(start_time, hours=12):
    url = "https://api.hyperliquid.xyz/info"
    end_time = start_time + timedelta(hours=hours)
    
    # 5m candles for analysis
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
    df['timestamp'] = pd.to_datetime(df['t'], unit='ms', utc=True)
    df['open'] = df['o'].astype(float)
    df['high'] = df['h'].astype(float)
    df['low'] = df['l'].astype(float)
    df['close'] = df['c'].astype(float)
    df['volume'] = df['v'].astype(float)
    return df

def calculate_indicators(df):
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # EMAs (Need to resample to 1H for accurate Trend comparison?)
    # Approximating 1H EMAs on 5m data is messy. 
    # Let's just use 5m EMAs to see immediate trend, 
    # but the BOT uses 1H EMA20/50.
    return df

# Get 1H data for Trend Baseline
def get_1h_trend_data(start_time):
    url = "https://api.hyperliquid.xyz/info"
    # Get enough history for EMA
    hist_start = start_time - timedelta(hours=100)
    end_time = start_time + timedelta(hours=24)
    
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": "BTC",
            "interval": "1h",
            "startTime": int(hist_start.timestamp() * 1000),
            "endTime": int(end_time.timestamp() * 1000)
        }
    }
    resp = requests.post(url, json=payload)
    df = pd.DataFrame(resp.json())
    df['timestamp'] = pd.to_datetime(df['t'], unit='ms', utc=True)
    df['close'] = df['c'].astype(float)
    
    df['ema20'] = df['close'].ewm(span=20).mean()
    df['ema50'] = df['close'].ewm(span=50).mean()
    return df

print("🔍 JAN 5 DEEP DIVE: THE KILL ZONE (17:00 - 18:00 UTC)")

# Focus Time: Jan 5 17:00 UTC
focus_start = datetime(2026, 1, 5, 12, 0, 0, tzinfo=timezone.utc)

# 1. Get Trend Data
df_1h = get_1h_trend_data(focus_start)
print(f"Loaded 1H Trend Data: {len(df_1h)} candles")

# 2. Get 5m Action Data
df_5m = get_candles(focus_start, hours=10)
df_5m = calculate_indicators(df_5m)

# Analyze the specific loss timestamps
loss_times = [
    "17:00", "17:05", "17:10", "17:15", "17:20", "17:25", "17:30", "17:35", "17:45"
]

print(f"\n{'Time':<8} | {'Price':<8} | {'1H Trend':<10} | {'1H EMA20':<8} | {'dist%':<6} | {'RSI':<5} | {'Note'}")
print("-" * 80)

for idx, row in df_5m.iterrows():
    ts_str = row['timestamp'].strftime('%H:%M')
    day = row['timestamp'].day
    if day != 5: continue
    
    # Only care about 16:00 to 18:00
    if row['timestamp'].hour < 16 or row['timestamp'].hour > 18:
        continue
        
    # Find matching 1H trend stats
    # Locate the 1H candle that CONTAINS this 5m candle
    # e.g. 17:05 belongs to 17:00 1H candle? Or 16:00?
    # Hyperliquid 1H candle at 17:00 covers 17:00:00 to 17:59:59? Usually.
    # We want the trend value KNOWN at that time. 
    # At 17:05, we technically only know the CLOSE of 16:00 candle?
    # Or the open/current state of 17:00.
    # The bot uses `calculate_trend` which likely looks at *closed* candles or latest calc.
    # Let's check the 1H candle timestamp <= current time.
    
    trend_row = df_1h[df_1h['timestamp'] <= row['timestamp']].iloc[-1]
    
    ema20 = trend_row['ema20']
    ema50 = trend_row['ema50']
    trend = "BULL" if ema20 > ema50 else "BEAR"
    
    price = row['close']
    dist_to_ema20 = (price - ema20) / ema20 * 100
    
    mark = ""
    if ts_str in loss_times:
        mark = "❌ LOSS ENTRY"
    elif "16:5" in ts_str:
        mark = "⚠️ Pre-Crash"
        
    print(f"{ts_str:<8} | ${price:<7.0f} | {trend:<10} | ${ema20:<7.0f} | {dist_to_ema20:>5.2f}% | {row['rsi']:>5.1f} | {mark}")

