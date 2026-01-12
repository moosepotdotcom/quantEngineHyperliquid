#!/usr/bin/env python3
"""
Global Strategy Optimizer
Runs all strategies against all datasets to find the best performing combination.
"""

import sys
import os
import json
import pandas as pd
from datetime import datetime
import time

# Add dashboard to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'dashboard'))

try:
    from strategies_complete import STRATEGIES
    from backtest_engine import run_backtest
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

# Map of friendly names to data files
DATA_FILES = {
    'BTC Daily': 'datasets/BTCUSD-1d-1000wks-data.csv',
    # 'BTC Hourly': 'datasets/BTCUSD-1h-500wks-data.csv',
    # 'BTC 6-Hour': 'datasets/BTCUSD-6h-500wks-data.csv',
    # 'BTC 15m (2022)': 'Open-AI-Assistants for Bootcamp Members Only/BTC-USD-15m-2022-1-01.csv',
    # 'BTC 15m (2023)': 'Open-AI-Assistants for Bootcamp Members Only/BTC-USD-15m-2023-1-01T00_00 (1).csv',
    # 'ETH 15m (2021)': 'Open-AI-Assistants for Bootcamp Members Only/ETH-USD-15m-2021-1-01T00_00.csv',
}

def main():
    print("\n=================================================")
    print("   🚀 MANDALORIANN GLOBAL OPTIMIZER 🚀")
    print("=================================================\n")
    
    results = []
    total_combinations = len(STRATEGIES) * len(DATA_FILES)
    current = 0
    
    start_optim_time = datetime.now()
    
    for strategy_name in STRATEGIES.keys():
        for data_label, data_path in DATA_FILES.items():
            current += 1
            print(f"[{current}/{total_combinations}] Testing {strategy_name} on {data_label}...", end="", flush=True)
            
            # Use default params for now
            params = {k: v['default'] for k, v in STRATEGIES[strategy_name]['params'].items()}
            filename = os.path.basename(data_path)
            
            try:
                # Capture print output to avoid clutter
                # sys.stdout = open(os.devnull, 'w')
                
                result = run_backtest(
                    strategy_name, 
                    params, 
                    filename, 
                    start_date='2020-01-01', 
                    end_date='2024-12-31',
                    initial_cash=10000
                )
                
                # Restore stdout
                # sys.stdout = sys.__stdout__
                
                if 'error' in result:
                    print(f" ❌ Error: {result['error']}")
                else:
                    # Sanity check for unrealistic profits (e.g. > 1 trillion %)
                    # These likely indicate data errors or overly aggressive compounding
                    is_unrealistic = result['profit_pct'] > 1_000_000
                    
                    if is_unrealistic:
                         print(f" ⚠️  Unrealistic Return ({result['profit_pct']:.0f}%) - Discarding")
                    else:
                        sharpe = result.get('sharpe_ratio')
                        print(f" ✅ Profit: {result['profit_pct']:.2f}% | Sharpe: {sharpe if sharpe is not None else 0.0:.2f}")
                        
                        results.append({
                            'strategy': strategy_name,
                            'data': data_label,
                            'profit_pct': result['profit_pct'],
                            'sharpe': sharpe if sharpe is not None else 0,
                            'trades': result['total_trades'],
                            'win_rate': result['win_rate'],
                            'max_drawdown': result['max_drawdown']
                        })
            except Exception as e:
                # sys.stdout = sys.__stdout__
                print(f" 💥 Critical Fail: {e}")

    # Sort results
    print("\n\n=================================================")
    print("   🏆 OPTIMIZATION RESULTS (Top 10) 🏆")
    print("=================================================")
    
    # Sort by Sharpe Ratio first (risk-adjusted return) then Profit
    # Filtering out zero trades
    valid_results = [r for r in results if r['trades'] > 0]
    
    # Sort by Profit (users usually care about this most, even if risky)
    sorted_results = sorted(valid_results, key=lambda x: x['profit_pct'], reverse=True)
    
    df = pd.DataFrame(sorted_results)
    if not df.empty:
        print(df.head(15).to_string(index=False, columns=['strategy', 'data', 'profit_pct', 'sharpe', 'trades', 'win_rate']))
        
        # Save to file
        csv_path = "optimization_results.csv"
        df.to_csv(csv_path, index=False)
        print(f"\nFull results saved to {csv_path}")
    else:
        print("No valid results found.")
        
    print(f"\nTotal Time: {datetime.now() - start_optim_time}")

if __name__ == "__main__":
    main()
