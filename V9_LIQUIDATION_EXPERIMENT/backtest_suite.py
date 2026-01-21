#!/usr/bin/env python3
"""
COMPREHENSIVE BACKTEST SUITE
Tests all 5 liquidation strategies + V8 baseline
Generates comparison report
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

# Import all strategies
from strategy_1_take_other_side import backtest_take_other_side
from strategy_2_cascade_detector import backtest_cascade_detector
from strategy_3_grid_liquidation import backtest_grid_liquidation
from strategy_4_bb_rsi_liquidation import backtest_bb_rsi_liquidation
from strategy_5_cascade_ordering import backtest_cascade_ordering

class BacktestSuite:
    """Run all strategies and compare results"""
    
    def __init__(self):
        self.results = {}
        self.v8_baseline = {
            'name': 'V8 Baseline (93% WR Model)',
            'trades': 68,
            'win_rate': 0.8382,
            'net_pnl_pct': 70.80,
            'trades_per_day': 4.8
        }
    
    def run_all_strategies(self, df_price, df_liquidations):
        """Run all strategies and collect results"""
        
        print("\n" + "="*70)
        print("🚀 COMPREHENSIVE BACKTEST SUITE")
        print("="*70)
        print(f"   Period: {df_price['timestamp'].min()} to {df_price['timestamp'].max()}")
        print(f"   Price candles: {len(df_price)}")
        print(f"   Liquidations: {len(df_liquidations)}")
        print("="*70)
        
        # Strategy 1: Take Other Side
        print("\n\n")
        df_trades_1, wr_1, pnl_1 = backtest_take_other_side(df_price, df_liquidations)
        if df_trades_1 is not None:
            self.results['Take Other Side'] = {
                'trades': len(df_trades_1),
                'win_rate': wr_1,
                'net_pnl_pct': pnl_1,
                'trades_per_day': len(df_trades_1) / 14
            }
        
        # Strategy 2: Cascade Detector
        print("\n\n")
        df_trades_2, wr_2, pnl_2 = backtest_cascade_detector(df_price, df_liquidations)
        if df_trades_2 is not None:
            self.results['Cascade Detector'] = {
                'trades': len(df_trades_2),
                'win_rate': wr_2,
                'net_pnl_pct': pnl_2,
                'trades_per_day': len(df_trades_2) / 14
            }
        
        # Strategy 3: Grid Around Liquidations
        print("\n\n")
        df_trades_3, wr_3, pnl_3 = backtest_grid_liquidation(df_price)
        if df_trades_3 is not None:
            self.results['Grid Liquidation'] = {
                'trades': len(df_trades_3),
                'win_rate': wr_3,
                'net_pnl_pct': pnl_3,
                'trades_per_day': len(df_trades_3) / 14
            }
        
        # Strategy 4: BB + RSI + Liquidation
        print("\n\n")
        df_trades_4, wr_4, pnl_4 = backtest_bb_rsi_liquidation(df_price, df_liquidations)
        if df_trades_4 is not None:
            self.results['BB+RSI+Liquidation'] = {
                'trades': len(df_trades_4),
                'win_rate': wr_4,
                'net_pnl_pct': pnl_4,
                'trades_per_day': len(df_trades_4) / 14
            }
        
        # Strategy 5: Cascade Ordering
        print("\n\n")
        df_trades_5, wr_5, pnl_5 = backtest_cascade_ordering(df_price, df_liquidations)
        if df_trades_5 is not None:
            self.results['Cascade Ordering'] = {
                'trades': len(df_trades_5),
                'win_rate': wr_5,
                'net_pnl_pct': pnl_5,
                'trades_per_day': len(df_trades_5) / 14
            }
    
    def print_comparison_report(self):
        """Print comprehensive comparison report"""
        
        print("\n\n" + "="*70)
        print("📊 STRATEGY COMPARISON REPORT")
        print("="*70)
        
        # Add V8 baseline to results
        all_results = {'V8 Baseline': self.v8_baseline, **self.results}
        
        # Print table
        print("\n{:<25} | {:>8} | {:>8} | {:>10} | {:>10}".format(
            "Strategy", "Trades", "WR", "Net PnL", "Trades/Day"
        ))
        print("-" * 70)
        
        for name, data in all_results.items():
            print("{:<25} | {:>8} | {:>7.1%} | {:>+9.2f}% | {:>10.1f}".format(
                name,
                data['trades'],
                data['win_rate'],
                data['net_pnl_pct'],
                data['trades_per_day']
            ))
        
        # Find best strategy
        print("\n" + "="*70)
        print("🏆 BEST PERFORMERS:")
        
        # Best win rate
        best_wr = max(all_results.items(), key=lambda x: x[1]['win_rate'])
        print(f"   Highest Win Rate: {best_wr[0]} ({best_wr[1]['win_rate']:.1%})")
        
        # Best PnL
        best_pnl = max(all_results.items(), key=lambda x: x[1]['net_pnl_pct'])
        print(f"   Highest PnL: {best_pnl[0]} ({best_pnl[1]['net_pnl_pct']:+.2f}%)")
        
        # Most trades
        best_freq = max(all_results.items(), key=lambda x: x[1]['trades_per_day'])
        print(f"   Most Active: {best_freq[0]} ({best_freq[1]['trades_per_day']:.1f}/day)")
        
        print("\n" + "="*70)
        print("💡 RECOMMENDATIONS:")
        
        # Compare to V8
        for name, data in self.results.items():
            if data['net_pnl_pct'] > self.v8_baseline['net_pnl_pct']:
                improvement = data['net_pnl_pct'] - self.v8_baseline['net_pnl_pct']
                print(f"   ✅ {name}: {improvement:+.2f}% better than V8")
            else:
                decline = self.v8_baseline['net_pnl_pct'] - data['net_pnl_pct']
                print(f"   ❌ {name}: {decline:.2f}% worse than V8")
        
        print("\n" + "="*70)

def main():
    """Main backtest execution"""
    
    # Load data
    print("📂 Loading data...")
    
    # Price data (Jan 2026)
    df_price = pd.read_csv('../training/data/BTC_5m_2025_enriched.csv')
    df_price['timestamp'] = pd.to_datetime(df_price['timestamp'])
    df_price = df_price[df_price['timestamp'] >= '2026-01-01'].reset_index(drop=True)
    
    # Liquidation data
    try:
        df_liqs = pd.read_csv('liquidation_data/historical_liquidations_inferred.csv')
        df_liqs['timestamp'] = pd.to_datetime(df_liqs['timestamp'])
        print(f"✅ Loaded {len(df_liqs)} liquidations")
    except:
        print("❌ No liquidation data found")
        return
    
    # Run backtest suite
    suite = BacktestSuite()
    suite.run_all_strategies(df_price, df_liqs)
    suite.print_comparison_report()

if __name__ == "__main__":
    main()
