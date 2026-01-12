
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
    
    # Use V2 Strategy
    cerebro.addstrategy(MTFScalperStrategy)
    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.0006)
    
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
    
    print("\n🚀 Running MTF Scalper Backtest...")
    results = cerebro.run()
    strat = results[0]
    
    # Calculate Metrics
    analysis = strat.analyzers.trades.get_analysis()
    total_trades = analysis.get('total', {}).get('total', 0)
    won = analysis.get('won', {}).get('total', 0)
    lost = analysis.get('lost', {}).get('total', 0)
    
    # Calculate Days
    if len(strat.data) > 0:
        start = bt.num2date(strat.data.datetime[0])
        end = bt.num2date(strat.data.datetime[-1])
        days = (end - start).days
        if days == 0: days = 1
    else:
        days = 1
        
    trades_per_day = total_trades / days
    
    # Calculate Points (Approximate from PnL or Price Diff)
    # We need to access the trade history from the strategy if possible, 
    # or just assume from PnL if 1pt = $1 (depends on size). 
    # Let's iterate through completed trades if we can, but analyzer summary is easier.
    # Analyzer gives PnL. PnL / Size = Points (roughly). 
    # Default size is 1? verification script didn't set sizer.
    # Default is usually 1 unit if not set? No, cerebro default is often 1.
    # Let's assume PnL Net Total.
    
    pnl_net = analysis.get('pnl', {}).get('net', {}).get('total', 0.0)
    avg_pnl = pnl_net / total_trades if total_trades > 0 else 0
    
    print(f"\n📊 V2 Performance Report:")
    print(f"   • Total Trades: {total_trades}")
    print(f"   • Days Scanned: {days}")
    print(f"   • Trades/Day:   {trades_per_day:.2f}")
    print(f"   • Win Rate:     {won/total_trades:.2%}" if total_trades > 0 else "   • Win Rate: N/A")
    print(f"   • Avg PnL:      ${avg_pnl:.2f} (Per Trade)")
    
    print("\n✅ Verification Complete")

if __name__ == '__main__':
    verify_mtf()
