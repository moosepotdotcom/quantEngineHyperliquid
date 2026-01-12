"""
READY-TO-RUN Backtesting Script
Uses your existing datasets - just run it!
"""

from datetime import datetime 
import backtrader as bt 
import backtrader.analyzers as btanalyzers
import os

# Get the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(current_dir, 'datasets', 'BTCUSD-1d-1000wks-data.csv')

print(f"📊 Loading data from: {data_path}")

# Strategy: SMA Crossover
class SmaCross(bt.SignalStrategy):
    def __init__(self): 
        # 20-period Simple Moving Average
        sma = bt.ind.SMA(period=20)
        price = self.data
        # Crossover signal: price crosses above SMA = BUY
        crossover = bt.ind.CrossOver(price, sma)
        self.signal_add(bt.SIGNAL_LONG, crossover)

# Initialize backtrader engine
cerebro = bt.Cerebro()

# Add strategy
cerebro.addstrategy(SmaCross)

# Load data from CSV
print("📈 Loading historical data...")
data = bt.feeds.YahooFinanceCSVData(
    dataname=data_path,
    fromdate=datetime(2020, 1, 1),  # Start date
    todate=datetime(2024, 12, 31),   # End date
    reverse=False
)

# Set initial capital
initial_cash = 10000
cerebro.broker.set_cash(initial_cash)
print(f"💰 Starting capital: ${initial_cash:,.2f}")

# Set commission (0.1% = 0.001)
cerebro.broker.setcommission(commission=0.001)

# Add data
cerebro.adddata(data)

# Position sizing: use 95% of available capital per trade
cerebro.addsizer(bt.sizers.AllInSizer, percents=95)

# Add analyzers
cerebro.addanalyzer(btanalyzers.SharpeRatio, _name='sharpe')
cerebro.addanalyzer(btanalyzers.Transactions, _name='tx')
cerebro.addanalyzer(btanalyzers.TradeAnalyzer, _name='trades')
cerebro.addanalyzer(btanalyzers.Returns, _name='returns')
cerebro.addanalyzer(btanalyzers.DrawDown, _name='drawdown')

# Run backtest
print("🚀 Running backtest...")
print("=" * 60)
results = cerebro.run()

# Get results
end_value = cerebro.broker.getvalue()
profit = end_value - initial_cash
profit_pct = (profit / initial_cash) * 100

# Get analyzer results
strategy_result = results[0]
sharpe = strategy_result.analyzers.sharpe.get_analysis()
txs = strategy_result.analyzers.tx.get_analysis()
trades = strategy_result.analyzers.trades.get_analysis()
returns = strategy_result.analyzers.returns.get_analysis()
drawdown = strategy_result.analyzers.drawdown.get_analysis()

# Print results
print("\n" + "=" * 60)
print("📊 BACKTEST RESULTS")
print("=" * 60)
print(f"💰 Starting Capital: ${initial_cash:,.2f}")
print(f"💰 Ending Capital:   ${end_value:,.2f}")
print(f"📈 Total Profit:      ${profit:,.2f}")
print(f"📊 Profit %:          {profit_pct:.2f}%")
print(f"📉 Total Trades:      {len(txs)}")
print(f"📉 Sharpe Ratio:      {sharpe.get('sharperatio', 'N/A')}")
print(f"📉 Max Drawdown:       {drawdown.get('max', {}).get('drawdown', 0):.2f}%")
print("=" * 60)

# Trade statistics
if trades:
    print("\n📈 TRADE STATISTICS:")
    print(f"   Total Trades: {trades.get('total', {}).get('total', 0)}")
    print(f"   Won: {trades.get('won', {}).get('total', 0)}")
    print(f"   Lost: {trades.get('lost', {}).get('total', 0)}")
    if trades.get('won', {}).get('total', 0) > 0:
        win_rate = (trades['won']['total'] / trades['total']['total']) * 100
        print(f"   Win Rate: {win_rate:.2f}%")

print("\n✅ Backtest complete!")
print("💡 Tip: Uncomment cerebro.plot() at the bottom to see charts")

# Uncomment to see the plot
# cerebro.plot(style='candlestick')

