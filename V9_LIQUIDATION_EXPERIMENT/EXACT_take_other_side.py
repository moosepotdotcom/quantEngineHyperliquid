#!/usr/bin/env python3
"""
EXACT REPLICATION: "Take the Other Side" Strategy
From research: Wait for large liquidation, enter opposite direction
Simple, proven approach - no overthinking
"""

import pandas as pd
import numpy as np
from datetime import timedelta

def simple_take_other_side(df_price, df_liquidations):
    """
    EXACT STRATEGY FROM RESEARCH:
    1. Wait for liquidation event (ANY size)
    2. Enter OPPOSITE direction immediately
    3. TP: 1%, SL: 0.5%
    4. Hold max 30min
    """
    
    print("🎯 EXACT REPLICATION: Take the Other Side")
    print("="*70)
    print("Rules:")
    print("  1. ANY liquidation triggers signal")
    print("  2. Enter OPPOSITE direction")
    print("  3. TP: 1%, SL: 0.5%, Max hold: 30min")
    print()
    
    trades = []
    
    # For each liquidation
    for _, liq in df_liquidations.iterrows():
        liq_time = liq['timestamp']
        liq_side = liq['side']
        
        # Find price at liquidation time
        price_row = df_price[df_price['timestamp'] >= liq_time].head(1)
        if len(price_row) == 0:
            continue
        
        entry_price = price_row.iloc[0]['close']
        entry_time = price_row.iloc[0]['timestamp']
        
        # Determine direction (OPPOSITE of liquidation)
        if liq_side == 'A':  # Longs liquidated
            direction = 'LONG'  # Buy the dip
            tp = entry_price * 1.01
            sl = entry_price * 0.995
        else:  # Shorts liquidated
            direction = 'SHORT'  # Sell the top
            tp = entry_price * 0.99
            sl = entry_price * 1.005
        
        # Find exit (TP/SL/30min timeout)
        exit_time = entry_time + timedelta(minutes=30)
        future = df_price[
            (df_price['timestamp'] > entry_time) &
            (df_price['timestamp'] <= exit_time)
        ]
        
        if len(future) == 0:
            continue
        
        # Check each candle for TP/SL
        outcome = None
        exit_price = None
        actual_exit_time = None
        
        for _, candle in future.iterrows():
            if direction == 'LONG':
                if candle['high'] >= tp:
                    outcome = 'WIN'
                    exit_price = tp
                    actual_exit_time = candle['timestamp']
                    break
                elif candle['low'] <= sl:
                    outcome = 'LOSS'
                    exit_price = sl
                    actual_exit_time = candle['timestamp']
                    break
            else:  # SHORT
                if candle['low'] <= tp:
                    outcome = 'WIN'
                    exit_price = tp
                    actual_exit_time = candle['timestamp']
                    break
                elif candle['high'] >= sl:
                    outcome = 'LOSS'
                    exit_price = sl
                    actual_exit_time = candle['timestamp']
                    break
        
        # If no TP/SL hit, exit at 30min
        if outcome is None:
            outcome = 'TIMEOUT'
            exit_price = future.iloc[-1]['close']
            actual_exit_time = future.iloc[-1]['timestamp']
        
        # Calculate PnL
        if direction == 'LONG':
            pnl_pct = (exit_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - exit_price) / entry_price
        
        # Subtract fees
        pnl_pct -= 0.001  # 0.1% round-trip
        
        trades.append({
            'entry_time': entry_time,
            'exit_time': actual_exit_time,
            'direction': direction,
            'entry': entry_price,
            'exit': exit_price,
            'outcome': outcome,
            'pnl_pct': pnl_pct * 100
        })
    
    # Results
    df_trades = pd.DataFrame(trades)
    
    if len(df_trades) > 0:
        wins = len(df_trades[df_trades['pnl_pct'] > 0])
        losses = len(df_trades[df_trades['pnl_pct'] <= 0])
        wr = wins / len(df_trades)
        net_pnl = df_trades['pnl_pct'].sum()
        
        print(f"📊 RESULTS:")
        print(f"   Total Trades: {len(df_trades)}")
        print(f"   Wins: {wins}, Losses: {losses}")
        print(f"   Win Rate: {wr:.1%}")
        print(f"   Net PnL: {net_pnl:+.2f}%")
        print(f"   Avg PnL/Trade: {df_trades['pnl_pct'].mean():+.3f}%")
        print()
        
        # Show sample trades
        print("Sample trades:")
        print(df_trades[['entry_time', 'direction', 'outcome', 'pnl_pct']].head(10))
        
        return df_trades, wr, net_pnl
    else:
        print("No trades")
        return None, 0, 0

if __name__ == "__main__":
    # Load data
    df_price = pd.read_csv('../training/data/BTC_5m_2025_enriched.csv')
    df_price['timestamp'] = pd.to_datetime(df_price['timestamp'])
    df_price = df_price[df_price['timestamp'] >= '2026-01-01'].reset_index(drop=True)
    
    df_liqs = pd.read_csv('liquidation_data/historical_liquidations_inferred.csv')
    df_liqs['timestamp'] = pd.to_datetime(df_liqs['timestamp'])
    
    simple_take_other_side(df_price, df_liqs)
