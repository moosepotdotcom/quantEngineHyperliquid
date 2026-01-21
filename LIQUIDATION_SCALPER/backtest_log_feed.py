#!/usr/bin/env python3
"""
🌊 LOG FEED BACKTESTER
Replays `logs/collector_debug.log` to reconstruct market data and test Strategy V2.
"""

import json
import re
import pandas as pd
from datetime import datetime

LOG_FILE = "logs/collector_debug.log"
MOMENTUM_THRESHOLD_VOL = 500000.0
TP_PCT = 0.002
SL_PCT = 0.001

def parse_logs():
    trades_list = []
    print(f"📂 Reading {LOG_FILE}...")
    
    with open(LOG_FILE, 'r') as f:
        for line in f:
            match = re.search(r"data=b'({.*})'", line)
            if match:
                try:
                    data = json.loads(match.group(1))
                    if data.get('channel') == 'trades':
                        for t in data.get('data', []):
                            # {"coin":"BTC","side":"B","px":"95909.0","sz":"0.021","time":1768...}
                            trades_list.append({
                                'time': int(t['time']),
                                'price': float(t['px']),
                                'size': float(t['sz']),
                                'side': t['side']
                            })
                except:
                    continue
                    
    df = pd.DataFrame(trades_list)
    if df.empty:
        print("❌ No trades found in log.")
        return None
        
    df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
    df = df.sort_values('timestamp')
    return df

def run_backtest(df):
    print(f"📊 Processing {len(df)} trades...")
    
    # Resample to 1min Candles
    df.set_index('timestamp', inplace=True)
    ohlcv = df['price'].resample('1T').ohlc()
    ohlcv['vol'] = df['price'].mul(df['size']).resample('1T').sum()
    ohlcv = ohlcv.dropna()
    
    print(f"🕯️ Generated {len(ohlcv)} candles.")
    
    balance = 1000.0
    position = None
    trades = []
    
    for i, row in ohlcv.iterrows():
        # Strategy V2: Momentum Spike
        # If Vol > Threshold -> Follow Trend
        
        # 1. Check Exit
        if position:
            entry = position['entry']
            side = position['side']
            curr_price = row['close']
            
            pnl_pct = (curr_price - entry) / entry if side == "BUY" else (entry - curr_price) / entry
            
            if pnl_pct >= TP_PCT:
                result = "WIN"
                pnl = position['size'] * pnl_pct
                balance += pnl
                trades.append({'time': i, 'type': 'TP', 'pnl': pnl})
                position = None
            elif pnl_pct <= -SL_PCT:
                result = "LOSS"
                pnl = position['size'] * pnl_pct
                balance += pnl
                trades.append({'time': i, 'type': 'SL', 'pnl': pnl})
                position = None
                
        # 2. Check Entry
        if not position and row['vol'] > MOMENTUM_THRESHOLD_VOL:
            # Trend Direction
            direction = "BUY" if row['close'] > row['open'] else "SELL"
            position = {'side': direction, 'entry': row['close'], 'size': 1000}
            trades.append({'time': i, 'type': 'OPEN', 'side': direction})
            
    # Final Report
    print("\n" + "="*40)
    print("🧪 BACKTEST RESULT (LOG REPLAY)")
    print(f"💰 Final Balance: ${balance:,.2f}")
    print(f"📈 Profit: ${balance - 1000:,.2f}")
    print(f"🔢 Trades: {len([t for t in trades if t['type'] in ['TP','SL']])}")
    print("="*40)
    
    for t in trades:
        print(t)

if __name__ == "__main__":
    df = parse_logs()
    if df is not None:
        run_backtest(df)
