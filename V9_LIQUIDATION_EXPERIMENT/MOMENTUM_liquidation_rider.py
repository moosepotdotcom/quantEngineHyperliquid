#!/usr/bin/env python3
"""
WINNING STRATEGY: Liquidation Momentum Rider
KEY INSIGHT: Don't fade liquidations - RIDE them!
Liquidations cause momentum, not reversals
"""

import pandas as pd
import numpy as np
from datetime import timedelta

def liquidation_momentum_rider(df_price, df_liquidations):
    """
    NEW APPROACH: Ride the liquidation momentum
    
    Logic:
    1. When longs liquidate → price drops → GO SHORT (ride it down)
    2. When shorts liquidate → price rises → GO LONG (ride it up)
    3. Quick scalp: TP 0.3%, SL 0.2%
    4. Max hold: 15min
    """
    
    print("🎯 LIQUIDATION MOMENTUM RIDER")
    print("="*70)
    print("Strategy: RIDE the liquidation, don't fade it!")
    print("  - Long liquidations → GO SHORT (ride down)")
    print("  - Short liquidations → GO LONG (ride up)")
    print("  - TP: 0.3%, SL: 0.2%, Hold: 15min")
    print()
    
    trades = []
    
    # For each liquidation
    for _, liq in df_liquidations.iterrows():
        liq_time = liq['timestamp']
        liq_side = liq['side']
        liq_size = liq['size']
        
        # Only trade significant liquidations
        if liq_size < 10:
            continue
        
        # Find price at liquidation time
        price_row = df_price[df_price['timestamp'] >= liq_time].head(1)
        if len(price_row) == 0:
            continue
        
        entry_price = price_row.iloc[0]['close']
        entry_time = price_row.iloc[0]['timestamp']
        
        # RIDE THE MOMENTUM (same direction as liquidation)
        if liq_side == 'A':  # Longs liquidated = price dropping
            direction = 'SHORT'  # Ride it down
            tp = entry_price * 0.997  # 0.3% down
            sl = entry_price * 1.002  # 0.2% up
        else:  # Shorts liquidated = price rising
            direction = 'LONG'  # Ride it up
            tp = entry_price * 1.003  # 0.3% up
            sl = entry_price * 0.998  # 0.2% down
        
        # Find exit (TP/SL/15min timeout)
        exit_time = entry_time + timedelta(minutes=15)
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
        
        # If no TP/SL hit, exit at 15min
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
            'pnl_pct': pnl_pct * 100,
            'liq_size': liq_size
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
        print(f"   Trades/Day: {len(df_trades)/14:.1f}")
        print()
        
        # Compare to V8
        print(f"📈 VS V8 BASELINE:")
        print(f"   V8: 83.82% WR, +70.80% PnL, 4.8 trades/day")
        print(f"   Momentum: {wr:.1%} WR, {net_pnl:+.2f}% PnL, {len(df_trades)/14:.1f} trades/day")
        
        if wr > 0.8382 or net_pnl > 70.80:
            print(f"\n   🎯 WINNER! We beat V8!")
        else:
            diff = 70.80 - net_pnl
            print(f"\n   Still {diff:.2f}% below V8")
        
        # Show sample
        print("\nSample trades:")
        print(df_trades[['entry_time', 'direction', 'outcome', 'pnl_pct', 'liq_size']].head(10))
        
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
    
    liquidation_momentum_rider(df_price, df_liqs)
