import sys
import os
import pandas as pd
import backtrader as bt
import logging

# Add project root to path
sys.path.append(os.getcwd())
from dashboard.strategies_complete import SMAStrategy

def run_backtest(data_path, fast, slow):
    print(f"\n📊 RUNNING BACKTEST: SMA ({fast}, {slow})")
    print("-" * 40)
    
    cerebro = bt.Cerebro()
    cerebro.addstrategy(SMAStrategy, fast_period=fast, slow_period=slow)
    
    # Load Data
    df = pd.read_csv(data_path)
    df.columns = [c.lower() for c in df.columns]
    time_col = 'datetime' if 'datetime' in df.columns else 'time'
    df[time_col] = pd.to_datetime(df[time_col])
    df.set_index(time_col, inplace=True)
    df.sort_index(ascending=True, inplace=True)
    
    print(f"Dataset: {os.path.basename(data_path)}")
    print(f"Timeframe: {df.index.min()} to {df.index.max()}")
    
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    
    # Initial Cash
    initial_cash = 10000
    cerebro.broker.setcash(initial_cash)
    
    # Analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    # Run
    results = cerebro.run()
    strat = results[0]
    
    final_value = cerebro.broker.getvalue()
    pnl = final_value - initial_cash
    pnl_pct = (pnl / initial_cash) * 100
    
    sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0)
    max_dd = strat.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0)
    trades = strat.analyzers.trades.get_analysis()
    
    total_trades = trades.get('total', {}).get('total', 0)
    won = trades.get('won', {}).get('total', 0)
    win_rate = (won / total_trades * 100) if total_trades > 0 else 0
    
    print("-" * 40)
    print(f"Final Value: ${final_value:.2f}")
    print(f"Total Profit: ${pnl:.2f} ({pnl_pct:.2f}%)")
    print(f"Sharpe Ratio: {sharpe:.2f}")
    print(f"Max Drawdown: {max_dd:.2f}%")
    print(f"Total Trades: {total_trades}")
    print(f"Win Rate: {win_rate:.2f}%")
    print("-" * 40)

if __name__ == "__main__":
    data_path = "datasets/BTCUSD-1h-500wks-data.csv"
    if os.path.exists(data_path):
        run_backtest(data_path, 45, 50)
    else:
        print("Data file not found.")
