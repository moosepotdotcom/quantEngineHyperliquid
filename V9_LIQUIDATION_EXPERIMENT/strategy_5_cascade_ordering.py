#!/usr/bin/env python3
"""
Strategy 5: Cascade Ordering
Dynamic order placement based on liquidation cascades
12% monthly target
"""

import pandas as pd
import numpy as np
from datetime import timedelta

class CascadeOrderingStrategy:
    """Dynamic cascade-based ordering"""
    
    def __init__(self):
        self.risk_per_trade = 0.01  # 1% risk
        self.base_tp_pct = 0.02
        self.base_sl_pct = 0.01
        self.max_positions = 3
    
    def detect_cascade_strength(self, df_liquidations, current_time):
        """Measure cascade intensity"""
        cutoff = current_time - timedelta(minutes=15)
        recent = df_liquidations[df_liquidations['timestamp'] > cutoff]
        
        if len(recent) < 2:
            return 0, None
        
        total_volume = recent['size'].sum()
        
        # Determine direction
        long_liq = recent[recent['side'] == 'A']['size'].sum()
        short_liq = recent[recent['side'] == 'B']['size'].sum()
        
        if long_liq > short_liq * 1.5:
            direction = 'down'
            strength = long_liq / 10  # Normalize
        elif short_liq > long_liq * 1.5:
            direction = 'up'
            strength = short_liq / 10
        else:
            return 0, None
        
        return min(strength, 3.0), direction  # Cap at 3x
    
    def calculate_dynamic_params(self, cascade_strength):
        """Adjust TP/SL based on cascade strength"""
        # Stronger cascade = wider TP, tighter SL
        tp_multiplier = 1 + (cascade_strength * 0.5)
        sl_multiplier = 1 - (cascade_strength * 0.2)
        
        tp_pct = self.base_tp_pct * tp_multiplier
        sl_pct = self.base_sl_pct * sl_multiplier
        
        return tp_pct, sl_pct
    
    def generate_signal(self, current_price, cascade_strength, cascade_direction):
        """Generate signal with dynamic params"""
        if cascade_strength < 1.0:
            return None  # Not strong enough
        
        tp_pct, sl_pct = self.calculate_dynamic_params(cascade_strength)
        
        if cascade_direction == 'down':
            # Longs cascading, buy the dip
            entry = current_price
            tp = entry * (1 + tp_pct)
            sl = entry * (1 - sl_pct)
            return 'LONG', entry, tp, sl, cascade_strength
        
        elif cascade_direction == 'up':
            # Shorts cascading, sell the top
            entry = current_price
            tp = entry * (1 - tp_pct)
            sl = entry * (1 + sl_pct)
            return 'SHORT', entry, tp, sl, cascade_strength
        
        return None

def backtest_cascade_ordering(df_price, df_liquidations, fee_pct=0.001):
    """Backtest Cascade Ordering strategy"""
    
    print("🎯 BACKTESTING: Cascade Ordering Strategy")
    print("="*70)
    
    strategy = CascadeOrderingStrategy()
    
    trades = []
    active_trades = []
    
    for i in range(len(df_price)):
        row = df_price.iloc[i]
        current_time = row['timestamp']
        current_price = row['close']
        
        # Manage active trades
        for trade in active_trades[:]:
            if trade['direction'] == 'LONG':
                if row['high'] >= trade['tp']:
                    pnl_pct = trade['tp_pct'] - fee_pct
                    trades.append({
                        'entry_time': trade['entry_time'],
                        'exit_time': current_time,
                        'direction': 'LONG',
                        'outcome': 'WIN',
                        'pnl_pct': pnl_pct,
                        'strength': trade['strength']
                    })
                    active_trades.remove(trade)
                elif row['low'] <= trade['sl']:
                    pnl_pct = -trade['sl_pct'] - fee_pct
                    trades.append({
                        'entry_time': trade['entry_time'],
                        'exit_time': current_time,
                        'direction': 'LONG',
                        'outcome': 'LOSS',
                        'pnl_pct': pnl_pct,
                        'strength': trade['strength']
                    })
                    active_trades.remove(trade)
            else:  # SHORT
                if row['low'] <= trade['tp']:
                    pnl_pct = trade['tp_pct'] - fee_pct
                    trades.append({
                        'entry_time': trade['entry_time'],
                        'exit_time': current_time,
                        'direction': 'SHORT',
                        'outcome': 'WIN',
                        'pnl_pct': pnl_pct,
                        'strength': trade['strength']
                    })
                    active_trades.remove(trade)
                elif row['high'] >= trade['sl']:
                    pnl_pct = -trade['sl_pct'] - fee_pct
                    trades.append({
                        'entry_time': trade['entry_time'],
                        'exit_time': current_time,
                        'direction': 'SHORT',
                        'outcome': 'LOSS',
                        'pnl_pct': pnl_pct,
                        'strength': trade['strength']
                    })
                    active_trades.remove(trade)
        
        # Check for new signal
        if len(active_trades) < strategy.max_positions:
            # Detect cascade
            strength, direction = strategy.detect_cascade_strength(df_liquidations, current_time)
            
            if strength > 0:
                # Generate signal
                signal = strategy.generate_signal(current_price, strength, direction)
                
                if signal:
                    dir, entry, tp, sl, str_val = signal
                    tp_pct = abs(tp - entry) / entry
                    sl_pct = abs(sl - entry) / entry
                    
                    active_trades.append({
                        'direction': dir,
                        'entry': entry,
                        'tp': tp,
                        'sl': sl,
                        'tp_pct': tp_pct,
                        'sl_pct': sl_pct,
                        'entry_time': current_time,
                        'strength': str_val
                    })
    
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
        print(f"   Avg Cascade Strength: {df_trades['strength'].mean():.2f}x")
        
        return df_trades, wr, net_pnl
    else:
        print("\n   ⚠️  No trades generated")
        return None, 0, 0

if __name__ == "__main__":
    print("Strategy 5: Cascade Ordering")
