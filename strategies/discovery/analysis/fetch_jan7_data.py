
import requests
import json
import pandas as pd
from datetime import datetime, timezone

def fetch_candles(start_ts, end_ts):
    url = "https://api.hyperliquid.xyz/info"
    headers = {"Content-Type": "application/json"}
    
    all_candles = []
    current_start = start_ts
    
    while current_start < end_ts:
        print(f"Fetching from {pd.to_datetime(current_start, unit='ms')}...")
        body = {
            "type": "candleSnapshot",
            "req": {
                "coin": "BTC",
                "interval": "1m",
                "startTime": current_start,
                "endTime": end_ts 
            }
        }
        
        try:
            res = requests.post(url, headers=headers, json=body)
            data = res.json()
            if not data:
                break
            
            all_candles.extend(data)
            last_candle_ts = data[-1]['t']
            
            # API returns candles inclusive of start?
            # If we get last_candle, next start should be last + 1m
            if last_candle_ts >= current_start:
                current_start = last_candle_ts + 60000
            else:
                current_start += 60000 # Safety
                
            # Rate limit
            # time.sleep(0.5) 
            
            # Since candleSnapshot returns up to 5000 candles or so? 
            # Actually Hyperliquid might return specific window.
            # If we got enough, break/continue.
            if len(data) < 2:
                break
                
        except Exception as e:
            print(f"Error: {e}")
            break
            
    return all_candles

# Jan 7 2026
# 2026-01-07 00:00:00 UTC
dt_start = datetime(2026, 1, 7, 0, 0, 0, tzinfo=timezone.utc)
dt_end = datetime(2026, 1, 8, 0, 0, 0, tzinfo=timezone.utc)

ts_start = int(dt_start.timestamp() * 1000)
ts_end = int(dt_end.timestamp() * 1000)

print(f"Fetching Jan 7 Data: {ts_start} to {ts_end}")
candles = fetch_candles(ts_start, ts_end)
print(f"Fetched {len(candles)} candles.")

with open('jan7_historical_1m.json', 'w') as f:
    json.dump(candles, f)
    
print("Saved to jan7_historical_1m.json")
