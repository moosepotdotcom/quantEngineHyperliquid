#!/usr/bin/env python3
"""
Strategy 1: Take the Other Side
Wait for liquidation spike, enter opposite direction
Expected WR: 70-80%
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class TakeOtherSideStrategy:
    """Fade liquidation spikes - buy dips, sell tops"""
    
    def __init__(self, spike_threshold_btc=10, overshoot_pct=0.02):
        """
        Args:
            spike_threshold_btc: Minimum BTC liquidated to trigger (default: 10)
            overshoot_pct: Price overshoot to confirm (default: 2%)
        """
        self.spike_threshold = spike_threshold_btc
        self.overshoot_pct = overshoot_pct
        
        # Strategy params
        self.tp_pct = 0.02  # 2% TP
        self.sl_pct = 0.005  # 0.5% SL
    
    def detect_liquidation_spike(self, df_liquidations, current_time, window_minutes=5):
        """
        Detect if liquidation spike occurred in last N minutes
        
        Returns:
            (spike_detected, direction, total_volume)
        """
        cutoff = current_time - timedelta(minutes=window_minutes)
        recent = df_liquidations[df_liquidations['timestamp'] > cutoff]
        
        if len(recent) == 0:
            return False, None, 0
        
        total_volume = recent['size'].sum()
        
        if total_volume >= self.spike_threshold:
            # Determine direction (which side got liquidated more)
            long_liq = recent[recent['side'] == 'A']['size'].sum()
            short_liq = recent[recent['side'] == 'B']['size'].sum()
            
            direction = 'long_liquidated' if long_liq > short_liq else 'short_liquidated'
            
            return True, direction, total_volume
        
        return False, None, total_volume
    
    def generate_signal(self, current_price, spike_direction, price_change_5m):
        """
        Generate trading signal based on liquidation spike
        
        Args:
            current_price: Current BTC price
            spike_direction: 'long_liquidated' or 'short_liquidated'
            price_change_5m: Price change in last 5 minutes (%)
            
        Returns:
            (direction, entry, tp, sl) or None
        """
        # Check if price overshoots
        if abs(price_change_5m) < self.overshoot_pct:
            return None  # Not enough overshoot
        
        if spike_direction == 'long_liquidated':
            # Longs liquidated = price dropped
            # Take OTHER side = BUY the dip
            if price_change_5m < -self.overshoot_pct:
                entry = current_price
                tp = entry * (1 + self.tp_pct)
                sl = entry * (1 - self.sl_pct)
                return 'LONG', entry, tp, sl
        
        elif spike_direction == 'short_liquidated':
            # Shorts liquidated = price spiked
            # Take OTHER side = SELL the top
            if price_change_5m > self.overshoot_pct:
                entry = current_price
                tp = entry * (1 - self.tp_pct)
                sl = entry * (1 + self.sl_pct)
                return 'SHORT', entry, tp, sl
        
        return None

def backtest_take_other_side(df_price, df_liquidations, fee_pct=0.001):
    """
    Backtest Take Other Side strategy
    
    Args:
        df_price: Price data (5min candles)
        df_liquidations: Liquidation events
        fee_pct: Trading fee (0.1% round-trip)
    """
    print("🎯 BACKTESTING: Take the Other Side Strategy")
    print("="*70)
    
    strategy = TakeOtherSideStrategy(spike_threshold_btc=10, overshoot_pct=0.02)
    
    trades = []
    active_trade = None
    
    for i in range(len(df_price)):
        row = df_price.iloc[i]
        current_time = row['timestamp']
        current_price = row['close']
        
        # Check for active trade exit
        if active_trade:
            if active_trade['direction'] == 'LONG':
                if row['high'] >= active_trade['tp']:
                    # TP hit
                    pnl_pct = strategy.tp_pct - fee_pct
                    trades.append({
                        'entry_time': active_trade['entry_time'],
                        'exit_time': current_time,
                        'direction': 'LONG',
                        'entry': active_trade['entry'],
                        'exit': active_trade['tp'],
                        'outcome': 'WIN',
                        'pnl_pct': pnl_pct
                    })
                    active_trade = None
                    continue
                elif row['low'] <= active_trade['sl']:
                    # SL hit
                    pnl_pct = -strategy.sl_pct - fee_pct
                    trades.append({
                        'entry_time': active_trade['entry_time'],
                        'exit_time': current_time,
                        'direction': 'LONG',
                        'entry': active_trade['entry'],
                        'exit': active_trade['sl'],
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
                        'entry': active_trade['entry'],
                        'exit': active_trade['tp'],
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
                        'entry': active_trade['entry'],
                        'exit': active_trade['sl'],
                        'outcome': 'LOSS',
                        'pnl_pct': pnl_pct
                    })
                    active_trade = None
                    continue
        
        # Check for new signal
        if active_trade is None:
            # Detect liquidation spike
            spike, direction, volume = strategy.detect_liquidation_spike(
                df_liquidations, current_time, window_minutes=5
            )
            
            if spike:
                # Calculate price change
                if i >= 1:
                    prev_price = df_price.iloc[i-1]['close']
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
    print("Strategy 1: Take the Other Side")
    print("Waiting for liquidation data to backtest...")
