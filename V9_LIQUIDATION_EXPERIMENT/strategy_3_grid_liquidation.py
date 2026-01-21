#!/usr/bin/env python3
"""
Strategy 3: Grid Around Liquidation Levels
Place orders around predicted liquidation prices
Capture volatility when levels are hit
"""

import pandas as pd
import numpy as np

class GridLiquidationStrategy:
    """Grid trading around liquidation levels"""
    
    def __init__(self, grid_spacing=100, grid_levels=3):
        """
        Args:
            grid_spacing: $ spacing between grid levels
            grid_levels: Number of levels above/below
        """
        self.grid_spacing = grid_spacing
        self.grid_levels = grid_levels
        self.tp_pct = 0.015  # 1.5% TP
        self.sl_pct = 0.008  # 0.8% SL
    
    def predict_liquidation_levels(self, current_price):
        """Predict where liquidations will occur"""
        levels = []
        
        # Common leverage levels
        for leverage in [10, 25, 50, 100]:
            liq_pct = 1 / leverage
            
            # Long liquidation (below price)
            long_liq = current_price * (1 - liq_pct)
            levels.append(('long_liq', long_liq, leverage))
            
            # Short liquidation (above price)
            short_liq = current_price * (1 + liq_pct)
            levels.append(('short_liq', short_liq, leverage))
        
        return levels
    
    def place_grid_orders(self, liquidation_levels, current_price):
        """
        Place grid of orders around liquidation levels
        
        Returns:
            List of (direction, price, tp, sl)
        """
        orders = []
        
        for liq_type, liq_price, leverage in liquidation_levels:
            # Only trade nearby levels (within 5%)
            distance_pct = abs(liq_price - current_price) / current_price
            if distance_pct > 0.05:
                continue
            
            if liq_type == 'long_liq':
                # Longs will be liquidated here
                # Place BUY orders below (catch the bounce)
                for i in range(self.grid_levels):
                    price = liq_price - (i * self.grid_spacing)
                    if price < current_price:
                        tp = price * (1 + self.tp_pct)
                        sl = price * (1 - self.sl_pct)
                        orders.append(('LONG', price, tp, sl))
            
            else:  # short_liq
                # Shorts will be liquidated here
                # Place SELL orders above (catch the drop)
                for i in range(self.grid_levels):
                    price = liq_price + (i * self.grid_spacing)
                    if price > current_price:
                        tp = price * (1 - self.tp_pct)
                        sl = price * (1 + self.sl_pct)
                        orders.append(('SHORT', price, tp, sl))
        
        return orders

def backtest_grid_liquidation(df_price, fee_pct=0.001):
    """Backtest Grid Liquidation strategy"""
    
    print("🎯 BACKTESTING: Grid Around Liquidations")
    print("="*70)
    
    strategy = GridLiquidationStrategy(grid_spacing=100, grid_levels=2)
    
    trades = []
    active_orders = []
    
    for i in range(len(df_price)):
        row = df_price.iloc[i]
        current_price = row['close']
        current_time = row['timestamp']
        
        # Check if any orders are filled
        for order in active_orders[:]:
            if order['direction'] == 'LONG':
                if row['low'] <= order['entry']:
                    # Order filled, now manage position
                    if row['high'] >= order['tp']:
                        # TP hit
                        pnl_pct = strategy.tp_pct - fee_pct
                        trades.append({
                            'entry_time': current_time,
                            'exit_time': current_time,
                            'direction': 'LONG',
                            'outcome': 'WIN',
                            'pnl_pct': pnl_pct
                        })
                        active_orders.remove(order)
                    elif row['low'] <= order['sl']:
                        # SL hit
                        pnl_pct = -strategy.sl_pct - fee_pct
                        trades.append({
                            'entry_time': current_time,
                            'exit_time': current_time,
                            'direction': 'LONG',
                            'outcome': 'LOSS',
                            'pnl_pct': pnl_pct
                        })
                        active_orders.remove(order)
            
            else:  # SHORT
                if row['high'] >= order['entry']:
                    if row['low'] <= order['tp']:
                        pnl_pct = strategy.tp_pct - fee_pct
                        trades.append({
                            'entry_time': current_time,
                            'exit_time': current_time,
                            'direction': 'SHORT',
                            'outcome': 'WIN',
                            'pnl_pct': pnl_pct
                        })
                        active_orders.remove(order)
                    elif row['high'] >= order['sl']:
                        pnl_pct = -strategy.sl_pct - fee_pct
                        trades.append({
                            'entry_time': current_time,
                            'exit_time': current_time,
                            'direction': 'SHORT',
                            'outcome': 'LOSS',
                            'pnl_pct': pnl_pct
                        })
                        active_orders.remove(order)
        
        # Place new grid every 4 hours
        if i % 48 == 0:  # Every 48 candles (4h)
            # Clear old orders
            active_orders = []
            
            # Predict liquidation levels
            liq_levels = strategy.predict_liquidation_levels(current_price)
            
            # Place grid
            new_orders = strategy.place_grid_orders(liq_levels, current_price)
            
            for direction, entry, tp, sl in new_orders:
                active_orders.append({
                    'direction': direction,
                    'entry': entry,
                    'tp': tp,
                    'sl': sl
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
        
        return df_trades, wr, net_pnl
    else:
        print("\n   ⚠️  No trades generated")
        return None, 0, 0

if __name__ == "__main__":
    print("Strategy 3: Grid Around Liquidations")
