
import sys
import os
import json
import logging
import pandas as pd
import backtrader as bt
from tabulate import tabulate
import random

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../dashboard'))

from dashboard.strategies_complete import (
    SMAStrategy, RSIStrategy, VWAPStrategy, BollingerBandsStrategy, 
    BollingerBandsTightStrategy, SupplyDemandStrategy, TurtleStrategy, 
    TurtleStrategyOptimized, ConsolidationPopStrategy
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

STRATEGIES_TO_FUZZ = [
    (SMAStrategy, {'fast_period': range(5, 20, 5), 'slow_period': range(20, 60, 10)}),
    (RSIStrategy, {'rsi_period': [10, 14, 21], 'rsi_oversold': [25, 30, 35], 'rsi_overbought': [65, 70, 75]}),
    (BollingerBandsStrategy, {'bb_period': [15, 20, 30], 'bb_dev': [1.8, 2.0, 2.2]}),
    (TurtleStrategyOptimized, {'lookback': range(40, 120, 20), 'atr_period': [14, 30], 'atr_multiplier': [2.0, 3.0, 3.7]}),
    (ConsolidationPopStrategy, {'consolidation_bars': [10, 15, 20], 'consolidation_pct': [0.5, 0.7, 1.0]})
]

def run_optimization():
    print("🚀 Starting Massive AI Strategy Search on BTC 1H...")
    
    # Load Data
    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'BTC_1h.csv')
    if not os.path.exists(data_path):
        print(f"❌ Data file not found: {data_path}")
        return

    df = pd.read_csv(data_path, parse_dates=True, index_col='timestamp')
    if 'datetime' in df.columns: df.drop(columns=['datetime'], inplace=True)
    
    # Results container
    all_results = []
    
    for strategy_class, params in STRATEGIES_TO_FUZZ:
        strat_name = strategy_class.__name__
        print(f"\n🧪 Fuzzing {strat_name}...")
        
        cerebro = bt.Cerebro(optreturn=True)
        cerebro.adddata(bt.feeds.PandasData(dataname=df))
        cerebro.broker.setcash(10000.0)
        cerebro.optstrategy(strategy_class, **params)
        
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        
        try:
            runs = cerebro.run()
            
            for run in runs:
                for strat in run:
                    p = strat.params.__dict__
                    # Filter out internal params that start with _
                    clean_params = {k:v for k,v in p.items() if not k.startswith('_')}
                    
                    # Analyze
                    trades = strat.analyzers.trades.get_analysis()
                    sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0)
                    
                    total_trades = trades.get('total', {}).get('total', 0)
                    pnl = trades.get('pnl', {}).get('net', {}).get('total', 0)
                    
                    if total_trades > 5: # Minimum valid trades
                         all_results.append({
                            'strategy': strat_name,
                            'params': clean_params,
                            'net_profit': pnl,
                            'sharpe': sharpe if sharpe else 0.0,
                            'trades': total_trades
                        })
                        
        except Exception as e:
            print(f"⚠️ Error fuzzing {strat_name}: {e}")

    # Sort & Save
    all_results.sort(key=lambda x: x['sharpe'], reverse=True)
    
    # Display Top 10
    display_data = []
    for r in all_results[:10]:
        display_params = str(r['params'])[:50] + "..."
        display_data.append([r['strategy'], f"${r['net_profit']:.2f}", f"{r['sharpe']:.2f}", r['trades'], display_params])
        
    print("\n🏆 AI GEM CANDIDATES (Top 10 by Sharpe) 🏆")
    print(tabulate(display_data, headers=['Strategy', 'Profit', 'Sharpe', 'Trades', 'Params'], tablefmt='grid'))
    
    # Save best
    with open(os.path.join(os.path.dirname(__file__), 'btc_leaderboard_1h.json'), 'w') as f:
        json.dump(all_results, f, indent=4)
        
    if all_results:
        best = all_results[0]
        print(f"\n💎 THE WINNER: {best['strategy']}")
        print(f"   Profit: ${best['net_profit']:.2f}, Sharpe: {best['sharpe']:.2f}")
        print(f"   Params: {best['params']}")

if __name__ == '__main__':
    run_optimization()
