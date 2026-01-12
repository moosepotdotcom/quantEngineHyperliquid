import sys
import os
import pandas as pd
import backtrader as bt
import numpy as np

# Add परियोजना root
sys.path.append(os.getcwd())
from dashboard.strategies_complete import STRATEGIES

def test_config(strat_name, params, data_path, sort=False):
    strat_info = STRATEGIES[strat_name]
    strat_class = strat_info['class']
    
    cerebro = bt.Cerebro()
    cerebro.addstrategy(strat_class, **params)
    
    df = pd.read_csv(data_path)
    df.columns = [c.lower() for c in df.columns]
    time_col = 'datetime' if 'datetime' in df.columns else 'time'
    df[time_col] = pd.to_datetime(df[time_col])
    df.set_index(time_col, inplace=True)
    if sort:
        df.sort_index(ascending=True, inplace=True)
    
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    cerebro.broker.setcash(10000)
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    try:
        strat_runs = cerebro.run()
        strat = strat_runs[0]
        trades = strat.analyzers.trades.get_analysis()
        pnl = trades.get('pnl', {}).get('net', {}).get('total', 0)
        profit_pct = (pnl / 10000.0) * 100
        return profit_pct
    except:
        return None

if __name__ == "__main__":
    data_path = "datasets/BTCUSD-1h-500wks-data.csv"
    configs = [
        ('SMA Crossover', {'fast_period': 49, 'slow_period': 34}),
        ('SMA Crossover', {'fast_period': 50, 'slow_period': 32}),
    ]
    
    print("Testing with SORT=FALSE (matches fuzzer bug):")
    for name, params in configs:
        profit = test_config(name, params, data_path, sort=False)
        print(f"{name} {params} -> {profit}%")

    print("\nTesting with SORT=TRUE (corrected):")
    for name, params in configs:
        profit = test_config(name, params, data_path, sort=True)
        print(f"{name} {params} -> {profit}%")
