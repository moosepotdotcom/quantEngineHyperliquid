
import requests
import pandas as pd
import time
import datetime
import os

def download_history(start_time, end_time, filename="BTC_history.csv"):
    print(f"⬇️ Starting Download: {start_time} to {end_time}")
    
    # Hyperliquid API Endpoint
    url = "https://api.hyperliquid.xyz/info"
    
    # Convert to timestamps (ms)
    start_ts = int(pd.Timestamp(start_time).timestamp() * 1000)
    end_ts = int(pd.Timestamp(end_time).timestamp() * 1000)
    
    chunk_size_ms = 7 * 24 * 60 * 60 * 1000 # 7 Days per chunk
    
    current_end = end_ts
    
    while current_end > start_ts:
        # Calculate start for this specific chunk
        req_start = max(start_ts, current_end - chunk_size_ms)
        
        print(f"   🌐 Fetching chunk: {pd.to_datetime(req_start, unit='ms')} to {pd.to_datetime(current_end, unit='ms')}...")
        
        headers = {'Content-Type': 'application/json'}
        body = {
            "type": "candleSnapshot",
            "req": {
                "coin": "BTC",
                "interval": "5m",
                "startTime": int(req_start), 
                "endTime": int(current_end)
            }
        }
        
        try:
            resp = requests.post(url, json=body, headers=headers)
            data = resp.json()
            
            if not data or len(data) == 0:
                print("   ⚠️ No data returned for this chunk.")
                # If we got nothing, try stepping back anyway to verify if it's just this gap
                current_end = req_start - 1000
                continue
                
            # Data comes [timestamp, open, high, low, close, volume, ...]
            
            chunk_df = pd.DataFrame(data)
            if 't' in chunk_df.columns:
                chunk_df.rename(columns={'t': 'timestamp', 'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'}, inplace=True)
            
            # Filter valid Time
            chunk_df['timestamp'] = pd.to_numeric(chunk_df['timestamp'])
            chunk_df = chunk_df[chunk_df['timestamp'] <= current_end]
            chunk_df = chunk_df[chunk_df['timestamp'] >= start_ts] # Strict lower bound
            
            if len(chunk_df) == 0:
                 # No data in this valid range?
                 current_end = req_start - 1000
                 continue
                 
            all_data.append(chunk_df)
            print(f"      ✅ Got {len(chunk_df)} rows.")
            
            # Update cursor: Move to before the earliest candle found
            min_ts = chunk_df['timestamp'].min()
            current_end = min_ts - 1000 
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            break
    
    if not all_data:
        print("❌ No data downloaded.")
        return

    # Combine all chunks
    full_df = pd.concat(all_data)
    full_df.drop_duplicates(subset=['timestamp'], inplace=True)
    full_df.sort_values('timestamp', inplace=True)
    
    # Convert types
    cols = ['open', 'high', 'low', 'close', 'volume']
    for c in cols:
        full_df[c] = pd.to_numeric(full_df[c])
    
    # Date index for CSV
    full_df['datetime'] = pd.to_datetime(full_df['timestamp'], unit='ms')
    full_df.set_index('datetime', inplace=True)
    
    # Filter exact range requested
    mask = (full_df.index >= pd.Timestamp(start_time)) & (full_df.index <= pd.Timestamp(end_time))
    final_df = full_df[mask]
    
    print(f"✅ Download Complete. Rows: {len(final_df)}")
    print(f"   Range: {final_df.index.min()} to {final_df.index.max()}")
    
    final_df.to_csv(filename)
    print(f"💾 Saved to {filename}")

if __name__ == "__main__":
    # Download November 2025
    # Buffer: Start Oct 25 to ensure indicators are warm for Nov 1
    download_history("2025-10-25 00:00:00", "2025-11-30 23:59:59", "BTC_Nov2025_5m.csv")
