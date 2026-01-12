######## BACKTESTING with backtrader 2024 - FIXED VERSION
# Uses your local data files

from datetime import datetime 
import backtrader as bt 
import backtrader.analyzers as btanalyzers
import pandas as pd
import os

# THIS IS WHERE WE DEFINE OUR STRATEGY
class SmaCross(bt.Strategy):
    def __init__(self): 
        # when simple moving average crosses the price, can change the number
        sma = bt.ind.SMA(period=20)
        # this grabs the price data
        price = self.data
        # this defines the cross over.. price and sma
        crossover = bt.ind.CrossOver(price, sma)
        # this tells the code to LONG when it crossover, which is defined above
        self.signal_add(bt.SIGNAL_LONG, crossover)


# this is activating the engine
cerebro = bt.Cerebro()
# this adds the strategy to it
cerebro.addstrategy(SmaCross)

# Find available data file
data_file = None
possible_files = [
    'datasets/BTCUSD-1d-1000wks-data.csv',
    'datasets/BTCUSD-1h-500wks-data.csv',
    'datasets/BTCUSD-6h-500wks-data.csv'
]

for file in possible_files:
    if os.path.exists(file):
        data_file = file
        print(f"📊 Using data file: {file}")
        break

if not data_file:
    print("❌ No data files found in datasets/ folder!")
    print("   Please make sure you have CSV files in the datasets/ directory")
    exit(1)

# Load and prepare data
print(f"📥 Loading data from {data_file}...")
df = pd.read_csv(data_file)

# Check column names and adjust if needed
# Expected columns: timestamp, open, high, low, close, volume
if 'timestamp' not in df.columns:
    # Try to find date/time column
    date_cols = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower()]
    if date_cols:
        df['timestamp'] = pd.to_datetime(df[date_cols[0]])
    else:
        df['timestamp'] = pd.date_range(start='2020-01-01', periods=len(df), freq='1D')

df['timestamp'] = pd.to_datetime(df['timestamp'])
df.set_index('timestamp', inplace=True)

# Ensure we have required columns
required_cols = ['open', 'high', 'low', 'close', 'volume']
for col in required_cols:
    if col not in df.columns:
        print(f"⚠️  Warning: Column '{col}' not found, using close price")
        df[col] = df.get('close', df.iloc[:, 0])  # Use first numeric column or close

# Convert to backtrader format
data = bt.feeds.PandasData(
    dataname=df,
    datetime=None,  # Use index
    open='open',
    high='high',
    low='low',
    close='close',
    volume='volume',
    openinterest=None
)

# this sets the cash amount to the back test
cerebro.broker.set_cash(1000000)

# set the commission 0.1% ... divide by 100 to remove the %
# phemex contract is .00075 taker and -.00025 for maker
# phemex spot is .001 for taker & maker
# ftx is .001 for maker and .004 for taker
cerebro.broker.setcommission(commission=0.001)

# this adds the data to the cerebro engine
cerebro.adddata(data)

# this says go all in, well 95% so we dont miss
cerebro.addsizer(bt.sizers.AllInSizer, percents=95)

# now adding some analyzers...
# this one below is how we get the sharpe analyzer
cerebro.addanalyzer(btanalyzers.SharpeRatio, _name = 'sharpe')
# this is the transactions analyzer
cerebro.addanalyzer(btanalyzers.Transactions, _name = 'tx')
# this is the trade analyzer
cerebro.addanalyzer(btanalyzers.TradeAnalyzer, _name = 'trades')

print("🚀 Running backtest...")
cerebro.run()

# now we run our engine & add it to a variable so we can later check perf
back = cerebro.run() 

# this gets our value back 
endvalue = cerebro.broker.getvalue() 

# below we are looking at our 3 analyzers.. sharpe here
sharpe = back[0].analyzers.sharpe.get_analysis() 

# this is running out transaction analyzer
txs = back[0].analyzers.tx.get_analysis() 

# this is running our trades analyzer
trades = back[0].analyzers.trades.get_analysis() 

txamount = len(txs)

print("\n" + "="*60)
print("📊 BACKTEST RESULTS")
print("="*60)
print(f"Sharpe Ratio: {sharpe}")
print(f"Number of Transactions: {txamount}")
print(f"Final Portfolio Value: ${endvalue:,.2f}")
print(f"Total Return: {((endvalue - 1000000) / 1000000 * 100):.2f}%")
print("="*60)

# Print trade statistics if available
if trades and 'total' in trades:
    print(f"\n📈 Trade Statistics:")
    print(f"   Total Trades: {trades.get('total', {}).get('total', 'N/A')}")
    print(f"   Won: {trades.get('won', {}).get('total', 'N/A')}")
    print(f"   Lost: {trades.get('lost', {}).get('total', 'N/A')}")

print("\n💡 To see the chart, uncomment the line: cerebro.plot()")
print("   (Note: This requires a display/GUI environment)")

# this plots the backtest (uncomment to see chart)
# cerebro.plot()

