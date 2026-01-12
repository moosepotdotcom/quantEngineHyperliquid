#!/usr/bin/env python3
"""
🌐 Multi-Source Data Fetcher
Pulls BTC/USD data across all timeframes from multiple sources.
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import time

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# Timeframes to fetch
TIMEFRAMES = ['1m', '3m', '5m', '15m', '30m', '1h', '4h', '1d']

def fetch_binance(symbol='BTCUSDT', interval='1h', limit=1000):
    """Fetch OHLCV from Binance public API"""
    url = 'https://api.binance.com/api/v3/klines'
    params = {
        'symbol': symbol,
        'interval': interval,
        'limit': limit
    }
    
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        df = df.astype({
            'open': float, 'high': float, 'low': float, 
            'close': float, 'volume': float
        })
        
        return df
    except Exception as e:
        print(f"❌ Binance Error ({interval}): {e}")
        return None

def fetch_all_timeframes(symbol='BTCUSDT', limit=1000):
    """Fetch all timeframes and save to CSV"""
    print(f"🌐 Fetching {symbol} data across {len(TIMEFRAMES)} timeframes...")
    
    for tf in TIMEFRAMES:
        print(f"   📥 Fetching {tf}...", end=" ")
        df = fetch_binance(symbol, tf, limit)
        
        if df is not None and len(df) > 0:
            filepath = os.path.join(DATA_DIR, f'BTC_{tf}.csv')
            df.to_csv(filepath, index=False)
            print(f"✅ {len(df)} bars saved")
        else:
            print(f"⚠️ Failed")
        
        time.sleep(0.5)  # Rate limit protection
    
    print("\n🎉 Data fetch complete!")
    return True

def load_data(timeframe):
    """Load data for a specific timeframe"""
    filepath = os.path.join(DATA_DIR, f'BTC_{timeframe}.csv')
    if os.path.exists(filepath):
        df = pd.read_csv(filepath)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    return None

if __name__ == '__main__':
    fetch_all_timeframes(limit=1000)  # ~1000 bars per TF
