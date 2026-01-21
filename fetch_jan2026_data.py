#!/usr/bin/env python3
"""
Fetch live BTC 5m data from Hyperliquid for Jan 2-15, 2026
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import time

print("="*70)
print("📡 FETCHING LIVE DATA FROM HYPERLIQUID")
print("="*70)

def fetch_hyperliquid_candles(symbol='BTC', interval='5m', start_time=None, end_time=None):
    """Fetch candles from Hyperliquid"""
    url = "https://api.hyperliquid.xyz/info"
    
    # Convert to milliseconds
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": symbol,
            "interval": interval,
            "startTime": start_ms,
            "endTime": end_ms
        }
    }
    
    try:
        print(f"\n📥 Fetching {symbol} {interval} from {start_time} to {end_time}...")
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            return None
        
        # Parse candles
        candles = []
        for candle in data:
            candles.append({
                'timestamp': pd.to_datetime(candle['t'], unit='ms'),
                'open': float(candle['o']),
                'high': float(candle['h']),
                'low': float(candle['l']),
                'close': float(candle['c']),
                'volume': float(candle['v']),
                'taker_buy_base': float(candle.get('buyVolume', candle['v'] * 0.5))
            })
        
        df = pd.DataFrame(candles)
        print(f"✅ Fetched {len(df)} candles")
        return df
        
    except Exception as e:
        print(f"❌ API Error: {e}")
        return None

# Fetch data for Jan 2-15, 2026
start_date = datetime(2026, 1, 2, 0, 0, 0)
end_date = datetime(2026, 1, 15, 23, 59, 59)

# Hyperliquid API has limits, so fetch in chunks
all_data = []
current_start = start_date

while current_start < end_date:
    current_end = min(current_start + timedelta(days=3), end_date)
    
    df_chunk = fetch_hyperliquid_candles('BTC', '5m', current_start, current_end)
    
    if df_chunk is not None and len(df_chunk) > 0:
        all_data.append(df_chunk)
        print(f"   Got {len(df_chunk)} candles for {current_start.date()} to {current_end.date()}")
    
    current_start = current_end + timedelta(minutes=5)
    time.sleep(1)  # Rate limiting

if all_data:
    df_final = pd.concat(all_data, ignore_index=True)
    df_final = df_final.sort_values('timestamp').drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    
    print(f"\n✅ Total candles fetched: {len(df_final)}")
    print(f"   Period: {df_final['timestamp'].min()} to {df_final['timestamp'].max()}")
    
    # Save
    output_file = 'training/data/BTC_5m_jan2_15_2026_live.csv'
    df_final.to_csv(output_file, index=False)
    print(f"\n💾 Saved to {output_file}")
    
    print("\n" + "="*70)
    print("✅ DATA FETCH COMPLETE")
    print("="*70)
else:
    print("\n❌ No data fetched!")
