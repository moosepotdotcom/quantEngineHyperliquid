
import sys
import os
import pandas as pd
import numpy as np
import backtrader as bt
import xgboost as xgb
import pickle
import json
from datetime import datetime

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

# Import Strategies
# We have to handle the relative imports inside strategies_complete by mocking if needed, 
# or just importing carefully.
from dashboard.strategies_complete import (
    TurtleStrategyOptimized, 
    ConsolidationPopStrategy, 
    SMAStrategy
)

# Import Data Logic (Mock or Real)
# Assuming 1H data for Day/Swing and 4H/Daily for Investor?
# For simplicity, we will use the same 5m/1H/4H CSVs we have in data/

DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
MODELS_DIR = os.path.join(PROJECT_ROOT, 'models')
os.makedirs(MODELS_DIR, exist_ok=True)


class DataCollectorMixin:
    """
    Mixin to intercept trades and log features.
    Must be the FIRST parent class to intercept methods.
    """
    
    def __init__(self):
        self.features = []
        self.labels = [] # 1 = Win, 0 = Loss
        self.pending_signal = None # (index, features, type)
        self.direction = 0 # 1 or -1
        self.entry_price = 0.0
        self.sl = 0.0
        self.tp = 0.0
        
        # Ensure parent init is called (The Strategy logic)
        super().__init__()

    def next(self):
        # Run the actual strategy logic (which calls self.buy/sell)
        super().next()
        
        # Check if trade closed (Result determination)
        if self.pending_signal:
            idx, feat, side = self.pending_signal
            outcome = None
            
            low = self.data.low[0]
            high = self.data.high[0]
            
            if self.direction == 1: # Long
                if high >= self.tp:
                    outcome = 1
                elif low <= self.sl:
                    outcome = 0
            else: # Short
                if low <= self.tp:
                    outcome = 1 
                elif high >= self.sl:
                    outcome = 0 
            
            if outcome is not None:
                self.features.append(feat)
                self.labels.append(outcome)
                self.pending_signal = None
                self.direction = 0

    def capture_signal(self, side, price):
        """Called when strategy wants to trade"""
        if self.pending_signal:
            return # Already in a trade
            
        # Extract Features
        try:
            rsi = bt.ind.RSI(self.data.close, period=14)[0]
        except: rsi = 50
        
        try:
            atr = bt.ind.ATR(self.data, period=14)[0]
            atr_pct = (atr / price) * 100
        except: atr_pct = 0.5
        
        try:
            vol_ma = bt.ind.SMA(self.data.volume, period=20)[0]
            vol_ratio = self.data.volume[0] / (vol_ma + 1)
        except: vol_ratio = 1.0
        
        feature_vector = [rsi, atr_pct, vol_ratio, side]
        
        self.entry_price = price
        self.direction = side
        
        # Attempt to get SL/TP from the strategy instance
        # Typically set before buy/sell in our code
        
        if hasattr(self, 'sl_price') and self.sl_price > 0:
            self.sl = self.sl_price
        else:
            self.sl = price * 0.99 if side == 1 else price * 1.01

        if hasattr(self, 'tp_price') and self.tp_price > 0:
            self.tp = self.tp_price
        else:
            self.tp = price * 1.01 if side == 1 else price * 0.99
        
        self.pending_signal = (len(self.data), feature_vector, side)

    # Overwrite Buy/Sell to capture signals
    def buy(self, *args, **kwargs):
        self.capture_signal(1, self.data.close[0])
        return None 
        
    def sell(self, *args, **kwargs):
        self.capture_signal(-1, self.data.close[0])
        return None

def train_model(strategy_class, name, data_path, timeframe_mins=60):
    print(f"\n🧠 Training XGBoost for {name}...")
    
    cerebro = bt.Cerebro()
    
    # Load Data
    if not os.path.exists(data_path):
        print(f"⚠️ Data not found: {data_path}")
        return
        
    df = pd.read_csv(data_path, parse_dates=True, index_col='timestamp')
    if 'datetime' in df.columns:
        df.drop(columns=['datetime'], inplace=True)
        
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    
    # Dynamic Inheritance: Mixin comes FIRST to override methods
    class WrappedStrategy(DataCollectorMixin, strategy_class):
        pass
            
    cerebro.addstrategy(WrappedStrategy)
    cerebro.run()
    
    # Retrieve results
    strat_instance = cerebro.runstrats[0][0]
    X = np.array(strat_instance.features)
    y = np.array(strat_instance.labels)
    
    if len(X) == 0:
        print("⚠️ No trades generated to train on!")
        return
        
    print(f"   Collected {len(X)} samples. Win Rate: {np.mean(y):.2%}")
    
    # Train XGBoost
    model = xgb.XGBClassifier(
        n_estimators=100, 
        max_depth=3, 
        learning_rate=0.1, 
        eval_metric='logloss'
    )
    model.fit(X, y)
    
    # Save
    model_path = os.path.join(MODELS_DIR, f"{name}_xgb.json")
    model.save_model(model_path)
    print(f"✅ Model saved to {model_path}")


def main():
    # 1. Day Trader (Turtle) - 1H Data
    # Assuming we have BTC_1h.csv or similar
    # If not, we might need to fetch it or use existing data.
    # Based on file list, we might only have what's in data/ 
    # Let's search for a CSV first.
    
    csv_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    if not csv_files:
        print("❌ No CSV data found in data/")
        return
        
    # Pick a good file (biggest one?)
    data_file = os.path.join(DATA_DIR, csv_files[0]) # Default to first found
    
    # Try find BTC specific
    for f in csv_files:
        if 'BTC' in f and '1h' in f.lower():
             data_file = os.path.join(DATA_DIR, f)
             break
             
    print(f"📂 Using data: {data_file}")
    
    # Train All
    train_model(TurtleStrategyOptimized, 'day_trader', data_file)
    train_model(ConsolidationPopStrategy, 'swing_trader', data_file) # Should use 4H ideally but we test with this
    train_model(SMAStrategy, 'investor', data_file)

if __name__ == '__main__':
    main()
