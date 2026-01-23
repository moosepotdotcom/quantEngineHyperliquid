#!/usr/bin/env python3
"""
Fetch 1m Data for Portfolio (BTC, ETH, SOL, AVAX, SUI)
------------------------------------------------------
Period: Last 7 Days
Source: Hyperliquid API
Timeframe: 1m
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import os

# --- CONFIG ---
COINS = ['BTC', 'ETH', 'SOL', 'AVAX', 'SUI']
INTERVAL = '1m'
DATA_DIR = 'data' # Relative to this script

# Fetch Last 7 Days
end_dt = datetime.now()
start_dt = end_dt - timedelta(days=7) 
START_DATE = start_dt.strftime('%Y-%m-%d %H:%M:%S')
END_DATE = end_dt.strftime('%Y-%m-%d %H:%M:%S')

def get_timestamp_ms(dt_str):
    dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
    return int(dt.timestamp() * 1000)

def fetch_candles(coin, start_ts, end_ts):
    url = 'https://api.hyperliquid.xyz/info'
    headers = {'Content-Type': 'application/json'}
    all_candles = []
    current_start = start_ts
    
    print(f"📥 Fetching {coin} {INTERVAL} from {START_DATE}...")
    
    while current_start < end_ts:
        payload = {
            'type': 'candleSnapshot',
            'req': {
                'coin': coin,
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
                break
                
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
            
            if new_candles == 0:
                # Force advance
                if len(data) > 0:
                    last_in_batch = data[-1]['t']
                    if last_in_batch > current_start:
                         current_start = last_in_batch + 1
                         continue
                break
                
            current_start = last_ts + 1  
            time.sleep(0.2) 
            
        except Exception as e:
            print(f"❌ Exception: {e}")
            break
            
    df = pd.DataFrame(all_candles)
    if not df.empty:
        df.sort_values('timestamp', inplace=True)
        df.drop_duplicates(subset='timestamp', inplace=True)
        print(f"   ✅ {coin}: {len(df)} candles")
    return df

def main():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    start_ts = int(datetime.strptime(START_DATE, '%Y-%m-%d %H:%M:%S').timestamp() * 1000)
    end_ts = int(datetime.strptime(END_DATE, '%Y-%m-%d %H:%M:%S').timestamp() * 1000)
    
    for coin in COINS:
        df = fetch_candles(coin, start_ts, end_ts)
        if not df.empty:
            path = os.path.join(DATA_DIR, f'{coin}_1m.csv')
            df.to_csv(path, index=False)
            print(f"   💾 Saved to {path}")
        else:
            print(f"   ⚠️ No data for {coin}")
            
    print("\n🎉 All Downloads Complete!")

if __name__ == "__main__":
    main()
