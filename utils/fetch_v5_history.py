
import os
import sys
import pandas as pd
from datetime import datetime, timedelta
import time
import requests

# Add root (one level up)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.fetch_data import fetch_binance

def fetch_v5_history():
    print("🌐 Fetching 2025 BTC History (Enriched with Taker Volume)...")
    
    # Setup
    symbol = 'BTCUSDT'
    interval = '5m'
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2026, 1, 15)
    
    # We need to fetch in chunks because Binance limit is 1000 candles
    # 5m candles per day = 288.
    # 1000 candles ~= 3.5 days.
    
    current_time = start_date
    all_dfs = []
    
    while current_time < end_date:
        # Convert to ms for Binance if needed, but fetch_binance uses 'limit' from 'end' usually?
        # Wait, fetch_binance implementation provided looks simple:
        # params = {'symbol': symbol, 'interval': interval, 'limit': limit}
        # It doesn't accept startTime/endTime in the provided snippet!
        # I need to modify fetch_binance or write a raw fetcher here to use startTime.
        # Let's verify fetch_data.py properly.
        # Actually the provided fetch_binance ONLY uses limit, effectively getting "recent" data.
        # I MUST IMPLEMENT HISTORY FETCHING HERE.
        
        start_ts = int(current_time.timestamp() * 1000)
        end_ts = int((current_time + timedelta(days=3)).timestamp() * 1000) # 3 days chunk
        
        url = 'https://api.binance.com/api/v3/klines'
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': start_ts,
            'endTime': end_ts,
            'limit': 1000
        }
        
        try:
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            
            if len(data) > 0:
                chunk = pd.DataFrame(data, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                    'taker_buy_quote', 'ignore'
                ])
                
                chunk = chunk[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'taker_buy_base']]
                chunk['timestamp'] = pd.to_datetime(chunk['timestamp'], unit='ms')
                
                chunk = chunk.astype({
                    'open': float, 'high': float, 'low': float, 
                    'close': float, 'volume': float, 'taker_buy_base': float
                })
                
                all_dfs.append(chunk)
                print(f"   ✅ Fetched {len(chunk)} bars from {current_time.strftime('%Y-%m-%d')}...", end='\r')
            
            current_time += timedelta(days=3)
            time.sleep(0.1) 
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            time.sleep(1)
            
    if all_dfs:
        full_df = pd.concat(all_dfs).drop_duplicates('timestamp').sort_values('timestamp').reset_index(drop=True)
        
        save_path = 'training/data/BTC_5m_2025_enriched.csv'
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        full_df.to_csv(save_path, index=False)
        print(f"\n🎉 Saved Enriched History to: {save_path}")
        print(f"   Total Candles: {len(full_df)}")
        print(f"   Columns: {list(full_df.columns)}")
    else:
        print("\n❌ No data fetched.")

if __name__ == "__main__":
    fetch_v5_history()
