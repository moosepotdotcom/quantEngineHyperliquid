#!/usr/bin/env python3
"""
🎰 EXNESS SIMULATOR (400x LEVERAGE)
Replays `logs/collector_debug.log` with aggressive CFD parameters.
"""

import json
import re
import pandas as pd
from datetime import datetime

LOG_FILE = "logs/collector_debug.log"
MOMENTUM_THRESHOLD_VOL = 500000.0 # Using the optimized threshold
TP_PCT = 0.002
SL_PCT = 0.001
LEVERAGE = 400.0
POSITION_SIZE_BTC = 0.5

def run_simulation():
    # 1. Parse Data
    trades_list = []
    with open(LOG_FILE, 'r') as f:
        for line in f:
            match = re.search(r"data=b'({.*})'", line)
            if match:
                try:
                    data = json.loads(match.group(1))
                    if data.get('channel') == 'trades':
                        for t in data.get('data', []):
                            trades_list.append({
                                'time': int(t['time']),
                                'price': float(t['px']),
                                'size': float(t['sz']),
                                'side': t['side']
                            })
                except:
                    continue
    
    df = pd.DataFrame(trades_list)
    df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
    df = df.sort_values('timestamp')
    df.set_index('timestamp', inplace=True)
    
    # 2. Resample Candles
    ohlcv = df['price'].resample('1T').ohlc()
    ohlcv['vol'] = df['price'].mul(df['size']).resample('1T').sum()
    ohlcv = ohlcv.dropna()
    
    # 3. Sim Loop
    balance_equity = 1000.0 # Starting Cash
    position = None
    trade_log = []
    
    print(f"🎰 EXNESS SIMULATION STARTED")
    print(f"⚙️  Lev: {LEVERAGE}x | Size: {POSITION_SIZE_BTC} BTC")
    print(f"💰 Start Equity: ${balance_equity:,.2f}")
    print("-" * 60)
    
    for i, row in ohlcv.iterrows():
        price = row['close']
        
        # Check Exit
        if position:
            entry = position['entry']
            side = position['side']
            margin = position['margin']
            
            pnl_btc = (price - entry) * POSITION_SIZE_BTC if side == "BUY" else (entry - price) * POSITION_SIZE_BTC
            roe_pct = (pnl_btc / margin) * 100
            
            # Simple TP/SL logic based on price movement %
            price_move = (price - entry) / entry if side == "BUY" else (entry - price) / entry
            
            if price_move >= TP_PCT:
                outcome = "WIN 🟢"
                balance_equity += pnl_btc
                trade_log.append([i, side, entry, price, margin, pnl_btc, roe_pct, balance_equity])
                print(f"{i.time()} {outcome} | PnL: ${pnl_btc:+8.2f} | ROE: {roe_pct:+6.1f}% | Bal: ${balance_equity:,.2f}")
                position = None
            elif price_move <= -SL_PCT:
                outcome = "LOSS 🔴"
                balance_equity += pnl_btc
                trade_log.append([i, side, entry, price, margin, pnl_btc, roe_pct, balance_equity])
                print(f"{i.time()} {outcome} | PnL: ${pnl_btc:+8.2f} | ROE: {roe_pct:+6.1f}% | Bal: ${balance_equity:,.2f}")
                position = None
                
        # Check Entry
        if not position and row['vol'] > MOMENTUM_THRESHOLD_VOL:
            direction = "BUY" if row['close'] > row['open'] else "SELL"
            margin_req = (price * POSITION_SIZE_BTC) / LEVERAGE
            
            # Check if we have enough equity
            if margin_req > balance_equity:
                # print(f"⚠️ Insufficient Margin: Need ${margin_req:.2f}, Have ${balance_equity:.2f}")
                pass
            else:
                position = {
                    'side': direction,
                    'entry': price,
                    'margin': margin_req
                }
                # print(f"🚀 OPEN {direction} @ {price:.0f} | Margin: ${margin_req:.1f}")

    print("-" * 60)
    print(f"🏁 FINAL EQUITY: ${balance_equity:,.2f}")
    pnl_total = balance_equity - 1000
    print(f"📈 TOTAL PnL: ${pnl_total:,.2f} ({pnl_total/10:.1f}%)")

if __name__ == "__main__":
    run_simulation()
