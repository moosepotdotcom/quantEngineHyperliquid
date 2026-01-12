"""
Strategy Library - Pre-built strategies for testing and backtesting
"""

from datetime import datetime
import backtrader as bt
import pandas as pd

class SMAStrategy(bt.Strategy):
    """Simple Moving Average Crossover"""
    params = (
        ('fast_period', 10),
        ('slow_period', 20),
    )
    
    def __init__(self):
        self.fast_sma = bt.ind.SMA(period=self.params.fast_period)
        self.slow_sma = bt.ind.SMA(period=self.params.slow_period)
        self.crossover = bt.ind.CrossOver(self.fast_sma, self.slow_sma)
    
    def next(self):
        if self.crossover > 0:  # Fast crosses above slow - BUY
            self.buy()
        elif self.crossover < 0:  # Fast crosses below slow - SELL
            self.sell()

class RSIStrategy(bt.Strategy):
    """RSI Mean Reversion Strategy"""
    params = (
        ('rsi_period', 14),
        ('rsi_oversold', 30),
        ('rsi_overbought', 70),
    )
    
    def __init__(self):
        self.rsi = bt.ind.RSI(period=self.params.rsi_period)
    
    def next(self):
        if self.rsi < self.params.rsi_oversold:  # Oversold - BUY
            self.buy()
        elif self.rsi > self.params.rsi_overbought:  # Overbought - SELL
            self.sell()

class BollingerBandsStrategy(bt.Strategy):
    """Bollinger Bands Mean Reversion"""
    params = (
        ('bb_period', 20),
        ('bb_dev', 2),
    )
    
    def __init__(self):
        self.bb = bt.ind.BollingerBands(period=self.params.bb_period, devfactor=self.params.bb_dev)
    
    def next(self):
        if self.data.close < self.bb.lines.bot:  # Price below lower band - BUY
            self.buy()
        elif self.data.close > self.bb.lines.top:  # Price above upper band - SELL
            self.sell()

class MACDStrategy(bt.Strategy):
    """MACD Crossover Strategy"""
    params = (
        ('fast_period', 12),
        ('slow_period', 26),
        ('signal_period', 9),
    )
    
    def __init__(self):
        self.macd = bt.ind.MACD(
            period_me1=self.params.fast_period,
            period_me2=self.params.slow_period,
            period_signal=self.params.signal_period
        )
        self.crossover = bt.ind.CrossOver(self.macd.macd, self.macd.signal)
    
    def next(self):
        if self.crossover > 0:  # MACD crosses above signal - BUY
            self.buy()
        elif self.crossover < 0:  # MACD crosses below signal - SELL
            self.sell()

class VWAPStrategy(bt.Strategy):
    """VWAP Crossover Strategy"""
    params = (
        ('vwap_period', 20),
    )
    
    def __init__(self):
        self.vwap = bt.ind.VWAP(period=self.params.vwap_period)
    
    def next(self):
        if self.data.close > self.vwap:  # Price above VWAP - BUY
            self.buy()
        elif self.data.close < self.vwap:  # Price below VWAP - SELL
            self.sell()

# Strategy registry
STRATEGIES = {
    'SMA Crossover': {
        'class': SMAStrategy,
        'description': 'Buy when fast SMA crosses above slow SMA',
        'params': {
            'fast_period': {'type': 'int', 'default': 10, 'min': 5, 'max': 50},
            'slow_period': {'type': 'int', 'default': 20, 'min': 10, 'max': 100},
        }
    },
    'RSI Mean Reversion': {
        'class': RSIStrategy,
        'description': 'Buy when RSI is oversold, sell when overbought',
        'params': {
            'rsi_period': {'type': 'int', 'default': 14, 'min': 5, 'max': 30},
            'rsi_oversold': {'type': 'int', 'default': 30, 'min': 10, 'max': 40},
            'rsi_overbought': {'type': 'int', 'default': 70, 'min': 60, 'max': 90},
        }
    },
    'Bollinger Bands': {
        'class': BollingerBandsStrategy,
        'description': 'Buy when price touches lower band, sell at upper band',
        'params': {
            'bb_period': {'type': 'int', 'default': 20, 'min': 10, 'max': 50},
            'bb_dev': {'type': 'float', 'default': 2.0, 'min': 1.0, 'max': 3.0},
        }
    },
    'MACD Crossover': {
        'class': MACDStrategy,
        'description': 'Buy when MACD crosses above signal line',
        'params': {
            'fast_period': {'type': 'int', 'default': 12, 'min': 5, 'max': 20},
            'slow_period': {'type': 'int', 'default': 26, 'min': 20, 'max': 50},
            'signal_period': {'type': 'int', 'default': 9, 'min': 5, 'max': 20},
        }
    },
    'VWAP Crossover': {
        'class': VWAPStrategy,
        'description': 'Buy when price is above VWAP, sell when below',
        'params': {
            'vwap_period': {'type': 'int', 'default': 20, 'min': 10, 'max': 50},
        }
    },
}

def get_strategy_info():
    """Get all available strategies"""
    return {name: {
        'description': info['description'],
        'params': info['params']
    } for name, info in STRATEGIES.items()}

