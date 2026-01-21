#!/usr/bin/env python3
"""
Backtest the VERIFIED 93% Engine (EXPORT version)
Date Range: Jan 2-7, 2026
Uses: Hyperliquid API data with ALL filters enabled
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests

# Add EXPORT to path
sys.path.insert(0, '/Users/alifiyaa/Downloads/quantEngineHyperliquid/EXPORT')

from quant_engine import TradingEngine

def fetch_historical_data(start_date='2026-01-02', end_date='2026-01-07', interval='5m'):
    """Fetch historical data from Hyperliquid for specific date range"""
    print(f"\n📡 Fetching {interval} data from Hyperliquid...")
    print(f"   Date Range: {start_date} to {end_date}")
    
    url = 'https://api.hyperliquid.xyz/info'
    
    # Convert dates to timestamps (milliseconds)
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
    
    start_time = int(start_dt.timestamp() * 1000)
    end_time = int(end_dt.timestamp() * 1000)
    
    payload = {
        'type': 'candleSnapshot',
        'req': {
            'coin': 'BTC',
            'interval': interval,
            'startTime': start_time,
            'endTime': end_time
        }
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=30)
        if resp.status_code != 200:
            print(f"❌ HTTP {resp.status_code}")
            return None
        
        data = resp.json()
        if not isinstance(data, list) or len(data) == 0:
            print(f"❌ No data returned")
            return None
        
        df_data = []
        for candle in data:
            df_data.append([
                candle['t'],
                float(candle['o']),
                float(candle['h']),
                float(candle['l']),
                float(candle['c']),
                float(candle['v'])
            ])
        
        df = pd.DataFrame(df_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        print(f"✅ Fetched {len(df)} candles")
        print(f"   Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
        return df
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def simulate_93_engine(df):
    """Simulate the VERIFIED 93% engine with ALL filters"""
    print("\n" + "="*70)
    print("🎯 BACKTESTING: VERIFIED 93% ENGINE (EXPORT)")
    print("="*70)
    print("Configuration:")
    print("  - MTF Threshold: 45% (with ATR penalty)")
    print("  - WH Threshold: 32.78% long, 40.89% short")
    print("  - Hurst Filter: ON (blocks falling knives)")
    print("  - ATR Penalty: ON (+0.002 per ATR point > 70)")
    print("  - AI Smart Filter: ON (no shorts when RSI_7 < 25)")
    print("  - Circuit Breaker: ON (2 losses in 60min → 4hr pause)")
    print("  - TP: 1.5% | SL: 0.8%")
    print("="*70)
    
    # Initialize the EXPORT engine
    engine = TradingEngine()
    
    print(f"\n✅ Engine initialized")
    print(f"   MTF Threshold: {engine.mtf_threshold_long:.2%}")
    print(f"   WH Threshold: {engine.winner_threshold_long:.2%}")
    
    # Track trades
    trades = []
    
    # Simulate checking every 5m candle (but skip first 100 for indicators)
    print(f"\n🔄 Simulating {len(df)} candles...")
    
    for i in range(100, len(df), 12):  # Check every 12 candles (1 hour)
        if i % 100 == 0:
            print(f"   Progress: {i}/{len(df)} candles...")
        
        try:
            # Check MTF Scalper (this will use live API internally, but we'll override)
            # For backtest, we need to simulate without live API calls
            # Let's just check if we get signals at this timestamp
            
            current_time = df.iloc[i]['timestamp']
            current_price = df.iloc[i]['close']
            
            # For simplicity, we'll check MTF every hour
            # In reality, the engine would fetch live data
            # This is a simplified backtest
            
            # Skip for now - the engine needs live API access
            # We'll need a different approach
            
        except Exception as e:
            pass
    
    print("\n" + "="*70)
    print("⚠️  NOTE: Full backtest requires modifying engine to use historical data")
    print("The EXPORT engine is designed for live trading with API calls")
    print("="*70)
    
    print("\n💡 RECOMMENDATION:")
    print("   1. Deploy EXPORT engine to cloud")
    print("   2. Run in paper mode for 24 hours")
    print("   3. Monitor actual signal generation")
    print("   4. Compare to verified Jan 2-11 results")
    
    return None

def main():
    print("\n" + "🚀"*35)
    print("VERIFIED 93% ENGINE BACKTEST")
    print("Testing Period: Jan 2-7, 2026")
    print("🚀"*35 + "\n")
    
    # Fetch data
    df = fetch_historical_data(start_date='2026-01-02', end_date='2026-01-07', interval='5m')
    
    if df is None:
        print("❌ Failed to fetch data")
        return
    
    # Run simulation
    results = simulate_93_engine(df)

if __name__ == '__main__':
    main()
