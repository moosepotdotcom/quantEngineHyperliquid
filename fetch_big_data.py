#!/usr/bin/env python3
"""
Fetch 3-Month Data for Robust ML Training
-----------------------------------------
Period: Nov 1, 2025 - Jan 21, 2026
Coins: BTC, ETH, SOL, AVAX, SUI
Timeframe: 15m
"""

import requests
import pandas as pd
from datetime import datetime
import time
import os

# --- CONFIG ---
COINS = ['BTC', 'ETH', 'SOL', 'AVAX', 'SUI']
INTERVAL = '5m'
START_DATE = '2025-11-01 00:00:00'
END_DATE = '2026-01-21 00:00:00'
DATA_DIR = 'training/data/5m_3months'

def get_timestamp_ms(dt_str):
    dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
    return int(dt.timestamp() * 1000)

def fetch_candles(coin, start_ts, end_ts):
    url = 'https://api.hyperliquid.xyz/info'
    headers = {'Content-Type': 'application/json'}
    all_candles = []
    
    CHUNK_SIZE_MS = 5 * 24 * 60 * 60 * 1000 # 5 days in ms
    
    current_chunk_start = start_ts
    
    print(f"📥 Fetching {coin} {INTERVAL} (Nov-Jan) in chunks...")
    
    while current_chunk_start < end_ts:
        current_chunk_end = min(current_chunk_start + CHUNK_SIZE_MS, end_ts)
        
        # print(f"   Fetching chunk: {datetime.fromtimestamp(current_chunk_start/1000)} -> {datetime.fromtimestamp(current_chunk_end/1000)}")
        
        payload = {
            'type': 'candleSnapshot',
            'req': {
                'coin': coin,
                'interval': INTERVAL,
                'startTime': current_chunk_start,
                'endTime': current_chunk_end 
            }
        }
        
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            if resp.status_code != 200:
                print(f"❌ Error {resp.status_code}: {resp.text}")
                time.sleep(1)
                continue
                
            data = resp.json()
            if data:
                for c in data:
                    ts = c['t']
                    # Strict filtering to avoid overlap duplicates logic, though explicit dedup later handles it
                    if ts >= current_chunk_start and ts < current_chunk_end:
                         all_candles.append({
                            'timestamp': datetime.fromtimestamp(ts/1000),
                            'open': float(c['o']),
                            'high': float(c['h']),
                            'low': float(c['l']),
                            'close': float(c['c']),
                            'volume': float(c['v'])
                        })
            
            time.sleep(0.2) # Rate limit nice
            
        except Exception as e:
            print(f"❌ Exception: {e}")
            time.sleep(1)
            
        current_chunk_start = current_chunk_end
            
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
            path = os.path.join(DATA_DIR, f'{coin}_5m_3mo.csv')
            df.to_csv(path, index=False)
            print(f"   💾 Saved to {path}")
        else:
            print(f"   ⚠️ No data for {coin}")

if __name__ == "__main__":
    main()
