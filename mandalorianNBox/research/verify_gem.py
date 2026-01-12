
import sys
import os
import backtrader as bt
import pandas as pd

# Path setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard.strategies_complete import AIGemV1

def verify_gem():
    print("💎 Verifying AI GEM V1...")
    
    cerebro = bt.Cerebro()
    
    # Load Data
    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'BTC_1h.csv')
    df = pd.read_csv(data_path, parse_dates=True, index_col='timestamp')
    if 'datetime' in df.columns: df.drop(columns=['datetime'], inplace=True)
    
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    
    # Add Gem
    cerebro.addstrategy(AIGemV1)
    
    print("\n🚀 Running AI GEM Backtest...")
    cerebro.run()
    
    print("\n✅ Verification Complete (Look for '💎 GEM ... Conf')")

if __name__ == '__main__':
    verify_gem()
