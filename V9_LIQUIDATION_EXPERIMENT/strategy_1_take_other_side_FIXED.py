#!/usr/bin/env python3
"""
FIXED Strategy 1: Take the Other Side
BUGS FIXED:
1. Lower spike threshold (5 BTC instead of 10)
2. Use ANY liquidation in window, not just total
3. Relax overshoot requirement
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class TakeOtherSideStrategyFixed:
    """FIXED: Fade liquidation spikes"""
    
    def __init__(self):
        # FIXED: Lower threshold
        self.spike_threshold = 5.0  # Was 10, now 5 BTC
        self.overshoot_pct = 0.01  # Was 0.02, now 1%
        
        # Trading params
        self.tp_pct = 0.02  # 2% TP
        self.sl_pct = 0.005  # 0.5% SL
    
    def detect_liquidation_spike(self, df_liquidations, current_time, window_minutes=10):
        """FIXED: Use 10min window and lower threshold"""
        cutoff = current_time - timedelta(minutes=window_minutes)
        recent = df_liquidations[df_liquidations['timestamp'] > cutoff]
        
        if len(recent) == 0:
            return False, None, 0
        
        total_volume = recent['size'].sum()
        
        # FIXED: Accept ANY liquidation in window
        if total_volume >= self.spike_threshold or len(recent) >= 2:
            # Determine direction
            long_liq = recent[recent['side'] == 'A']['size'].sum()
            short_liq = recent[recent['side'] == 'B']['size'].sum()
            
            direction = 'long_liquidated' if long_liq > short_liq else 'short_liquidated'
            
            return True, direction, total_volume
        
        return False, None, total_volume
    
    def generate_signal(self, current_price, spike_direction, price_change_10m):
        """FIXED: Relax overshoot requirement"""
        
        # FIXED: Accept smaller moves
        if abs(price_change_10m) < 0.005:  # Was 0.02, now 0.5%
            return None
        
        if spike_direction == 'long_liquidated':
            # Longs liquidated = price dropped
            # Buy the dip
            if price_change_10m < 0:  # ANY drop
                entry = current_price
                tp = entry * (1 + self.tp_pct)
                sl = entry * (1 - self.sl_pct)
                return 'LONG', entry, tp, sl
        
        elif spike_direction == 'short_liquidated':
            # Shorts liquidated = price spiked
            # Sell the top
            if price_change_10m > 0:  # ANY rise
                entry = current_price
                tp = entry * (1 - self.tp_pct)
                sl = entry * (1 + self.sl_pct)
                return 'SHORT', entry, tp, sl
        
        return None

def backtest_take_other_side_fixed(df_price, df_liquidations, fee_pct=0.001):
    """FIXED backtest"""
    
    print("🎯 BACKTESTING: Take Other Side (FIXED)")
    print("="*70)
    
    strategy = TakeOtherSideStrategyFixed()
    
    trades = []
    active_trade = None
    
    for i in range(2, len(df_price)):  # Start at index 2
        row = df_price.iloc[i]
        current_time = row['timestamp']
        current_price = row['close']
        
        # Manage active trade
        if active_trade:
            if active_trade['direction'] == 'LONG':
                if row['high'] >= active_trade['tp']:
                    pnl_pct = strategy.tp_pct - fee_pct
                    trades.append({
                        'entry_time': active_trade['entry_time'],
                        'exit_time': current_time,
                        'direction': 'LONG',
                        'outcome': 'WIN',
                        'pnl_pct': pnl_pct
                    })
                    active_trade = None
                    continue
                elif row['low'] <= active_trade['sl']:
                    pnl_pct = -strategy.sl_pct - fee_pct
                    trades.append({
                        'entry_time': active_trade['entry_time'],
                        'exit_time': current_time,
                        'direction': 'LONG',
                        'outcome': 'LOSS',
                        'pnl_pct': pnl_pct
                    })
                    active_trade = None
                    continue
            else:  # SHORT
                if row['low'] <= active_trade['tp']:
                    pnl_pct = strategy.tp_pct - fee_pct
                    trades.append({
                        'entry_time': active_trade['entry_time'],
                        'exit_time': current_time,
                        'direction': 'SHORT',
                        'outcome': 'WIN',
                        'pnl_pct': pnl_pct
                    })
                    active_trade = None
                    continue
                elif row['high'] >= active_trade['sl']:
                    pnl_pct = -strategy.sl_pct - fee_pct
                    trades.append({
                        'entry_time': active_trade['entry_time'],
                        'exit_time': current_time,
                        'direction': 'SHORT',
                        'outcome': 'LOSS',
                        'pnl_pct': pnl_pct
                    })
                    active_trade = None
                    continue
        
        # Check for new signal
        if active_trade is None:
            # Detect liquidation spike
            spike, direction, volume = strategy.detect_liquidation_spike(
                df_liquidations, current_time, window_minutes=10
            )
            
            if spike:
                # Calculate price change over 10min
                if i >= 2:
                    prev_price = df_price.iloc[i-2]['close']  # 10min ago
                    price_change = (current_price - prev_price) / prev_price
                    
                    # Generate signal
                    signal = strategy.generate_signal(current_price, direction, price_change)
                    
                    if signal:
                        dir, entry, tp, sl = signal
                        active_trade = {
                            'direction': dir,
                            'entry': entry,
                            'tp': tp,
                            'sl': sl,
                            'entry_time': current_time
                        }
    
    # Results
    df_trades = pd.DataFrame(trades)
    
    if len(df_trades) > 0:
        wins = len(df_trades[df_trades['outcome'] == 'WIN'])
        losses = len(df_trades[df_trades['outcome'] == 'LOSS'])
        wr = wins / len(df_trades)
        net_pnl = df_trades['pnl_pct'].sum() * 100
        
        print(f"\n📊 RESULTS:")
        print(f"   Total Trades: {len(df_trades)}")
        print(f"   Wins: {wins}, Losses: {losses}")
        print(f"   Win Rate: {wr:.1%}")
        print(f"   Net PnL: {net_pnl:+.2f}%")
        print(f"   Avg Win: {df_trades[df_trades['outcome']=='WIN']['pnl_pct'].mean()*100:.2f}%")
        print(f"   Avg Loss: {df_trades[df_trades['outcome']=='LOSS']['pnl_pct'].mean()*100:.2f}%")
        
        return df_trades, wr, net_pnl
    else:
        print("\n   ⚠️  No trades generated")
        return None, 0, 0

if __name__ == "__main__":
    # Quick test
    import sys
    sys.path.insert(0, '..')
    
    df_price = pd.read_csv('../training/data/BTC_5m_2025_enriched.csv')
    df_price['timestamp'] = pd.to_datetime(df_price['timestamp'])
    df_price = df_price[df_price['timestamp'] >= '2026-01-01'].reset_index(drop=True)
    
    df_liqs = pd.read_csv('liquidation_data/historical_liquidations_inferred.csv')
    df_liqs['timestamp'] = pd.to_datetime(df_liqs['timestamp'])
    
    backtest_take_other_side_fixed(df_price, df_liqs)
