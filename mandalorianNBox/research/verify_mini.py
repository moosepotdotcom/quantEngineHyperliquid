
import sys
import os
import backtrader as bt
import pandas as pd

# Path setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard.strategies_complete import MiniScalperStrategy

def verify_mini():
    print("🔥 Verifying Mini AI Scalper V3...")
    
    cerebro = bt.Cerebro()
    
    # Load 15m Data
    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'BTC_15m.csv')
    df = pd.read_csv(data_path, parse_dates=True, index_col='timestamp')
    if 'datetime' in df.columns: df.drop(columns=['datetime'], inplace=True)
    
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    
    cerebro.addstrategy(MiniScalperStrategy)
    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.0006)
    
    print("\n🚀 Running Mini Scalper Backtest...")
    cerebro.run()
    
    print("\n✅ Verification Complete (Look for '🔥 Mini Scalp Signal')")

if __name__ == '__main__':
    verify_mini()
