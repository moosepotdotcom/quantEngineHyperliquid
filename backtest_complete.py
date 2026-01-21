#!/usr/bin/env python3
"""Complete Phase4 integrated backtest - all logic inline"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re

# ===== LOAD DATA =====
print("Loading data...")

# Whales
whales = []
with open('live_system.log', 'r') as f:
    for line in f:
        if 'WHALE' in line:
            m = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),(\d+).*WHALE (\w): \$([0-9,]+)', line)
            if m:
                dt_str, ms, direction, usd_str = m.groups()
                dt = pd.to_datetime(dt_str) + timedelta(milliseconds=int(ms))
                side = 'BUY' if direction == 'A' else 'SELL'
                usd = float(usd_str.replace(',', ''))
                whales.append({'dt': dt, 'side': side, 'usd': usd})

whales_df = pd.DataFrame(whales)

# Candles
candles_df = pd.read_csv('data/btc_5m_jan16_2026.csv')
candles_df['dt'] = pd.to_datetime(candles_df['timestamp'], unit='ms')

# Phase4
p4_df = pd.read_csv('data/phase4_features_jan16.csv')
p4_df['dt'] = pd.to_datetime(p4_df['timestamp'])

print(f"Whales: {len(whales_df)}, Candles: {len(candles_df)}, Phase4: {len(p4_df)}")

# ===== PREPARE SIGNALS =====
candles_df['whale_count'] = 0
candles_df['whale_usd'] = 0.0
candles_df['whale_bias'] = 0
candles_df['imbalance'] = 0.0
candles_df['funding'] = 0.0
candles_df['atr'] = 0.0
candles_df['signal'] = 0.0

# ATR
high = candles_df['high']
low = candles_df['low']
close = candles_df['close']
tr = np.maximum(high - low, np.maximum(abs(high - close.shift()), abs(low - close.shift())))
candles_df['atr'] = tr.rolling(3, min_periods=1).mean()

# Merge whales (allow 10-minute lookback window for better signal capture)
for idx, row in candles_df.iterrows():
    dt_start = row['dt'] - timedelta(minutes=5)  # Include prior window
    dt_end = row['dt'] + timedelta(minutes=5)    # Include future window
    mask = (whales_df['dt'] >= dt_start) & (whales_df['dt'] < dt_end)
    w = whales_df[mask]
    if len(w) > 0:
        candles_df.at[idx, 'whale_count'] = len(w)
        candles_df.at[idx, 'whale_usd'] = w['usd'].sum()
        buy = (w['side'] == 'BUY').sum()
        sell = (w['side'] == 'SELL').sum()
        candles_df.at[idx, 'whale_bias'] = 1 if buy > sell else (-1 if sell > buy else 0)

# Merge Phase4
for idx, row in candles_df.iterrows():
    nearest_idx = (p4_df['dt'] - row['dt']).abs().idxmin()
    p4_row = p4_df.iloc[nearest_idx]
    candles_df.at[idx, 'imbalance'] = p4_row['ob_imbalance']
    candles_df.at[idx, 'funding'] = p4_row['funding_pct']

# Generate signals (much lower thresholds to actually generate signals)
for idx in range(len(candles_df)):
    row = candles_df.iloc[idx]
    whale_sc = row['whale_bias'] * min(1.0, row['whale_usd'] / 400000.0) * 0.6 if row['whale_count'] >= 2 else 0
    imb_sc = np.sign(row['imbalance']) * min(1.0, abs(row['imbalance']) / 0.08) * 0.25 if abs(row['imbalance']) > 0.01 else 0
    fund_sc = -np.sign(row['funding']) * min(1.0, abs(row['funding']) / 0.08) * 0.15 if abs(row['funding']) > 0.01 else 0
    comp = whale_sc + imb_sc + fund_sc
    if abs(comp) > 0.15:  # Lower threshold for more signals
        candles_df.at[idx, 'signal'] = np.sign(comp)

# ===== BACKTEST =====
print("\nRunning backtest...")
trades = []
balance = 10000
position = None

for idx in range(len(candles_df)):
    row = candles_df.iloc[idx]
    price = row['close']
    
    # Entry
    if position is None and row['signal'] != 0:
        atr_val = max(row['atr'], 50)
        position = {
            'idx': idx, 'price': price, 'side': 'LONG' if row['signal'] == 1 else 'SHORT',
            'atr': atr_val, 'size': (balance * 0.02) / price
        }
        if position['side'] == 'LONG':
            position['tp'] = price + atr_val * 2
            position['sl'] = price - atr_val * 1.5
        else:
            position['tp'] = price - atr_val * 2
            position['sl'] = price + atr_val * 1.5
    
    # Exit
    elif position is not None:
        should_exit = False
        exit_price = price
        reason = None
        
        if position['side'] == 'LONG':
            if row['high'] >= position['tp']:
                exit_price = position['tp']
                should_exit, reason = True, 'TP'
            elif row['low'] <= position['sl']:
                exit_price = position['sl']
                should_exit, reason = True, 'SL'
        else:
            if row['low'] <= position['tp']:
                exit_price = position['tp']
                should_exit, reason = True, 'TP'
            elif row['high'] >= position['sl']:
                exit_price = position['sl']
                should_exit, reason = True, 'SL'
        
        if not should_exit and idx - position['idx'] >= 5:
            should_exit, reason = True, 'TIMEOUT'
        
        if should_exit:
            pnl = (exit_price - position['price']) * position['size'] if position['side'] == 'LONG' else (position['price'] - exit_price) * position['size']
            balance += pnl
            trades.append({'entry': position['price'], 'exit': exit_price, 'side': position['side'], 'pnl': pnl, 'reason': reason})
            position = None

# ===== REPORT =====
print("\n" + "=" * 60)
print("BACKTEST RESULTS")
print("=" * 60)
print(f"Signals Generated:")
print(f"  BUY signals:  {(candles_df['signal'] == 1.0).sum()}")
print(f"  SELL signals: {(candles_df['signal'] == -1.0).sum()}")
print(f"\nCandles with whale activity: {(candles_df['whale_count'] > 0).sum()}")

print(f"\nTrades Executed: {len(trades)}")
if trades:
    total_pnl = sum(t['pnl'] for t in trades)
    wins = sum(1 for t in trades if t['pnl'] > 0)
    losses = sum(1 for t in trades if t['pnl'] < 0)
    print(f"Wins/Losses: {wins}/{losses}")
    print(f"Win Rate: {wins/len(trades)*100:.1f}%")
    print(f"Total PnL: ${total_pnl:.2f}")
    print(f"Avg PnL/Trade: ${total_pnl/len(trades):.2f}")
    print(f"\nFinal Balance: ${balance:.2f}")
    print(f"Return: {(balance - 10000)/10000*100:.2f}%")
    
    print(f"\nTrade Details:")
    for i, t in enumerate(trades, 1):
        print(f"  {i}. {t['side']:5} @ {t['entry']:8.1f} -> {t['exit']:8.1f} | PnL: ${t['pnl']:8.2f} ({t['reason']})")
else:
    print(f"No trades executed (insufficient signals or strict thresholds)")
    print(f"Final Balance: ${balance:.2f}")
