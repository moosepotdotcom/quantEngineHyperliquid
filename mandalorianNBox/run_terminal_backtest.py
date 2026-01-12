#!/usr/bin/env python3
"""
Terminal Backtester for MoonDev Strategies
Run this script to backtest strategies directly in your terminal.
"""

import sys
import os
import json
try:
    import inquirer
except ImportError:
    inquirer = None
from datetime import datetime
import pandas as pd
import backtrader as bt

# Add dashboard to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'dashboard'))

try:
    from strategies_complete import STRATEGIES
    from backtest_engine import run_backtest
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you are running this from the root directory.")
    sys.exit(1)

# Map of friendly names to data files
DATA_FILES = {
    'BTC Daily (Last 1000 weeks)': 'datasets/BTCUSD-1d-1000wks-data.csv',
    'BTC Hourly (Last 500 weeks)': 'datasets/BTCUSD-1h-500wks-data.csv',
    'BTC 6-Hour (Last 500 weeks)': 'datasets/BTCUSD-6h-500wks-data.csv',
    'BTC 15m (2022)': 'Open-AI-Assistants for Bootcamp Members Only/BTC-USD-15m-2022-1-01.csv',
    'BTC 15m (2023)': 'Open-AI-Assistants for Bootcamp Members Only/BTC-USD-15m-2023-1-01T00_00 (1).csv',
    'ETH 15m (2021)': 'Open-AI-Assistants for Bootcamp Members Only/ETH-USD-15m-2021-1-01T00_00.csv',
}

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--strategy', help='Name of strategy to run')
    parser.add_argument('--data', help='Name of data file key')
    args = parser.parse_args()

    print("\n=================================================")
    print("   🌙 MANDALORIANN TERMINAL BACKTESTER 🚀")
    print("=================================================\n")

    # 1. Select Strategy
    strategy_choices = list(STRATEGIES.keys())
    
    if args.strategy and args.data:
        # Non-interactive mode
        if args.strategy not in STRATEGIES:
            print(f"Error: Strategy '{args.strategy}' not found.")
            sys.exit(1)
        if args.data not in DATA_FILES:
            print(f"Error: Data '{args.data}' not found.")
            sys.exit(1)
            
        answers = {'strategy': args.strategy, 'data': args.data}
        print(f"Auto-selecting Strategy: {answers['strategy']}")
        print(f"Auto-selecting Data: {answers['data']}")
    else: 
        # Interactive mode
        if inquirer:
            questions = [
                inquirer.List('strategy',
                              message="Select a Strategy to Backtest",
                              choices=strategy_choices,
                          ),
                inquirer.List('data',
                              message="Select Data File",
                              choices=list(DATA_FILES.keys()),
                          ),
            ]
            answers = inquirer.prompt(questions)
        else:
            answers = None

        if answers is None:
            # Fallback if inquirer is not installed or fails
            print("Creating simple input mode (install 'inquirer' for better UI)...")
            print("Available Strategies:")
            for i, s in enumerate(strategy_choices):
                print(f"{i+1}. {s}")
            try:
                s_idx = int(input("Select Strategy (number): ")) - 1
                strategy_selected = strategy_choices[s_idx]
            except (ValueError, IndexError):
                print("Invalid selection. Exiting.")
                sys.exit(1)
                
            print("\nAvailable Data:")
            data_keys = list(DATA_FILES.keys())
            for i, d in enumerate(data_keys):
                print(f"{i+1}. {d}")
            try:
                d_idx = int(input("Select Data (number): ")) - 1
                data_selected = data_keys[d_idx]
            except (ValueError, IndexError):
                print("Invalid selection. Exiting.")
                sys.exit(1)
                
            answers = {
                'strategy': strategy_selected,
                'data': data_selected
            }

    strategy_name = answers['strategy']
    data_label = answers['data']
    data_file = DATA_FILES[data_label]
    
    # Get Params
    strategy_info = STRATEGIES[strategy_name]
    params = {}
    print(f"\nConfiguration for {strategy_name}:")
    print(f"Description: {strategy_info['description']}")
    
    if args.strategy:
        use_defaults = True
    else:
        use_defaults = input("\nUse default parameters? (Y/n): ").lower() != 'n'
    
    if not use_defaults:
        for p_name, p_info in strategy_info['params'].items():
            default = p_info['default']
            val = input(f"{p_name} (default: {default}): ")
            if val.strip() == "":
                params[p_name] = default
            else:
                if p_info['type'] == 'int':
                    params[p_name] = int(val)
                elif p_info['type'] == 'float':
                    params[p_name] = float(val)
                else:
                    params[p_name] = val
    else:
        for p_name, p_info in strategy_info['params'].items():
            params[p_name] = p_info['default']

    print("\n-------------------------------------------------")
    print(f"RUNNING BACKTEST: {strategy_name}")
    print(f"Data: {data_label}")
    print(f"Params: {params}")
    print("-------------------------------------------------\n")
    
    # Run Backtest
    # We need to extract the filename from the path for backtest_engine compatibility
    # The backtest engine looks in datasets/ or the boolean folder based on filename
    filename = os.path.basename(data_file)
    
    try:
        # Capture start time
        start_time = datetime.now()
        
        result = run_backtest(
            strategy_name, 
            params, 
            filename, 
            start_date='2020-01-01', 
            end_date='2024-12-31',
            initial_cash=10000
        )
        
        duration = datetime.now() - start_time
        
        if 'error' in result:
            print(f"\n❌ ERROR: {result['error']}")
        else:
            print("\n✅ BACKTEST COMPLETE")
            print(f"Time Taken: {duration}")
            print("\n📊 RESULTS:")
            print(f"Initial Cash: ${result['start_cash']:,.2f}")
            print(f"Final Cash:   ${result['end_cash']:,.2f}")
            print(f"Net Profit:   ${result['profit']:,.2f} ({result['profit_pct']:.2f}%)")
            print(f"Total Trades: {result['total_trades']}")
            print(f"Win Rate:     {result['win_rate']:.2f}%")
            print(f"Sharpe Ratio: {result['sharpe_ratio'] if result['sharpe_ratio'] is not None else 0.0:.2f}")
            print(f"Max Drawdown: {result['max_drawdown']:.2f}%")
            
            # Save detailed report
            # timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            # report_file = f"backtest_report_{strategy_name.replace(' ', '_')}_{timestamp}.json"
            # with open(report_file, 'w') as f:
            #     json.dump(result, f, indent=4)
            # print(f"\nDetailed report saved to {report_file}")
            
    except Exception as e:
        print(f"Critical Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
