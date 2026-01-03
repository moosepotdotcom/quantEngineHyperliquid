#!/usr/bin/env python3
"""
Download 10 years of BTC historical data from multiple sources
"""
import pandas as pd
import requests
from datetime import datetime, timedelta
import time
import os

def download_binance_data(symbol='BTCUSDT', interval='1h', start_date='2015-01-01', end_date='2025-12-30'):
    """
    Download historical data from Binance API
    """
    print(f"\n📊 Downloading {symbol} {interval} data from Binance...")
    print(f"   Date range: {start_date} to {end_date}")
    
    # Convert to timestamps
    start_ts = int(pd.Timestamp(start_date).timestamp() * 1000)
    end_ts = int(pd.Timestamp(end_date).timestamp() * 1000)
    
    # Binance API endpoint
    url = 'https://api.binance.com/api/v3/klines'
    
    all_data = []
    current_ts = start_ts
    
    # Binance returns max 1000 candles per request
    limit = 1000
    
    while current_ts < end_ts:
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': current_ts,
            'limit': limit
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                break
            
            all_data.extend(data)
            
            # Update timestamp for next batch
            current_ts = data[-1][0] + 1
            
            # Progress
            current_date = pd.Timestamp(current_ts, unit='ms')
            print(f"   Downloaded up to: {current_date.strftime('%Y-%m-%d %H:%M')}", end='\r')
            
            # Rate limiting
            time.sleep(0.1)
            
        except Exception as e:
            print(f"\n   ⚠️ Error: {e}")
            print(f"   Retrying in 5 seconds...")
            time.sleep(5)
            continue
    
    print(f"\n   ✅ Downloaded {len(all_data)} candles")
    
    # Convert to DataFrame
    df = pd.DataFrame(all_data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    
    # Keep only relevant columns
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    
    # Convert types
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    
    return df

def download_cryptodatadownload(interval='1h'):
    """
    Download from CryptoDataDownload (if available)
    """
    print(f"\n📊 Attempting to download from CryptoDataDownload...")
    
    # CryptoDataDownload URLs (may need updating)
    urls = {
        '1h': 'https://www.cryptodatadownload.com/cdd/Binance_BTCUSDT_1h.csv',
        '5m': 'https://www.cryptodatadownload.com/cdd/Binance_BTCUSDT_5m.csv',
        '15m': 'https://www.cryptodatadownload.com/cdd/Binance_BTCUSDT_15m.csv'
    }
    
    if interval not in urls:
        print(f"   ⚠️ Interval {interval} not available")
        return None
    
    try:
        # Download
        response = requests.get(urls[interval], timeout=60)
        response.raise_for_status()
        
        # Parse CSV (skip first 2 rows which are metadata)
        from io import StringIO
        df = pd.read_csv(StringIO(response.text), skiprows=2)
        
        # Standardize column names
        df.columns = df.columns.str.lower()
        df = df.rename(columns={
            'unix': 'timestamp',
            'date': 'date_str'
        })
        
        # Convert timestamp
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        elif 'date_str' in df.columns:
            df['timestamp'] = pd.to_datetime(df['date_str'])
        
        # Keep only relevant columns
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        
        print(f"   ✅ Downloaded {len(df)} candles from CryptoDataDownload")
        return df
        
    except Exception as e:
        print(f"   ⚠️ CryptoDataDownload failed: {e}")
        return None

def main():
    """Main execution"""
    print("="*70)
    print("📦 BTC HISTORICAL DATA DOWNLOADER")
    print("="*70)
    
    # Create data directory
    os.makedirs('training/data', exist_ok=True)
    
    # Download 1H data (for Winner Hunter)
    print("\n" + "="*70)
    print("1️⃣ DOWNLOADING 1H DATA")
    print("="*70)
    
    # Try CryptoDataDownload first, fallback to Binance
    df_1h = download_cryptodatadownload('1h')
    if df_1h is None or len(df_1h) < 50000:
        print("   Falling back to Binance API...")
        df_1h = download_binance_data('BTCUSDT', '1h', '2015-01-01', '2025-12-30')
    
    # Save
    output_file = 'training/data/BTC_1h_10y.csv'
    df_1h.to_csv(output_file, index=False)
    print(f"\n✅ Saved to {output_file}")
    print(f"   Rows: {len(df_1h):,}")
    print(f"   Date range: {df_1h.iloc[0]['timestamp']} to {df_1h.iloc[-1]['timestamp']}")
    
    # Download 5M data (for MTF Scalper base)
    print("\n" + "="*70)
    print("2️⃣ DOWNLOADING 5M DATA")
    print("="*70)
    
    df_5m = download_cryptodatadownload('5m')
    if df_5m is None or len(df_5m) < 100000:
        print("   Falling back to Binance API...")
        # For 5M, get last 3 years (older data may not be available)
        df_5m = download_binance_data('BTCUSDT', '5m', '2022-01-01', '2025-12-30')
    
    output_file = 'training/data/BTC_5m_10y.csv'
    df_5m.to_csv(output_file, index=False)
    print(f"\n✅ Saved to {output_file}")
    print(f"   Rows: {len(df_5m):,}")
    print(f"   Date range: {df_5m.iloc[0]['timestamp']} to {df_5m.iloc[-1]['timestamp']}")
    
    # Download 15M data (for MTF Scalper context)
    print("\n" + "="*70)
    print("3️⃣ DOWNLOADING 15M DATA")
    print("="*70)
    
    df_15m = download_cryptodatadownload('15m')
    if df_15m is None or len(df_15m) < 100000:
        print("   Falling back to Binance API...")
        df_15m = download_binance_data('BTCUSDT', '15m', '2022-01-01', '2025-12-30')
    
    output_file = 'training/data/BTC_15m_10y.csv'
    df_15m.to_csv(output_file, index=False)
    print(f"\n✅ Saved to {output_file}")
    print(f"   Rows: {len(df_15m):,}")
    print(f"   Date range: {df_15m.iloc[0]['timestamp']} to {df_15m.iloc[-1]['timestamp']}")
    
    # Summary
    print("\n" + "="*70)
    print("📊 DOWNLOAD SUMMARY")
    print("="*70)
    print(f"1H data:  {len(df_1h):,} candles")
    print(f"5M data:  {len(df_5m):,} candles")
    print(f"15M data: {len(df_15m):,} candles")
    print("\n✅ All data downloaded successfully!")
    print("="*70)

if __name__ == '__main__':
    main()
