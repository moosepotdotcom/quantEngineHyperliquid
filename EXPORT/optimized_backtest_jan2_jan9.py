
import sys
import os
import pandas as pd
import numpy as np
import warnings
from datetime import datetime, timedelta

# Suppress warnings
warnings.filterwarnings('ignore')

# Add path to find quant_engine
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quant_engine import TradingEngine

class BacktestEngine(TradingEngine):
    def __init__(self, raw5, raw15, raw1h):
        super().__init__()
        self.raw5 = raw5
        self.raw15 = raw15
        self.raw1h = raw1h
        self.current_t = None
        
        # Disable logging to file to speed up?
        # self.logger.log_prediction = lambda *args, **kwargs: None

    def set_time(self, t):
        self.current_t = t

    def fetch_data(self, interval='5m', limit=500):
        # Return SLICE of RAW data
        if interval == '5m': df = self.raw5
        elif interval == '15m': df = self.raw15
        elif interval == '1h': df = self.raw1h
        else: return None
        
        if df is None: return None
        
        # Optimize: ensure index is datetime
        # (It should be from init)
        
        # Slice
        mask = df.index <= self.current_t
        sliced = df[mask].tail(limit).copy()
        
        # Quant Engine expects 'timestamp' column if not index?
        # Actually it adds it if missing.
        # But for 'add_all_indicators' cleanly, we just pass the DF.
        # However, check_mtf_scalper expects fetch_data to return a DF.
        # Reset index to make 'timestamp' a column?
        # quant_engine.py: "df_5m = add_all_indicators(df_5m)"
        # feature_engineer.py: "if 'timestamp' not in df.columns: df['timestamp'] = df.index"
        # So we should Reset Index.
        return sliced.reset_index()

def run_recreation():
    print("🚀 RECREATION: 93% WIN RATE LOGIC (MTF Only, Sliced Calc)")
    print("   Period: Jan 2 - Jan 9 2026")
    
    # 1. Fetch Raw Data
    print("📥 Fetching Raw Data...", flush=True)
    temp = TradingEngine()
    # Need ample history to ensure Jan 2 start has 500 candles.
    # Jan 2 - 500*5m = Jan 1 approx.
    # Fetching 4000 candles ending Jan 9 covers Dec 26.
    raw5 = temp.fetch_data('5m', 4000)
    raw15 = temp.fetch_data('15m', 4000)
    raw1h = temp.fetch_data('1h', 4000)
    
    # Ensure index
    for df in [raw5, raw15, raw1h]:
        if 'timestamp' in df.columns:
            df.set_index('timestamp', inplace=True)
            
    print("✅ Data Fetched.")

    # 2. Init Engine
    engine = BacktestEngine(raw5, raw15, raw1h)
    
    # 3. Loop
    start_date = "2026-01-02 00:00:00"
    end_date = "2026-01-09 23:59:59"
    
    mask = (raw5.index >= start_date) & (raw5.index <= end_date)
    sim_candles = raw5[mask]
    
    print(f"🔄 Simulating {len(sim_candles)} candles...", flush=True)
    
    trades = []
    
    for i, (timestamp, row) in enumerate(sim_candles.iterrows()):
        if i % 50 == 0: print(f"   Processing {timestamp}...", end='\r')
        
        engine.set_time(timestamp)
        
        # MTF Only
        signal, _ = engine.check_mtf_scalper()
        
        if signal:
            price = signal['price']
            direction = signal['direction']
            model = signal['model']
            
            # Simple Outcome Logic (for verification)
            tp_pct = 0.015
            sl_pct = 0.008
            
            if direction == 'LONG':
                tp = price * (1+tp_pct)
                sl = price * (1-sl_pct)
            else:
                tp = price * (1-tp_pct)
                sl = price * (1+sl_pct)
                
            outcome = 'OPEN'
            future = raw5[raw5.index > timestamp]
            for _, f_row in future.iterrows():
                h, l = f_row['high'], f_row['low']
                if direction == 'LONG':
                    if h >= tp: outcome='WIN'; break
                    if l <= sl: outcome='LOSS'; break
                else:
                    if l <= tp: outcome='WIN'; break
                    if h >= sl: outcome='LOSS'; break
            
            # print(f"   🚨 {timestamp} | {direction} @ {price:.0f} | {outcome}")
            trades.append({
                'time': timestamp,
                'dir': direction,
                'price': price,
                'res': outcome,
                'tp': tp,
                'sl': sl
            })
            
    # Report & CSV
    import csv
    filename = 'trades_recreated_93.csv'
    if trades:
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['time', 'dir', 'price', 'res', 'tp', 'sl'])
            writer.writeheader()
            writer.writerows(trades)
        print(f"\n✅ Saved {len(trades)} trades to {filename}")
        
    print("\n" + "="*70)
    print("📊 93% RECREATION RESULTS")
    wins = len([t for t in trades if t['res']=='WIN'])
    losses = len([t for t in trades if t['res']=='LOSS'])
    total = len(trades)
    print(f"Total Trades: {total}")
    print(f"Wins: {wins}")
    print(f"Losses: {losses}")
    if total > 0:
        print(f"Win Rate: {wins/total*100:.1f}%")

if __name__ == "__main__":
    run_recreation()
