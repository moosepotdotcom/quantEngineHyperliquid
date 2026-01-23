
import sys
import os
import requests
import pandas as pd
import time
import json

# Mimic fetch_candles from live_trader.py
def fetch_candles(coin):
    end_ts = int(time.time() * 1000)
    start_ts = end_ts - (1000 * 5 * 60 * 300) # Last 300 candles (5m)
    
    url = "https://api.hyperliquid.xyz/info"
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": coin,
            "interval": "5m",
            "startTime": start_ts,
            "endTime": end_ts
        }
    }
    
    print(f"DEBUG: Fetching {coin} from {start_ts} to {end_ts}...")
    try:
        resp = requests.post(url, json=payload, timeout=15)
        print(f"DEBUG: Status Code: {resp.status_code}")
        
        try:
            data = resp.json()
            print(f"DEBUG: Response Params: {str(data)[:200]}...") # First 200 chars
        except:
            print(f"DEBUG: Raw Content: {resp.text[:200]}")
            return pd.DataFrame()
            
        if not data: 
            print("DEBUG: Empty Data Returned")
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        print(f"DEBUG: DF Shape: {df.shape}")
        return df
    except Exception as e:
        print(f"DEBUG: Exception: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    df = fetch_candles("BTC")
    if not df.empty:
        print("✅ SUCCESS")
    else:
        print("❌ FAILURE")
