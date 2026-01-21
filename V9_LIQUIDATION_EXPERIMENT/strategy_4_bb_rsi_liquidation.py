#!/usr/bin/env python3
"""
Strategy 4: BB + RSI + Liquidation Combo
Only trade when near liquidation cluster
2x confidence boost
"""

import pandas as pd
import numpy as np

class BBRSILiquidationStrategy:
    """Bollinger Bands + RSI enhanced with liquidation proximity"""
    
    def __init__(self):
        # BB params
        self.bb_period = 20
        self.bb_std = 2
        
        # RSI params
        self.rsi_period = 14
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        
        # Liquidation proximity
        self.liq_proximity_pct = 0.02  # Within 2% of liquidation level
        
        # Trading params
        self.tp_pct = 0.02
        self.sl_pct = 0.008
    
    def calculate_bb(self, df):
        """Calculate Bollinger Bands"""
        df['bb_mid'] = df['close'].rolling(self.bb_period).mean()
        df['bb_std'] = df['close'].rolling(self.bb_period).std()
        df['bb_upper'] = df['bb_mid'] + (self.bb_std * df['bb_std'])
        df['bb_lower'] = df['bb_mid'] - (self.bb_std * df['bb_std'])
        return df
    
    def calculate_rsi(self, df):
        """Calculate RSI"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        return df
    
    def near_liquidation_level(self, current_price, df_liquidations, current_time):
        """Check if price is near a liquidation cluster"""
        from datetime import timedelta
        
        # Get recent liquidations (last hour)
        cutoff = current_time - timedelta(hours=1)
        recent = df_liquidations[df_liquidations['timestamp'] > cutoff]
        
        if len(recent) == 0:
            return False, None
        
        # Check if any liquidation levels are nearby
        for _, liq in recent.iterrows():
            distance_pct = abs(liq['price'] - current_price) / current_price
            
            if distance_pct <= self.liq_proximity_pct:
                # Near liquidation level
                direction = 'long_liq' if liq['side'] == 'A' else 'short_liq'
                return True, direction
        
        return False, None
    
    def generate_signal(self, row, near_liq, liq_direction):
        """Generate signal with liquidation boost"""
        
        # Base BB + RSI signal
        if row['close'] < row['bb_lower'] and row['rsi'] < self.rsi_oversold:
            base_signal = 'LONG'
        elif row['close'] > row['bb_upper'] and row['rsi'] > self.rsi_overbought:
            base_signal = 'SHORT'
        else:
            return None
        
        # Boost if near liquidation
        if near_liq:
            if base_signal == 'LONG' and liq_direction == 'long_liq':
                # Oversold + near long liquidation = strong buy
                return 'LONG', 2.0  # 2x confidence
            elif base_signal == 'SHORT' and liq_direction == 'short_liq':
                # Overbought + near short liquidation = strong sell
                return 'SHORT', 2.0
        
        # Regular signal without boost
        return base_signal, 1.0

def backtest_bb_rsi_liquidation(df_price, df_liquidations, fee_pct=0.001):
    """Backtest BB + RSI + Liquidation strategy"""
    
    print("🎯 BACKTESTING: BB + RSI + Liquidation Combo")
    print("="*70)
    
    strategy = BBRSILiquidationStrategy()
    
    # Calculate indicators
    df = df_price.copy()
    df = strategy.calculate_bb(df)
    df = strategy.calculate_rsi(df)
    
    trades = []
    active_trade = None
    
    for i in range(strategy.bb_period, len(df)):
        row = df.iloc[i]
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
                        'pnl_pct': pnl_pct,
                        'confidence': active_trade['confidence']
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
                        'pnl_pct': pnl_pct,
                        'confidence': active_trade['confidence']
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
                        'pnl_pct': pnl_pct,
                        'confidence': active_trade['confidence']
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
                        'pnl_pct': pnl_pct,
                        'confidence': active_trade['confidence']
                    })
                    active_trade = None
                    continue
        
        # Check for new signal
        if active_trade is None:
            # Check liquidation proximity
            near_liq, liq_dir = strategy.near_liquidation_level(
                current_price, df_liquidations, current_time
            )
            
            # Generate signal
            signal = strategy.generate_signal(row, near_liq, liq_dir)
            
            if signal:
                direction, confidence = signal
                entry = current_price
                tp = entry * (1 + strategy.tp_pct) if direction == 'LONG' else entry * (1 - strategy.tp_pct)
                sl = entry * (1 - strategy.sl_pct) if direction == 'LONG' else entry * (1 + strategy.sl_pct)
                
                active_trade = {
                    'direction': direction,
                    'entry': entry,
                    'tp': tp,
                    'sl': sl,
                    'entry_time': current_time,
                    'confidence': confidence
                }
    
    # Results
    df_trades = pd.DataFrame(trades)
    
    if len(df_trades) > 0:
        wins = len(df_trades[df_trades['outcome'] == 'WIN'])
        losses = len(df_trades[df_trades['outcome'] == 'LOSS'])
        wr = wins / len(df_trades)
        net_pnl = df_trades['pnl_pct'].sum() * 100
        
        # High confidence trades
        high_conf = df_trades[df_trades['confidence'] > 1.5]
        if len(high_conf) > 0:
            high_conf_wr = len(high_conf[high_conf['outcome'] == 'WIN']) / len(high_conf)
            print(f"\n   🎯 High Confidence Trades: {len(high_conf)} ({high_conf_wr:.1%} WR)")
        
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
    print("Strategy 4: BB + RSI + Liquidation Combo")
