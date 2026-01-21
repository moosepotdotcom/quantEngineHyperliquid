#!/usr/bin/env python3
"""
Williams %R (140) Strategy Backtest
-----------------------------------
Period: 140
Long Signal: Williams %R crosses ABOVE -18
Short Signal: Williams %R crosses BELOW -80

Data: training/data/BTC_Jan2_11_2026_Hyperliquid.csv
"""

import pandas as pd
import numpy as np
import ta
import os
import sys

# --- CONFIGURATION ---
DATA_FILE = 'training/data/BTC_Jan2_11_2026_Hyperliquid.csv'
PERIOD = 140
LONG_THRESH = -25
SHORT_THRESH = -80

# Trading Params (Optimized)
TP_PCT = 0.010  # 1.0%
SL_PCT = 0.005  # 0.5%
FEE_PCT = 0.00035 

def calculate_williams_r(df, period=14):
    """
    Calculate Williams %R
    """
    highest_high = df['high'].rolling(window=period).max()
    lowest_low = df['low'].rolling(window=period).min()
    
    denominator = highest_high - lowest_low
    denominator = denominator.replace(0, np.nan) 
    
    wr = -100 * (highest_high - df['close']) / denominator
    return wr

def run_backtest():
    if not os.path.exists(DATA_FILE):
        print(f"❌ Error: Data file not found at {DATA_FILE}")
        return

    print(f"📥 Loading data from {DATA_FILE}...")
    df = pd.read_csv(DATA_FILE)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Sort just in case
    df.sort_values('timestamp', inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    print(f"✅ Loaded {len(df)} candles.")

    # --- Feature Engineering ---
    print(f"🔧 Calculating Features (Williams %R {PERIOD}, EMA 200, Vol)...")
    df['williams_r'] = calculate_williams_r(df, PERIOD)
    df['williams_r_prev'] = df['williams_r'].shift(1)
    
    # Trend Filter
    df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # Volume Filter
    df['vol_sma_20'] = df['volume'].rolling(20).mean()

    # --- Backtest Loop ---
    print("🚀 Starting Simulation (Optimized)...")
    
    trades = []
    position = None 
    
    for i in range(200, len(df)): # Start after 200 for EMA
        row = df.iloc[i]
        curr_wr = row['williams_r']
        prev_wr = row['williams_r_prev']
        
        if pd.isna(curr_wr) or pd.isna(prev_wr):
            continue
            
        # 1. Manage Open Position
        if position:
            outcome = None
            exit_price = 0
            
            if position['type'] == 'LONG':
                if row['high'] >= position['tp']:
                    outcome = 'WIN'; exit_price = position['tp']
                elif row['low'] <= position['sl']:
                    outcome = 'LOSS'; exit_price = position['sl']
            elif position['type'] == 'SHORT':
                if row['low'] <= position['tp']:
                    outcome = 'WIN'; exit_price = position['tp']
                elif row['high'] >= position['sl']:
                    outcome = 'LOSS'; exit_price = position['sl']
            
            if outcome:
                pnl_raw = (exit_price - position['entry']) / position['entry']
                if position['type'] == 'SHORT': pnl_raw = -pnl_raw
                pnl_net = pnl_raw - (FEE_PCT * 2)
                
                trades.append({
                    'entry_time': position['time'],
                    'exit_time': row['timestamp'],
                    'type': position['type'],
                    'outcome': outcome,
                    'pnl': pnl_net,
                    'price': position['entry']
                })
                position = None
            continue 

        # 2. Check Signals
        
        # Filters
        is_uptrend = row['close'] > row['ema_200']
        is_downtrend = row['close'] < row['ema_200']
        
        # Volume Surge (> 1.5x)
        vol_ok = row['volume'] > (1.5 * row['vol_sma_20'])
        
        if not vol_ok: continue
            
        # Long Signal
        # Trend: OFF (Based on Opt) or ON?
        # Opt said: Trend=True, Vol=True, TP/SL=1.0/0.5 is Robust (+2.31%, 17 trades)
        
        if is_uptrend and prev_wr < LONG_THRESH and curr_wr >= LONG_THRESH:
            entry = row['close']
            position = {
                'type': 'LONG',
                'entry': entry,
                'tp': entry * (1 + TP_PCT),
                'sl': entry * (1 - SL_PCT),
                'time': row['timestamp']
            }

        # Short Signal
        elif is_downtrend and prev_wr > SHORT_THRESH and curr_wr <= SHORT_THRESH:
            entry = row['close']
            position = {
                'type': 'SHORT',
                'entry': entry,
                'tp': entry * (1 - TP_PCT),
                'sl': entry * (1 + SL_PCT),
                'time': row['timestamp']
            }

    # --- Results ---
    if not trades:
        print("⚠️  No trades executed.")
        return

    df_trades = pd.DataFrame(trades)
    
    total_trades = len(df_trades)
    wins = len(df_trades[df_trades['outcome'] == 'WIN'])
    win_rate = (wins / total_trades) * 100
    total_pnl = df_trades['pnl'].sum() * 100
    
    print("\n" + "="*50)
    print(f"📊 OPTIMIZED WILLIAMS %R ({PERIOD}) RESULTS")
    print("="*50)
    print(f"Total Trades: {total_trades}")
    print(f"Win Rate:     {win_rate:.2f}%")
    print(f"Total PnL:    {total_pnl:.2f}%")
    
    days = (df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]).days
    if days > 0:
        print(f"Trades/Day:   {total_trades / days:.1f}")

    print("\nRecent Trades:")
    print(df_trades.tail().to_string(index=False))

if __name__ == "__main__":
    run_backtest()
