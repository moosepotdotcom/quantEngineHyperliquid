
import sys
import os
import pandas as pd
import numpy as np
import warnings
from datetime import datetime, timedelta
warnings.filterwarnings('ignore')

# Force import from local directory (the bundle)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quant_engine import TradingEngine, add_all_indicators

# No mocking needed - we use the real engine to fetch real data
# from the real API, just like the original verification script.

def run_bundled_verification():
    print("📦 VERIFYING BUNDLED ENGINE (Jan 2 - Jan 9 2026)")
    print("   Data Source: Hyperliquid API (Live Fetch)")
    print("="*70)
    
    # 1. Initialize Bundled Engine
    engine = TradingEngine()
    
    # 2. Fetch Data (4000 candles = ~13 days of 5m data)
    print("📥 Fetching Jan 2026 Data...", flush=True)
    df_raw = engine.fetch_data('5m', 4000)
    
    if df_raw is None or len(df_raw) == 0:
        print("❌ API fetch failed.")
        return

    # Add indicators as required by the engine's internal checks?
    # Actually, check_mtf_scalper inside quant_engine CALLS fetch_data itself.
    # It doesn't take a DataFrame as input.
    # This is a problem for backtesting: check_mtf_scalper fetches 'latest' 500 candles ending NOW.
    # It is not designed to backtest on historical data provided by argument.
    
    # To backtest historical data using the bundled code, we MUST override fetch_data.
    # The Mock approach was correct, I just lacked the data.
    # So I will re-implement the Mock, but this time populate it with FRESHLY FETCHED data.
    
    print(f"   Fetched {len(df_raw)} raw candles.")
    df_5m = add_all_indicators(df_raw)
    
    # Fetch Context Data too
    df_15m = add_all_indicators(engine.fetch_data('15m', 4000))
    df_1h = add_all_indicators(engine.fetch_data('1h', 4000))
    
    # Set indices
    for df in [df_5m, df_15m, df_1h]:
        if 'timestamp' in df.columns:
            df.set_index('timestamp', inplace=True)
            
    # Mock Engine Class (Defined locally to wrap the real engine instance)
    # We can't easily patch the instance methods of 'engine'.
    # Better to subclass TradingEngine again and initialize it with this data.
    
    del engine # Free memory/cleanup
    
    print("   Initializing Backtest Sandbox...", flush=True)
    
    # Define Subclass Here
    class BacktestEngine(TradingEngine):
        def __init__(self, d5, d15, d1h):
            super().__init__()
            self.d5 = d5
            self.d15 = d15
            self.d1h = d1h
            self.current_t = None
            
        def set_time(self, t):
            self.current_t = t
            
        def fetch_data(self, interval='5m', limit=500):
            if interval == '5m': df = self.d5
            elif interval == '15m': df = self.d15
            elif interval == '1h': df = self.d1h
            else: return None
            
            # Slice up to current time
            mask = df.index <= self.current_t
            return df[mask].tail(limit).reset_index()

    # Create Mock Engine
    mock_engine = BacktestEngine(df_5m, df_15m, df_1h)
    
    # 3. Run Simulation Loop
    start_date = "2026-01-02 00:00:00"
    end_date = "2026-01-09 23:59:59"
    
    mask = (df_5m.index >= start_date) & (df_5m.index <= end_date)
    sim_candles = df_5m[mask]
    
    print(f"🔄 Simulating {len(sim_candles)} candles from {start_date} to {end_date}...", flush=True)
    
    trades = []
    
    for i, (timestamp, row) in enumerate(sim_candles.iterrows()):
        mock_engine.set_time(timestamp)
        
        # logic
        signal, conf = mock_engine.check_mtf_scalper()
        
        if signal:
            entry_price = signal['price']
            direction = signal['direction']
            
            tp_pct = 0.015
            sl_pct = 0.008
            
            if direction == 'LONG':
                tp_p = entry_price * (1+tp_pct)
                sl_p = entry_price * (1-sl_pct)
            else:
                tp_p = entry_price * (1-tp_pct)
                sl_p = entry_price * (1+sl_pct)
                
            # Outcome
            future_mask = df_5m.index > timestamp
            future = df_5m[future_mask]
            
            outcome = "OPEN"
            for _, f_row in future.iterrows():
                h, l = f_row['high'], f_row['low']
                if direction == 'LONG':
                    if h >= tp_p: outcome='WIN'; break
                    if l <= sl_p: outcome='LOSS'; break
                else:
                    if l <= tp_p: outcome='WIN'; break
                    if h >= sl_p: outcome='LOSS'; break
            
            mock_engine.report_outcome('MTF', outcome)
            trades.append({'outcome': outcome, 'dir': direction})
            
    # Report
    total = len(trades)
    if total > 0:
        wins = len([t for t in trades if t['outcome']=='WIN'])
        print(f"\n📊 Result: {wins}/{total} Wins ({wins/total*100:.1f}%)")
    else:
        print("❌ No trades.")

if __name__ == "__main__":
    run_bundled_verification()
