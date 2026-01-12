
import sys
import os
import pandas as pd
import numpy as np
import warnings
from datetime import datetime, timedelta
import builtins

# Suppress warnings
warnings.filterwarnings('ignore')

# Add path to find quant_engine
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the real components
from quant_engine import TradingEngine
import utils.feature_engineer

# Monkeypatch removed to allow on-the-fly calculation



class MockCircuitBreaker:
    def __init__(self, engine, max_losses=2, window_minutes=60, cooldown_hours=4):
        self.engine = engine
        self.max_losses = max_losses
        self.window_minutes = window_minutes
        self.cooldown_hours = cooldown_hours
        self.losses = []
        self.cooldown_until = None
        
    def record_loss(self):
        now = self.engine.current_t
        self.losses = [t for t in self.losses if (now - t).total_seconds() < self.window_minutes * 60]
        self.losses.append(now)
        if len(self.losses) >= self.max_losses:
            self.trip()
            
    def trip(self):
        self.cooldown_until = self.engine.current_t + timedelta(hours=self.cooldown_hours)
        # print(f"   🛑 CIRCUIT BREAKER TRIGGERED! Pausing trading until {self.cooldown_until}")
        
    def reset(self):
        if not self.is_active():
            self.losses = []

    def is_active(self):
        if self.cooldown_until:
            if self.engine.current_t < self.cooldown_until:
                return True
            else:
                self.cooldown_until = None
                self.losses = []
        return False

class BacktestEngine(TradingEngine):
    def __init__(self, d5, d15, d1h):
        # We must initialize without calling super().__init__ triggers that fetch data?
        # TradingEngine.__init__ loads models, which is fine.
        # But it doesn't fetch data in init.
        super().__init__()
        self.d5 = d5
        self.d15 = d15
        self.d1h = d1h
        self.current_t = None
        
        # Override circuit breaker with mock
        self.circuit_breaker = MockCircuitBreaker(self)
        
    def set_time(self, t):
        self.current_t = t
        
    def fetch_data(self, interval='5m', limit=500):
        # Return pre-calculated data slice
        if interval == '5m': df = self.d5
        elif interval == '15m': df = self.d15
        elif interval == '1h': df = self.d1h
        else: return None
        
        if df is None: return None
        
        # Slicing for backtest
        # ideally we use searchsorted for speed, but this is python
        mask = df.index <= self.current_t
        subset = df[mask].tail(limit).copy() # return copy to be safe
        
        # Quant engine expects 'timestamp' column, but we might have it as index
        # Let's reset index if needed, OR ensure index is not lost.
        # Original fetch_data returns dataframe with 'timestamp' COLUMN.
        if 'timestamp' not in subset.columns:
            subset.reset_index(inplace=True)
            
        return subset

def run_backtest():
    print("🚀 BACKTESTING FULL ENGINE (Jan 2 - Jan 9 2026)")
    print("   Models: Winner Hunter (1H) + MTF Scalper (5M)")
    print("="*70)
    
    # Use a temp engine to fetch raw data
    # (We can't use BacktestEngine yet)
    temp_engine = TradingEngine()
    
    print("📥 Fetching Raw Data (Limit 5000)...", flush=True)
    try:
        raw_5m = temp_engine.fetch_data('5m', 5000)
        raw_15m = temp_engine.fetch_data('15m', 5000)
        raw_1h = temp_engine.fetch_data('1h', 5000)
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        return

    if raw_5m is None:
        print("❌ API returned None")
        return

    print("   Using Raw Data injection (indicators calculated on-the-fly)...")
    
    # Use Raw Dataframes
    d5 = raw_5m.copy()
    d15 = raw_15m.copy()
    d1h = raw_1h.copy()
    
    for df in [d5, d15, d1h]:
        if 'timestamp' in df.columns:
            df.set_index('timestamp', inplace=True)
            
    engine = BacktestEngine(d5, d15, d1h)
    
    # Run Simulation
    start_date = "2026-01-02 00:00:00"
    end_date = "2026-01-09 23:59:59"
    
    mask = (d5.index >= start_date) & (d5.index <= end_date)
    sim_candles = d5[mask]
    
    print(f"🔄 Simulating {len(sim_candles)} candles...", flush=True)
    
    trades = []
    
    for i, (timestamp, row) in enumerate(sim_candles.iterrows()):
        if i % 100 == 0:
            print(f"   Processing {timestamp}...", end='\r')
            
        engine.set_time(timestamp)
        
        # Check CB
        if engine.circuit_breaker.is_active():
            continue
            
        # Run Checks
        wh_signal, wh_bias = None, 0
        mtf_signal, mtf_bias = None, 0
        
        try:
           wh_signal, wh_bias = engine.check_winner_hunter()
        except Exception as e:
           # print(f"WH Error: {e}")
           pass
           
        try:
           mtf_signal, mtf_bias = engine.check_mtf_scalper()
        except Exception as e:
           # print(f"MTF Error: {e}")
           pass
           
        # Combine signals
        active_signal = None
        source = ""
        
        if wh_signal:
            active_signal = wh_signal
            source = "WH"
        elif mtf_signal:
            active_signal = mtf_signal
            source = "MTF"
            
        if active_signal:
            price = active_signal.get('price', 0)
            direction = active_signal.get('direction', 'LONG')
            conf = active_signal.get('confidence', 0)
            
            if not price: continue
            
            # Simple Trade Logic
            outcome = "OPEN"
            tp = price * 1.015 if direction == 'LONG' else price * 0.985
            sl = price * 0.992 if direction == 'LONG' else price * 1.008
            
            # Look forward
            future = d5[d5.index > timestamp].copy()
            for _, f_row in future.iterrows():
                h, l = f_row['high'], f_row['low']
                if direction == 'LONG':
                    if h >= tp: outcome='WIN'; break
                    if l <= sl: outcome='LOSS'; break
                else:
                    if l <= tp: outcome='WIN'; break
                    if h >= sl: outcome='LOSS'; break
            
            # Update CB
            engine.report_outcome(source, outcome)
            
            trades.append({
                'time': timestamp,
                'model': source,
                'dir': direction,
                'price': price,
                'outcome': outcome,
                'conf': conf
            })
            
            print(f"   🚨 {timestamp} | {source} {direction} | ${price:.0f} | {outcome}")

    # Summary
    print("\n" + "="*70)
    print("📊 BACKTEST REPORT")
    print("="*70)
    
    if not trades:
        print("No trades generated.")
    else:
        wins = len([t for t in trades if t['outcome'] == 'WIN'])
        losses = len([t for t in trades if t['outcome'] == 'LOSS'])
        total = wins + losses
        wr = (wins/total*100) if total > 0 else 0
        
        print(f"Total Trades: {total} (Wins: {wins}, Losses: {losses})")
        print(f"Win Rate: {wr:.2f}%")
        
        # PnL calc
        pnl = (wins * 1.5) - (losses * 0.8)
        print(f"Estimated PnL: +{pnl:.1f}%")

if __name__ == "__main__":
    run_backtest()
