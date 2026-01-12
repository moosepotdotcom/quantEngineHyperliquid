import sys
import os
import pandas as pd
import backtrader as bt
import logging
from datetime import datetime

# Add root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dashboard.strategies_complete import SMAStrategy, RSIStrategy
from strategies.ml_quantum_strategy import MLQuantumStrategy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_benchmark(data_path):
    print("\n🏁 STARTING GOD MODE BENCHMARK 🏁")
    print("-" * 40)
    
    results = {}
    
    # Define benchmark runs
    benchmarks = [
        ("SMA (Fuzzed)", SMAStrategy, {'fast_period': 12, 'slow_period': 26}), # Example of "fuzzed" params
        ("RSI (Mean Rev)", RSIStrategy, {'rsi_period': 14, 'rsi_oversold': 30, 'rsi_overbought': 70}),
        ("QUANTUM AI", MLQuantumStrategy, {'confidence_threshold': 0.60})
    ]
    
    for name, strat_class, params in benchmarks:
        print(f"🚀 Running: {name}...")
        cerebro = bt.Cerebro()
        cerebro.addstrategy(strat_class, **params)
        
        df = pd.read_csv(data_path)
        # Handle Column Names
        df.columns = [c.lower() for c in df.columns]
        
        # Ensure 'time' or 'timestamp' or 'datetime' is datetime
        time_col = 'time' if 'time' in df.columns else 'timestamp' if 'timestamp' in df.columns else 'datetime' if 'datetime' in df.columns else None
        if time_col:
            df[time_col] = pd.to_datetime(df[time_col])
            df.set_index(time_col, inplace=True)
            df.sort_index(ascending=True, inplace=True)
        
        # Use only last 20% of data for benchmark (Out-of-sample)
        split_idx = int(len(df) * 0.8)
        df_oos = df.iloc[split_idx:]
        
        data = bt.feeds.PandasData(dataname=df_oos)
        cerebro.adddata(data)
        cerebro.broker.setcash(10000)
        
        cerebro.run()
        final_value = cerebro.broker.getvalue()
        profit = final_value - 10000
        results[name] = profit
        print(f"✅ {name} Result: ${profit:.2f}\n")

    print("\n📊 FINAL BENCHMARK SUMMARY 📊")
    for name, pnl in results.items():
        print(f"{name:<20}: ${pnl:>10.2f}")

if __name__ == "__main__":
    # Use relative path for portability
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_file = os.path.join(base_dir, "datasets", "BTCUSD-1h-500wks-data.csv")
    if os.path.exists(data_file):
        run_benchmark(data_file)
