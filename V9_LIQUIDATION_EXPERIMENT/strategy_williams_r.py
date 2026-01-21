#!/usr/bin/env python3
"""
Williams %R Strategy Implementation
Based on 100% WR example from research
"""

import pandas as pd
import numpy as np

class WilliamsRStrategy:
    """Williams %R momentum indicator strategy"""
    
    def __init__(self):
        self.period = 14
        self.oversold = -80
        self.overbought = -20
        
        # Trading params
        self.tp_pct = 0.005  # 0.5% TP
        self.sl_pct = 0.003  # 0.3% SL
    
    def calculate_williams_r(self, df):
        """Calculate Williams %R"""
        high_roll = df['high'].rolling(self.period).max()
        low_roll = df['low'].rolling(self.period).min()
        
        df['williams_r'] = -100 * (high_roll - df['close']) / (high_roll - low_roll)
        return df
    
    def generate_signal(self, row):
        """Generate trading signal"""
        if pd.isna(row['williams_r']):
            return None
        
        if row['williams_r'] < self.oversold:
            # Oversold - BUY
            return 'LONG', row['close'], row['close'] * (1 + self.tp_pct), row['close'] * (1 - self.sl_pct)
        elif row['williams_r'] > self.overbought:
            # Overbought - SELL
            return 'SHORT', row['close'], row['close'] * (1 - self.tp_pct), row['close'] * (1 + self.sl_pct)
        
        return None

def backtest_williams_r(df_price, fee_pct=0.001):
    """Backtest Williams %R strategy"""
    
    print("🎯 BACKTESTING: Williams %R Strategy")
    print("="*70)
    
    strategy = WilliamsRStrategy()
    df = df_price.copy()
    df = strategy.calculate_williams_r(df)
    
    trades = []
    active_trade = None
    
    for i in range(strategy.period, len(df)):
        row = df.iloc[i]
        
        # Manage active trade
        if active_trade:
            if active_trade['direction'] == 'LONG':
                if row['high'] >= active_trade['tp']:
                    pnl_pct = strategy.tp_pct - fee_pct
                    trades.append({
                        'entry_time': active_trade['entry_time'],
                        'exit_time': row['timestamp'],
                        'direction': 'LONG',
                        'outcome': 'WIN',
                        'pnl_pct': pnl_pct * 100
                    })
                    active_trade = None
                    continue
                elif row['low'] <= active_trade['sl']:
                    pnl_pct = -strategy.sl_pct - fee_pct
                    trades.append({
                        'entry_time': active_trade['entry_time'],
                        'exit_time': row['timestamp'],
                        'direction': 'LONG',
                        'outcome': 'LOSS',
                        'pnl_pct': pnl_pct * 100
                    })
                    active_trade = None
                    continue
            else:  # SHORT
                if row['low'] <= active_trade['tp']:
                    pnl_pct = strategy.tp_pct - fee_pct
                    trades.append({
                        'entry_time': active_trade['entry_time'],
                        'exit_time': row['timestamp'],
                        'direction': 'SHORT',
                        'outcome': 'WIN',
                        'pnl_pct': pnl_pct * 100
                    })
                    active_trade = None
                    continue
                elif row['high'] >= active_trade['sl']:
                    pnl_pct = -strategy.sl_pct - fee_pct
                    trades.append({
                        'entry_time': active_trade['entry_time'],
                        'exit_time': row['timestamp'],
                        'direction': 'SHORT',
                        'outcome': 'LOSS',
                        'pnl_pct': pnl_pct * 100
                    })
                    active_trade = None
                    continue
        
        # Check for new signal
        if active_trade is None:
            signal = strategy.generate_signal(row)
            if signal:
                direction, entry, tp, sl = signal
                active_trade = {
                    'direction': direction,
                    'entry': entry,
                    'tp': tp,
                    'sl': sl,
                    'entry_time': row['timestamp']
                }
    
    # Results
    df_trades = pd.DataFrame(trades)
    
    if len(df_trades) > 0:
        wins = len(df_trades[df_trades['outcome'] == 'WIN'])
        losses = len(df_trades[df_trades['outcome'] == 'LOSS'])
        wr = wins / len(df_trades)
        net_pnl = df_trades['pnl_pct'].sum()
        
        print(f"\\n📊 RESULTS:")
        print(f"   Total Trades: {len(df_trades)}")
        print(f"   Wins: {wins}, Losses: {losses}")
        print(f"   Win Rate: {wr:.1%}")
        print(f"   Net PnL: {net_pnl:+.2f}%")
        print(f"   Trades/Day: {len(df_trades)/14:.1f}")
        
        # Compare to V8
        print(f"\\n📈 VS V8 BASELINE:")
        print(f"   V8: 83.82% WR, +70.80% PnL")
        print(f"   Williams %R: {wr:.1%} WR, {net_pnl:+.2f}% PnL")
        
        if wr > 0.8382 or net_pnl > 70.80:
            print(f"\\n   ✅ WINNER!")
        
        return df_trades, wr, net_pnl
    else:
        print("\\n   ⚠️  No trades generated")
        return None, 0, 0

if __name__ == "__main__":
    # Test on Jan 2026 data
    df = pd.read_csv('../training/data/BTC_5m_2025_enriched.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df[df['timestamp'] >= '2026-01-01'].reset_index(drop=True)
    
    backtest_williams_r(df)
