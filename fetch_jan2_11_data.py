import requests
import pandas as pd
from datetime import datetime
import time
import os

# Configuration
SYMBOL = 'BTC'
INTERVAL = '5m'
START_DATE = '2026-01-02 00:00:00'
END_DATE = '2026-01-11 23:59:59'
OUTPUT_FILE = 'training/data/BTC_Jan2_11_2026_Hyperliquid.csv'

def get_timestamp_ms(dt_str):
    dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
    return int(dt.timestamp() * 1000)

def fetch_candles(start_ts, end_ts):
    url = 'https://api.hyperliquid.xyz/info'
    headers = {'Content-Type': 'application/json'}
    
    all_candles = []
    current_start = start_ts
    
    # Check output directory
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    print(f"📥 Fetching {SYMBOL} {INTERVAL} from {START_DATE} to {END_DATE}...")
    
    while current_start < end_ts:
        payload = {
            'type': 'candleSnapshot',
            'req': {
                'coin': SYMBOL,
                'interval': INTERVAL,
                'startTime': current_start,
                'endTime': end_ts 
            }
        }
        
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            if resp.status_code != 200:
                print(f"❌ Error {resp.status_code}: {resp.text}")
                break
                
            data = resp.json()
            if not data:
                print("⚠️ No more data returned.")
                break
                
            # Filter and append
            new_candles = 0
            last_ts = 0
            
            for c in data:
                ts = c['t']
                if ts >= current_start and ts <= end_ts:
                    all_candles.append({
                        'timestamp': datetime.fromtimestamp(ts/1000),
                        'open': float(c['o']),
                        'high': float(c['h']),
                        'low': float(c['l']),
                        'close': float(c['c']),
                        'volume': float(c['v'])
                    })
                    last_ts = ts
                    new_candles += 1
            
            print(f"   Fetched {new_candles} candles... (Last: {datetime.fromtimestamp(last_ts/1000)})")
            
            if new_candles == 0:
                print("⚠️ Zero new candles valid for range. Stopping.")
                break
                
            # Update start time for next batch (avoid duplicates)
            current_start = last_ts + 1
            time.sleep(0.5) # Rate limit politeness
            
        except Exception as e:
            print(f"❌ Exception: {e}")
            break
            
    return pd.DataFrame(all_candles)

def main():
    start_ts = get_timestamp_ms(START_DATE)
    end_ts = get_timestamp_ms(END_DATE)
    
    df = fetch_candles(start_ts, end_ts)
    
    if not df.empty:
        # Sort and Drop Duplicates
        df.sort_values('timestamp', inplace=True)
        df.drop_duplicates(subset='timestamp', inplace=True)
        
        print(f"\n✅ Total unique candles: {len(df)}")
        print(f"   Start: {df['timestamp'].min()}")
        print(f"   End:   {df['timestamp'].max()}")
        
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"💾 Saved to: {OUTPUT_FILE}")
    else:
        print("❌ No data fetched")

if __name__ == "__main__":
    main()
