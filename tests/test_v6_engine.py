
import pandas as pd
import sys
import os
from datetime import datetime

# Add root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from model_engines.v6_grid.engine import V6GridEngine

def run_integration_test():
    print("🚀 Running V6 Grid Engine Integration Test...")
    
    # 1. Initialize Engine
    try:
        engine = V6GridEngine()
        engine.initialize()
    except Exception as e:
        print(f"❌ Failed to initialize engine: {e}")
        return

    # 2. Load Data
    data_path = 'training/data/BTC_5m_2025_enriched.csv'
    if not os.path.exists(data_path):
        print("❌ Data not found")
        return
        
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Filter for Jan 1-14 2026 (Test Set)
    df_test = df[df['timestamp'] >= '2026-01-01'].copy().reset_index(drop=True)
    print(f"   📊 Loaded {len(df_test)} candles for Jan 2026")
    
    # 3. Simulation Loop
    # We will feed the engine growing windows of data to simulate live feed
    # For speed, we will pre-calculate features roughly but let the engine do its internal logic
    
    # Actually, the engine.analyze() expects a DataFrame history.
    # To test properly, we should loop through the last N candles.
    
    trades = 0
    signals = 0
    
    print("   🤖 processing signals...")
    
    # For the sake of the test time, we will just pass the WHOLE dataframe to the engine
    # And check if it can generate a signal for the LAST row.
    
    # But to backtest, we need a loop.
    # Let's run a loop on the first 500 candles of Jan 2026 to verify signal generation works.
    
    start_idx = 1000 # Need largerr warmup for 1h indicators (14 * 60m = 840m minimum)
    n_steps = 500
    
    generated_signals = []
    
    for i in range(start_idx, start_idx + n_steps):
        # Window of history (e.g. last 1000 candles)
        history = df_test.iloc[i-1000:i+1].copy()
        
        signal = engine.analyze(history)
        
        if signal.signal_type == 'GRID':
            print(f"   ✅ GRID SIGNAL @ {history.iloc[-1]['timestamp']}: Conf={signal.confidence:.2f} Buy={signal.grid_buy_level:.2f} Sell={signal.grid_sell_level:.2f}")
            generated_signals.append(signal)
            
    print(f"\n   🏁 Integration Test Complete.")
    print(f"      Signals Generated: {len(generated_signals)} / {n_steps} candles")
    
    if len(generated_signals) > 0:
        print("   ✅ Engine is functioning correctly.")
    else:
        print("   ⚠️ No signals generated. Check logic/thresholds.")

if __name__ == "__main__":
    run_integration_test()
