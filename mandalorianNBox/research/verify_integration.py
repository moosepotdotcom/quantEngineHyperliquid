
import sys
import os
import backtrader as bt
import pandas as pd

# Path setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard.strategies_complete import TurtleStrategyOptimized

def verify():
    print("🧪 Verifying ML Integration...")
    
    cerebro = bt.Cerebro()
    
    # Load Data
    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'BTC_1h.csv')
    df = pd.read_csv(data_path, parse_dates=True, index_col='timestamp')
    if 'datetime' in df.columns: df.drop(columns=['datetime'], inplace=True)
    
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    
    cerebro.addstrategy(TurtleStrategyOptimized)
    
    print("\n🚀 Running Backtest with ML...")
    cerebro.run()
    
    print("\n✅ Verification Complete (Check logs above for '🤖 AI Loaded' and 'Confidence')")

if __name__ == '__main__':
    verify()
