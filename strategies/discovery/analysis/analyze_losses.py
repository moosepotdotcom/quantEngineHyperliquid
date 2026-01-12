#!/usr/bin/env python3
"""
Analyze market conditions during Jan 6th Loss Streak
"""
import pandas as pd
import numpy as np
import requests
import json
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))
from feature_engineer import add_all_indicators

def fetch_data(start_time, end_time):
    url = 'https://api.hyperliquid.xyz/info'
    payload = {
        'type': 'candleSnapshot',
        'req': {'coin': 'BTC', 'interval': '5m', 'startTime': start_time, 'endTime': end_time}
    }
    resp = requests.post(url, json=payload)
    data = resp.json()
    df_data = []
    for candle in data:
        df_data.append([candle['t'], float(candle['o']), float(candle['h']), float(candle['l']), float(candle['c']), float(candle['v'])])
    df = pd.DataFrame(df_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def main():
    # Jan 6th 16:00 to 19:00 (Loss streak was 17:05 - 17:40)
    start_dt = datetime(2026, 1, 6, 12, 0, 0) # Lookback for indicators
    end_dt = datetime(2026, 1, 6, 20, 0, 0)
    
    start_ts = int(start_dt.timestamp() * 1000)
    end_ts = int(end_dt.timestamp() * 1000)
    
    print(f"📊 Analyzing Market Conditions: {start_dt} - {end_dt}")
    
    df = fetch_data(start_ts, end_ts)
    df = add_all_indicators(df)
    df.set_index('timestamp', inplace=True)
    
    # Filter to the loss period
    focus_start = datetime(2026, 1, 6, 17, 0, 0)
    focus_end = datetime(2026, 1, 6, 18, 0, 0)
    
    subset = df[(df.index >= focus_start) & (df.index <= focus_end)]
    
    print("\n🔍 Market Conditions during Loss Streak (Short Signals):")
    print(f"{'Time':<20} {'Price':<10} {'EMA_50':<10} {'EMA_200':<10} {'RSI':<6} {'ADX':<6} {'Tremd':<10}")
    print("-" * 80)
    
    for idx, row in subset.iterrows():
        ema50 = row['ema_50']
        ema200 = row['ema_200']
        price = row['close']
        
        trend = "BEAR" if price < ema200 else "BULL"
        if price < ema50 and price > ema200: trend = "PULLBACK"
        
        print(f"{idx.strftime('%H:%M'):<20} "
              f"{price:<10.1f} "
              f"{ema50:<10.1f} "
              f"{ema200:<10.1f} "
              f"{row['rsi_14']:<6.1f} "
              f"{row['adx_14']:<6.1f} "
              f"{trend:<10}")

    print("\n💡 Hypothesis:")
    print("If price was ABOVE EMA 200, it was an UPTREND.")
    print("Shorting in an UPTREND is risky. An EMA 200 Trend Filter would prevent this.")

if __name__ == '__main__':
    main()
