
import sys
import os
import backtrader as bt
import pandas as pd
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class TurtleStrategy(bt.Strategy):
    """Turtle Trading - Optimized Parameters"""
    params = (
        ('lookback', 98),
        ('atr_period', 30),
        ('atr_multiplier', 3.7065),
        ('take_profit_pct', 0.8997),
    )
    
    def __init__(self):
        self.high = bt.ind.Highest(self.data.high, period=self.params.lookback)
        self.low = bt.ind.Lowest(self.data.low, period=self.params.lookback)
        self.atr = bt.ind.ATR(period=self.params.atr_period)
    
    def next(self):
        if not self.position:
            # Entry: Breakout above lookback-bar high
            if self.data.close > self.high[0]:
                self.buy()
            # Entry: Breakdown below lookback-bar low
            elif self.data.close < self.low[0]:
                self.sell()
        else:
            # Exit: Take profit
            if self.position.size > 0:  # Long
                entry = self.position.price
                if self.data.close >= entry * (1 + self.params.take_profit_pct / 100):
                    self.close()
                # Stop loss: atr_multiplier x ATR below entry
                elif self.data.close <= entry - (self.atr[0] * self.params.atr_multiplier):
                    self.close()
            elif self.position.size < 0:  # Short
                entry = self.position.price
                if self.data.close <= entry * (1 - self.params.take_profit_pct / 100):
                    self.close()
                # Stop loss: atr_multiplier x ATR above entry
                elif self.data.close >= entry + (self.atr[0] * self.params.atr_multiplier):
                    self.close()

def run_backtest(data_path, name):
    if not os.path.exists(data_path):
        logger.error(f"File not found: {data_path}")
        return

    logger.info(f"--- Testing on {name} ---")
    
    cerebro = bt.Cerebro()
    cerebro.addstrategy(TurtleStrategy)
    
    # Load Data
    try:
        df = pd.read_csv(data_path)
        time_col = 'timestamp' if 'timestamp' in df.columns else 'time'
        if time_col not in df.columns:
            time_col = df.columns[0]
        df[time_col] = pd.to_datetime(df[time_col])
        df.set_index(time_col, inplace=True)
        df.sort_index(ascending=True, inplace=True)
        
        data = bt.feeds.PandasData(dataname=df)
        cerebro.adddata(data)
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return

    cerebro.broker.setcash(10000)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

    initial_value = cerebro.broker.getvalue()
    logger.info(f"Starting Portfolio Value: {initial_value}")
    
    try:
        results = cerebro.run()
        strat = results[0]
        
        final_value = cerebro.broker.getvalue()
        pnl = final_value - initial_value
        pnl_pct = (pnl / initial_value) * 100
        
        sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0)
        drawdown = strat.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0)
        trades = strat.analyzers.trades.get_analysis()
        total_trades = trades.get('total', {}).get('total', 0)
        
        logger.info(f"Final Portfolio Value: {final_value:.2f}")
        logger.info(f"PnL: ${pnl:.2f} ({pnl_pct:.2f}%)")
        logger.info(f"Sharpe Ratio: {sharpe}")
        logger.info(f"Max Drawdown: {drawdown:.2f}%")
        logger.info(f"Total Trades: {total_trades}")
        
    except Exception as e:
        logger.error(f"Backtest failed: {e}")

if __name__ == "__main__":
    datasets = [
        ("1 Hour", "/Users/alifiyaa/Downloads/ATC Bootcamp Code 2025/datasets/BTCUSD-1h-500wks-data.csv"),
        ("6 Hours", "/Users/alifiyaa/Downloads/ATC Bootcamp Code 2025/datasets/BTCUSD-6h-500wks-data.csv"),
        ("Daily", "/Users/alifiyaa/Downloads/ATC Bootcamp Code 2025/datasets/BTCUSD-1d-1000wks-data.csv")
    ]
    
    for name, path in datasets:
        run_backtest(path, name)
        print("\n")
