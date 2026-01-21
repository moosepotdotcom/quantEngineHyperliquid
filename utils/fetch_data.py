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
        
        # Keep Taker Buy Base Asset Volume for V5 Features
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'taker_buy_base']]
        
        df = df.astype({
            'open': float, 'high': float, 'low': float, 
            'close': float, 'volume': float,
            'taker_buy_base': float
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

def fetch_live_data(symbol="BTC", interval="1h", limit=1000):
    """
    Fetch live data from Hyperliquid for trading engine.
    Compatible with existing quant_engine interface.
    """
    url = "https://api.hyperliquid.xyz/info"
    
    # Map interval to milliseconds
    tf_map = {
        '1m': 60000, '3m': 180000, '5m': 300000, '15m': 900000, 
        '30m': 1800000, '1h': 3600000, '4h': 14400000, '1d': 86400000
    }
    
    ms_per_candle = tf_map.get(interval, 3600000)
    duration_ms = limit * ms_per_candle
    
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - duration_ms
    
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": symbol,
            "interval": interval,
            "startTime": start_ms,
            "endTime": now_ms
        }
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        
        if not data:
            return pd.DataFrame()
            
        df = pd.DataFrame(data)
        # Rename columns to match engine expectations
        df.rename(columns={
            't': 'timestamp',
            'o': 'open',
            'h': 'high',
            'l': 'low',
            'c': 'close',
            'v': 'volume'
        }, inplace=True)
        
        # Convert types
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        cols = ['open', 'high', 'low', 'close', 'volume']
        for c in cols:
            df[c] = df[c].astype(float)
            
        return df[['timestamp'] + cols]
        
    except Exception as e:
        print(f"❌ Error fetching live data: {e}")
        return pd.DataFrame()
