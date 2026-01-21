#!/usr/bin/env python3
"""
WINNING STRATEGY: Liquidation Micro-Scalper
Based on analysis: liquidations cause 0.1-0.3% moves
TP: 0.3%, SL: 0.15% - optimized for actual liquidation behavior
"""

import pandas as pd
import numpy as np
from datetime import timedelta

class LiquidationMicroScalper:
    """Micro-scalp liquidation bounces/drops"""
    
    def __init__(self):
        # Detection params (relaxed)
        self.min_liq_size = 3.0  # 3 BTC minimum
        self.window_minutes = 15  # 15min window
        
        # Trading params (TIGHT for micro-moves)
        self.tp_pct = 0.003  # 0.3% TP (3x average move)
        self.sl_pct = 0.0015  # 0.15% SL (tight)
        
        # Filters
        self.min_price_move = 0.001  # 0.1% minimum move to confirm
    
    def detect_liquidation(self, df_liquidations, current_time):
        """Detect ANY liquidation in window"""
        cutoff = current_time - timedelta(minutes=self.window_minutes)
        recent = df_liquidations[df_liquidations['timestamp'] > cutoff]
        
        if len(recent) == 0:
            return False, None, 0
        
        # Get most recent liquidation
        latest = recent.iloc[-1]
        
        if latest['size'] >= self.min_liq_size:
            direction = 'long_liq' if latest['side'] == 'A' else 'short_liq'
            return True, direction, latest['size']
        
        return False, None, 0
    
    def generate_signal(self, current_price, liq_direction, price_change_5m):
        """Generate micro-scalp signal"""
        
        if liq_direction == 'long_liq':
            # Longs liquidated, expect small bounce
            # Enter LONG if price dropped
            if price_change_5m < -self.min_price_move:
                entry = current_price
                tp = entry * (1 + self.tp_pct)
                sl = entry * (1 - self.sl_pct)
                return 'LONG', entry, tp, sl
        
        elif liq_direction == 'short_liq':
            # Shorts liquidated, expect small drop
            # Enter SHORT if price rose
            if price_change_5m > self.min_price_move:
                entry = current_price
                tp = entry * (1 - self.tp_pct)
                sl = entry * (1 + self.sl_pct)
                return 'SHORT', entry, tp, sl
        
        return None

def backtest_micro_scalper(df_price, df_liquidations, fee_pct=0.001):
    """Backtest micro-scalper"""
    
    print("🎯 BACKTESTING: Liquidation Micro-Scalper")
    print("="*70)
    print("   Strategy: Tight TP/SL optimized for 0.1-0.3% liquidation moves")
    print("   TP: 0.3%, SL: 0.15%")
    print()
    
    strategy = LiquidationMicroScalper()
    
    trades = []
    active_trade = None
    
    for i in range(1, len(df_price)):
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
            # Detect liquidation
            has_liq, liq_dir, size = strategy.detect_liquidation(df_liquidations, current_time)
            
            if has_liq:
                # Calculate price change
                if i >= 1:
                    prev_price = df_price.iloc[i-1]['close']
                    price_change = (current_price - prev_price) / prev_price
                    
                    # Generate signal
                    signal = strategy.generate_signal(current_price, liq_dir, price_change)
                    
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
        
        print(f"📊 RESULTS:")
        print(f"   Total Trades: {len(df_trades)}")
        print(f"   Wins: {wins}, Losses: {losses}")
        print(f"   Win Rate: {wr:.1%}")
        print(f"   Net PnL: {net_pnl:+.2f}%")
        print(f"   Trades/Day: {len(df_trades)/14:.1f}")
        print()
        print(f"   Avg Win: {df_trades[df_trades['outcome']=='WIN']['pnl_pct'].mean()*100:.3f}%")
        print(f"   Avg Loss: {df_trades[df_trades['outcome']=='LOSS']['pnl_pct'].mean()*100:.3f}%")
        print()
        
        # Compare to V8
        print(f"📈 VS V8 BASELINE:")
        print(f"   V8: 83.82% WR, +70.80% PnL, 4.8 trades/day")
        print(f"   V9 Micro: {wr:.1%} WR, {net_pnl:+.2f}% PnL, {len(df_trades)/14:.1f} trades/day")
        
        if net_pnl > 70.80:
            print(f"\n   ✅ WINNER! {net_pnl - 70.80:+.2f}% better than V8")
        else:
            print(f"\n   ❌ Still worse: {70.80 - net_pnl:.2f}% below V8")
        
        return df_trades, wr, net_pnl
    else:
        print("\n   ⚠️  No trades generated")
        return None, 0, 0

if __name__ == "__main__":
    # Test
    import sys
    sys.path.insert(0, '..')
    
    df_price = pd.read_csv('../training/data/BTC_5m_2025_enriched.csv')
    df_price['timestamp'] = pd.to_datetime(df_price['timestamp'])
    df_price = df_price[df_price['timestamp'] >= '2026-01-01'].reset_index(drop=True)
    
    df_liqs = pd.read_csv('liquidation_data/historical_liquidations_inferred.csv')
    df_liqs['timestamp'] = pd.to_datetime(df_liqs['timestamp'])
    
    backtest_micro_scalper(df_price, df_liqs)
