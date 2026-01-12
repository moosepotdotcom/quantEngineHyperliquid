
import backtrader as bt
import pandas as pd
import numpy as np
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.logger import log_to_journal

class LiquidationProxy(bt.Indicator):
    """
    Simulates Liquidation Events based on:
    - High Volume (> 3x Avg)
    - Sharp Price Drop (> 1% in 1 bar)
    - Close near Low (Panic selling)
    """
    lines = ('liq_signal',)
    params = (('vol_mult', 3.0), ('drop_pct', 0.01), ('period', 20),)

    def __init__(self):
        self.vol_ma = bt.indicators.SMA(self.data.volume, period=self.p.period)
        
    def next(self):
        # proxy logic
        vol_spike = self.data.volume[0] > (self.vol_ma[0] * self.p.vol_mult)
        price_drop = (self.data.open[0] - self.data.close[0]) / self.data.open[0] > self.p.drop_pct
        panic_close = (self.data.close[0] - self.data.low[0]) < (self.data.high[0] - self.data.low[0]) * 0.2
        
        if vol_spike and price_drop:
            self.lines.liq_signal[0] = 1.0 # Long Liquidation Detected (Buy Signal for Reversal)
        else:
            self.lines.liq_signal[0] = 0.0

class WhaleProxy(bt.Indicator):
    """
    Simulates Whale Accumulation based on:
    - High Volume (> 3x Avg)
    - Small Price Change (Absorption)
    """
    lines = ('whale_signal',)
    params = (('vol_mult', 3.0), ('range_pct', 0.005), ('period', 20),)

    def __init__(self):
        self.vol_ma = bt.indicators.SMA(self.data.volume, period=self.p.period)
        
    def next(self):
        vol_spike = self.data.volume[0] > (self.vol_ma[0] * self.p.vol_mult)
        small_range = (self.data.high[0] - self.data.low[0]) / self.data.open[0] < self.p.range_pct
        
        if vol_spike and small_range:
            self.lines.whale_signal[0] = 1.0 # Whale Accumulation (Buy Signal)
        else:
            self.lines.whale_signal[0] = 0.0

class EventDrivenStrategy(bt.Strategy):
    params = (
        ('use_liq', True),
        ('use_whale', True),
        ('take_profit', 0.02),
        ('stop_loss', 0.01),
    )

    def __init__(self):
        self.liq_ind = LiquidationProxy(self.data)
        self.whale_ind = WhaleProxy(self.data)
        self.bb = bt.indicators.BollingerBands(self.data.close, period=20, devfactor=2.0)

    def next(self):
        if not self.position:
            # 1. Check Liquidation Reversal (Catch the knife at BB Low)
            if self.p.use_liq and self.liq_ind.liq_signal[0] > 0:
                if self.data.close[0] <= self.bb.lines.bot[0]: # Confluence
                    self.buy()
                    self.entry_price = self.data.close[0]
                    # print(f"🌊 LIQUIDATION PROXY BUY @ {self.data.close[0]}")

            # 2. Check Whale Accumulation (Ride the trend)
            elif self.p.use_whale and self.whale_ind.whale_signal[0] > 0:
                if self.data.close[0] > self.bb.lines.mid[0]: # Above mean
                    self.buy()
                    self.entry_price = self.data.close[0]
                    # print(f"🐋 WHALE PROXY BUY @ {self.data.close[0]}")

        else:
            # Simple Risk Management
            pct_change = (self.data.close[0] - self.entry_price) / self.entry_price
            
            if pct_change >= self.p.take_profit:
                self.sell()
            elif pct_change <= -self.p.stop_loss:
                self.sell()

    def stop(self):
        pnl = self.broker.getvalue() - 100000
        # print(f"Final PnL: ${pnl:.2f}")

def run_event_backtest():
    cerebro = bt.Cerebro()
    
    # Data
    # Use relative path for portability
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(base_dir, "datasets", "BTCUSD-1h-500wks-data.csv")
    if not os.path.exists(data_path):
        print("Data not found!")
        return

    data = bt.feeds.GenericCSVData(
        dataname=data_path,
        dtformat='%Y-%m-%d %H:%M:%S',
        timeframe=bt.TimeFrame.Minutes,
        compression=60,
        openinterest=-1
    )
    cerebro.adddata(data)
    
    # Strategy
    cerebro.addstrategy(EventDrivenStrategy)
    
    # Settings
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)
    
    print("\n⚡ STARTING EVENT-DRIVEN PROXY STARTING...")
    print(f"Initial Portfolio: ${cerebro.broker.getvalue():.2f}")
    
    cerebro.run()
    
    print(f"Final Portfolio:   ${cerebro.broker.getvalue():.2f}")
    pnl = cerebro.broker.getvalue() - 100000.0
    print(f"Net Profit:        ${pnl:.2f}")
    
    log_to_journal("Event Backtest", f"**Result**: ${pnl:.2f}\nProxy logic for Liquidations/Whales tested on historical 1h data.", "⚡")

if __name__ == "__main__":
    run_event_backtest()
