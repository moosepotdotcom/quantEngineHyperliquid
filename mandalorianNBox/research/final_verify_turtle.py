
import backtrader as bt
import pandas as pd
import datetime
import os
import sys

# Add dashboard path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'dashboard')))
from strategies_complete import STRATEGIES

def run_compare():
    strategies_to_test = ['Turtle Trading (Optimized)', 'SMA Crossover']
    
    # Load Data
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(curr_dir, '..', 'datasets', 'BTCUSD-1h-500wks-data.csv')
    
    df = pd.read_csv(data_path)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime', ascending=True)
    df.set_index('datetime', inplace=True)
    
    # Filter 2023+
    df = df[df.index >= '2023-01-01']

    print(f"Comparing Strategies on clean data (Rows: {len(df)})...")
    print("-" * 60)
    print(f"{'Strategy':<30} | {'Return':<10} | {'Trades':<8} | {'WinRate':<8}")
    print("-" * 60)

    for name in strategies_to_test:
        strat_info = STRATEGIES[name]
        cerebro = bt.Cerebro()
        
        data = bt.feeds.PandasData(dataname=df, timeframe=bt.TimeFrame.Minutes, compression=60)
        cerebro.adddata(data)
        
        cerebro.addstrategy(strat_info['class']) # Use defaults
        
        # Safe Sizing: 10% of equity to avoid blowups
        cerebro.addsizer(bt.sizers.PercentSizer, percents=10)
        cerebro.broker.setcash(100000.0)
        cerebro.broker.setcommission(commission=0.001)
        
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

        try:
            runs = cerebro.run()
            strat = runs[0]
            val = cerebro.broker.getvalue()
            pnl = ((val - 100000)/100000) * 100
            
            t_an = strat.analyzers.trades.get_analysis()
            total = t_an.get('total', {}).get('total', 0)
            won = t_an.get('won', {}).get('total', 0)
            wr = (won/total*100) if total else 0
            
            print(f"{name:<30} | {pnl:>9.2f}% | {total:>8} | {wr:>7.1f}%")
        except Exception as e:
            print(f"{name}: Error {e}")

if __name__ == "__main__":
    run_compare()
