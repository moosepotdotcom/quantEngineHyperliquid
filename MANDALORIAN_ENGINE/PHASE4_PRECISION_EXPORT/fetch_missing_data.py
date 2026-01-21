import requests
import pandas as pd
import time
from datetime import datetime

# Binance Public API
BASE_URL = "https://api.binance.com/api/v3/klines"
SYMBOL = "BTCUSDT"
INTERVAL = "5m"

def fetch_period(start_date, end_date, filename):
    print(f"\n🌍 Fetching data for {filename} ({start_date} to {end_date})...")
    
    try:
        start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
        end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)
    except ValueError as e:
        print(f"❌ Date format error: {e}")
        return

    all_candles = []
    current_start = start_ts
    
    while current_start < end_ts:
        params = {
            "symbol": SYMBOL,
            "interval": INTERVAL,
            "startTime": current_start,
            "endTime": end_ts,
            "limit": 1000
        }
        
        try:
            response = requests.get(BASE_URL, params=params, timeout=10)
            if response.status_code != 200:
                print(f"❌ HTTP Error {response.status_code}: {response.text}")
                time.sleep(1)
                continue
                
            data = response.json()
            
            if not isinstance(data, list) or len(data) == 0:
                break
                
            all_candles.extend(data)
            last_close_time = data[-1][6] 
            current_start = last_close_time + 1
            
            print(f"   ✅ Fetched {len(data)} candles... Total: {len(all_candles)}")
            time.sleep(0.1) # Rate limit protection
            
        except Exception as e:
            print(f"❌ Connection Error: {e}")
            time.sleep(5)
            continue
            
    print(f"\n   📊 Total: {len(all_candles)} candles")
    
    if len(all_candles) > 0:
        df = pd.DataFrame(all_candles, columns=[
            "timestamp", "open", "high", "low", "close", "volume", 
            "close_time", "qav", "num_trades", "taker_base_vol", "taker_quote_vol", "ignore"
        ])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df["open"] = df["open"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["close"] = df["close"].astype(float)
        df["volume"] = df["volume"].astype(float)
        
        df = df[["timestamp", "open", "high", "low", "close", "volume"]]
        df.to_csv(filename, index=False)
        print(f"   💾 Saved to {filename}")
    else:
        print("   ❌ Failed to fetch data (empty)")

if __name__ == "__main__":
    # Fetch missing months
    fetch_period("2025-01-01", "2025-02-01", "jan2025_binance_data.csv")
    fetch_period("2025-02-01", "2025-03-01", "feb2025_binance_data.csv")
    
    # Re-fetch Dec and Jan 2026 for consistency
    fetch_period("2025-12-01", "2026-01-01", "dec2025_binance_data.csv")
    fetch_period("2026-01-01", "2026-01-18", "jan2026_binance_data.csv")
