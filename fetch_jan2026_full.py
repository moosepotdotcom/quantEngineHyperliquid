import requests
import pandas as pd
from datetime import datetime
import time
import os

# Configuration
SYMBOL = 'BTC'
START_DATE = '2026-01-01 00:00:00'
END_DATE = '2026-01-21 23:59:59' # Cover present
INTERVALS = ['5m', '15m', '1h']
OUTPUT_DIR = 'training/data'

os.makedirs(OUTPUT_DIR, exist_ok=True)

def fetch_candles(coin, interval, start_ts, end_ts):
    url = "https://api.hyperliquid.xyz/info"
    all_candles = []
    
    current_start = start_ts
    
    # Hyperliquid limit is usually around 5000 candles per req, but we'll safe chunk
    # Time window chunks: 3 days (approx 864 5m candles per 3 days) to be safe
    chunk_size_ms = 3 * 24 * 60 * 60 * 1000 
    
    while current_start < end_ts:
        current_end = min(current_start + chunk_size_ms, end_ts)
        
        payload = {
            "type": "candleSnapshot",
            "req": {
                "coin": coin,
                "interval": interval,
                "startTime": current_start,
                "endTime": current_end
            }
        }
        
        try:
            print(f"   Fetching {interval} {datetime.fromtimestamp(current_start/1000)} -> {datetime.fromtimestamp(current_end/1000)}...")
            resp = requests.post(url, json=payload, timeout=10)
            data = resp.json()
            
            if isinstance(data, list) and len(data) > 0:
                candles = []
                for c in data:
                    candles.append({
                        'timestamp': pd.to_datetime(c['t'], unit='ms'),
                        'open': float(c['o']),
                        'high': float(c['h']),
                        'low': float(c['l']),
                        'close': float(c['c']),
                        'volume': float(c['v'])
                    })
                all_candles.extend(candles)
                print(f"      Got {len(candles)} candles.")
            else:
                print(f"      No data for this chunk.")
                
        except Exception as e:
            print(f"      Error: {e}")
        
        current_start = current_end + 1 # Next ms
        time.sleep(0.5) # Rate limit safety

    return pd.DataFrame(all_candles)

def main():
    print("="*70)
    print("📥 FETCHING HYPERLIQUID DATA (JAN 2026 FULL)")
    print("="*70)
    
    start_ts = int(pd.Timestamp(START_DATE).timestamp() * 1000)
    end_ts = int(pd.Timestamp(END_DATE).timestamp() * 1000)
    
    for interval in INTERVALS:
        print(f"\nProcessing {interval}...")
        df = fetch_candles(SYMBOL, interval, start_ts, end_ts)
        
        if not df.empty:
            df = df.sort_values('timestamp').drop_duplicates('timestamp').reset_index(drop=True)
            filename = f"{OUTPUT_DIR}/{SYMBOL}_{interval}_jan2026.csv"
            df.to_csv(filename, index=False)
            print(f"✅ Saved {len(df)} rows to {filename}")
        else:
            print(f"❌ Failed to fetch {interval} data")

if __name__ == "__main__":
    main()
