
import sys
import os
import backtrader as bt
import pandas as pd

# Path setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard.strategies_complete import MTFScalperStrategy

def verify_mtf():
    print("🦅 Verifying MTF AI Scalper V2...")
    
    cerebro = bt.Cerebro()
    
    # Load 15m Data
    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'BTC_15m.csv')
    df = pd.read_csv(data_path, parse_dates=True, index_col='timestamp')
    if 'datetime' in df.columns: df.drop(columns=['datetime'], inplace=True)
    
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    
    cerebro.addstrategy(MTFScalperStrategy)
    
    print("\n🚀 Running MTF Backtest...")
    cerebro.run()
    
    print("\n✅ Verification Complete (Look for '🦅 MTF Scalper Signal' and 'Conf')")

if __name__ == '__main__':
    verify_mtf()
