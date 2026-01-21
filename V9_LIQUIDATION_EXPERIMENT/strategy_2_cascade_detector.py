#!/usr/bin/env python3
"""
Strategy 2: Cascade Detector
Detect price overshoots during liquidation cascades
Mean reversion play - Expected WR: 80-85%
"""

import pandas as pd
import numpy as np
from datetime import timedelta

class CascadeDetectorStrategy:
    """Detect and fade liquidation cascades"""
    
    def __init__(self):
        # Cascade detection params
        self.cascade_volume_threshold = 20  # BTC
        self.cascade_time_window = 10  # minutes
        self.overshoot_threshold = 0.03  # 3% overshoot
        
        # Trading params
        self.tp_pct = 0.025  # 2.5% TP (larger for mean reversion)
        self.sl_pct = 0.005  # 0.5% SL (tight)
    
    def detect_cascade(self, df_liquidations, current_time):
        """
        Detect if liquidation cascade is occurring
        
        Returns:
            (cascade_active, direction, intensity)
        """
        cutoff = current_time - timedelta(minutes=self.cascade_time_window)
        recent = df_liquidations[df_liquidations['timestamp'] > cutoff]
        
        if len(recent) < 3:  # Need multiple liquidations
            return False, None, 0
        
        total_volume = recent['size'].sum()
        
        if total_volume >= self.cascade_volume_threshold:
            # Determine cascade direction
            long_liq = recent[recent['side'] == 'A']['size'].sum()
            short_liq = recent[recent['side'] == 'B']['size'].sum()
            
            if long_liq > short_liq * 2:  # 2:1 ratio
                direction = 'down_cascade'  # Longs getting rekt
                intensity = long_liq / self.cascade_volume_threshold
            elif short_liq > long_liq * 2:
                direction = 'up_cascade'  # Shorts getting rekt
                intensity = short_liq / self.cascade_volume_threshold
            else:
                return False, None, 0  # Mixed, not clear cascade
            
            return True, direction, intensity
        
        return False, None, 0
    
    def detect_overshoot(self, df_price, current_idx, lookback=12):
        """
        Detect if price has overshot (moved too far too fast)
        
        Returns:
            (overshooted, direction, magnitude)
        """
        if current_idx < lookback:
            return False, None, 0
        
        current_price = df_price.iloc[current_idx]['close']
        lookback_price = df_price.iloc[current_idx - lookback]['close']
        
        price_change = (current_price - lookback_price) / lookback_price
        
        if price_change < -self.overshoot_threshold:
            # Oversold
            return True, 'oversold', abs(price_change)
        elif price_change > self.overshoot_threshold:
            # Overbought
            return True, 'overbought', price_change
        
        return False, None, 0
    
    def generate_signal(self, cascade_direction, overshoot_direction, current_price):
        """
        Generate mean reversion signal
        
        Logic:
        - Down cascade + oversold = BUY (mean reversion)
        - Up cascade + overbought = SELL (mean reversion)
        """
        if cascade_direction == 'down_cascade' and overshoot_direction == 'oversold':
            # Price crashed due to cascade, buy the dip
            entry = current_price
            tp = entry * (1 + self.tp_pct)
            sl = entry * (1 - self.sl_pct)
            return 'LONG', entry, tp, sl
        
        elif cascade_direction == 'up_cascade' and overshoot_direction == 'overbought':
            # Price spiked due to cascade, sell the top
            entry = current_price
            tp = entry * (1 - self.tp_pct)
            sl = entry * (1 + self.sl_pct)
            return 'SHORT', entry, tp, sl
        
        return None

def backtest_cascade_detector(df_price, df_liquidations, fee_pct=0.001):
    """Backtest Cascade Detector strategy"""
    
    print("🎯 BACKTESTING: Cascade Detector Strategy")
    print("="*70)
    
    strategy = CascadeDetectorStrategy()
    
    trades = []
    active_trade = None
    
    for i in range(12, len(df_price)):  # Start after lookback
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
            # Detect cascade
            cascade, cascade_dir, intensity = strategy.detect_cascade(df_liquidations, current_time)
            
            if cascade:
                # Detect overshoot
                overshoot, overshoot_dir, magnitude = strategy.detect_overshoot(df_price, i)
                
                if overshoot:
                    # Generate signal
                    signal = strategy.generate_signal(cascade_dir, overshoot_dir, current_price)
                    
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
        
        return df_trades, wr, net_pnl
    else:
        print("\n   ⚠️  No trades generated")
        return None, 0, 0

if __name__ == "__main__":
    print("Strategy 2: Cascade Detector")
    print("Waiting for liquidation data to backtest...")
