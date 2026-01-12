
import backtrader as bt
import pandas as pd
import json
import os
import sys

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from research.feature_generator import AdvancedFeatureGenerator
from research.genetic_genome import Genome

class DarwinScalperStrategy(bt.Strategy):
    params = (('genome', None),)
    
    def __init__(self):
        self.genome = self.p.genome
        # We need to pre-calculate the features for the ENTIRE dataset at once for efficiency?
        # Or calculate on fly? Backtrader is bar-by-bar.
        # But our FeatureGenerator is Pandas based.
        # Hybrid approach: We can't easily use the Pandas Generator inside next() without overhead.
        # BUT, since we have the full data CSV, we can pre-calc the signals!
        
        # Actually, let's trust the logic: 
        # We will map the pre-calculated 'signal' column to the strategy lines.
        pass

    def next(self):
        buy_sig = self.data.buy_sig[0]
        sell_sig = self.data.sell_sig[0]
        
        # Debug first 5 bars
        if len(self) < 5:
            print(f"Bar {len(self)} | Buy: {buy_sig} | Sell: {sell_sig} | Pos: {self.position.size}")
            
        if not self.position:
            if buy_sig > 0:
                self.buy()
                self.entry_price = self.data.close[0]
        else:
            # Check SL/TP
            pnl_pct = (self.data.close[0] - self.entry_price) / self.entry_price * 100
            
            if pnl_pct >= self.genome.take_profit_pct:
                self.sell() # TP
            elif pnl_pct <= -self.genome.stop_loss_pct:
                self.sell() # SL
            elif sell_sig > 0:
                self.sell() # Strategy Exit

def run_verification():
    print("📊 STARTING SCALPER VERIFICATION (15m)...")
    
    # 1. Load Data
    data_path = "datasets/BTCUSD-15m-max-data.csv"
    if not os.path.exists(data_path):
        print("Data not found.")
        return
        
    df = pd.read_csv(data_path)
    
    # 2. Load Strategy
    if not os.path.exists('darwin_scalper.json'):
        print("Strategy file darwin_scalper.json not found.")
        return
        
    with open('darwin_scalper.json', 'r') as f:
        dna = json.load(f)
        
    print(f"🧬 Loaded Strategy: {dna['buy_conditions']}")
    
    # 3. Generate Features & Signals (Vectorized)
    gen = AdvancedFeatureGenerator(df)
    df_feat = gen.generate_all()
    
    genome = Genome(list(df_feat.columns))
    genome.buy_conditions = dna['buy_conditions']
    genome.sell_conditions = dna['sell_conditions']
    genome.stop_loss_pct = dna['stop_loss_pct']
    genome.take_profit_pct = dna['take_profit_pct']
    
    print("🚀 Calculating Signals on History...")
    buy_series, sell_series = genome.get_signal_series(df_feat)
    
    
    # Debug
    print(f"DEBUG: Buy Signal Count: {buy_series.sum()}")
    print(f"DEBUG: Sell Signal Count: {sell_series.sum()}")

    # Prepare Data for Backtrader
    # We need separate columns to avoid overwriting
    df_feat['buy_sig'] = buy_series.astype(int)
    df_feat['sell_sig'] = sell_series.astype(int)
    
    if 'datetime' in df_feat.columns:
        df_feat['datetime'] = pd.to_datetime(df_feat['datetime'])
        df_feat.set_index('datetime', inplace=True)
    
    bt_cols = ['open', 'high', 'low', 'close', 'volume', 'buy_sig', 'sell_sig']
    bt_data = df_feat[bt_cols].copy()
    
    # Create Data Feed with 2 custom lines
    class SignalData(bt.feeds.PandasData):
        lines = ('buy_sig', 'sell_sig',)
        params = (
            ('open', 'open'),
            ('high', 'high'),
            ('low', 'low'),
            ('close', 'close'),
            ('volume', 'volume'),
            ('openinterest', None),
            ('buy_sig', 'buy_sig'),
            ('sell_sig', 'sell_sig'),
        )
    
    data = SignalData(dataname=bt_data)
    
    # Run Cerebro
    cerebro = bt.Cerebro()
    cerebro.adddata(data)
    cerebro.addstrategy(DarwinScalperStrategy, genome=genome)
    
    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.0006) 
    
    # Use 50% of cash per trade to allow for margin/slippage safety
    # Or 95% if spot.
    cerebro.addsizer(bt.sizers.PercentSizer, percents=50)

    print(f"💰 Initial Cash: ${cerebro.broker.getvalue():.2f}")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    
    results = cerebro.run()
    strat = results[0]
    
    # Report
    print("\n📝 BACKTEST REPORT (Scalper 15m)")
    print("=" * 40)
    
    final_value = cerebro.broker.getvalue()
    net_profit = final_value - 10000.0
    
    trade_an = strat.analyzers.trades.get_analysis()
    dd_an = strat.analyzers.drawdown.get_analysis()
    sharpe_an = strat.analyzers.sharpe.get_analysis()
    
    total = trade_an.get('total', {}).get('closed', 0)
    won = trade_an.get('won', {}).get('total', 0)
    lost = trade_an.get('lost', {}).get('total', 0)
    win_rate = (won / total * 100) if total > 0 else 0
    
    # Sharpe dict access
    sharpe_val = sharpe_an.get('sharperatio', 0.0)
    if sharpe_val is None: sharpe_val = 0.0
    
    print(f"Final Balance:  ${final_value:,.2f}")
    print(f"Net Profit:     ${net_profit:,.2f} ({net_profit/100:.1f}%)")
    print(f"Total Trades:   {total}")
    print(f"Win Rate:       {win_rate:.1f}%")
    print(f"Drawdown:       {dd_an.max.drawdown:.2f}%")
    print(f"Sharpe Ratio:   {sharpe_val:.2f}")
    print("=" * 40)
    
    # Save chart?
    # cerebro.plot() # Hard in headless

if __name__ == "__main__":
    run_verification()
