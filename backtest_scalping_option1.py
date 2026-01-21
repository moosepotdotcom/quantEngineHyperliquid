#!/usr/bin/env python3
"""
OPTION 1: Use Proven 93% Model with Scalping Targets
TP: 0.5% | SL: 0.3% | NO ATR Penalty
"""

import sys
sys.path.insert(0, '/Users/alifiyaa/Downloads/quantEngineHyperliquid/EXPORT')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from quant_engine import TradingEngine, add_all_indicators

class MockCircuitBreaker:
    def __init__(self, engine):
        self.engine = engine
        self.losses = []
        self.cooldown_until = None
        
    def record_loss(self):
        self.losses.append(self.engine.current_t)
        if len(self.losses) >= 2:
            self.cooldown_until = self.engine.current_t + timedelta(hours=4)
            print(f"   🛑 Circuit Breaker Triggered!")
            
    def reset(self):
        if not self.is_active():
            self.losses = []
    
    def is_active(self):
        if self.cooldown_until and self.engine.current_t < self.cooldown_until:
            return True
        if self.cooldown_until:
            self.cooldown_until = None
            self.losses = []
        return False

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
        if df is None: return None
        mask = df.index <= self.current_t
        return df[mask].tail(limit).reset_index()

print("\n" + "="*70)
print("🚀 SCALPING BACKTEST - PROVEN 93% MODEL")
print("TP: 0.5% | SL: 0.3% | NO ATR PENALTY")
print("="*70)

# Load data
print("\n📥 Loading data...")
engine = TradingEngine()
df_raw = engine.fetch_data('5m', 4000)

if df_raw is None:
    print("❌ Failed")
    sys.exit(1)

df_raw.sort_values('timestamp', inplace=True)
df_5m = add_all_indicators(df_raw)
df_15m = add_all_indicators(engine.fetch_data('15m', 4000))
df_1h = add_all_indicators(engine.fetch_data('1h', 4000))

for df in [df_5m, df_15m, df_1h]:
    if df is not None and 'timestamp' in df.columns:
        df.set_index('timestamp', inplace=True)

print("✅ Data loaded")

# Initialize
mock_engine = BacktestEngine(df_5m, df_15m, df_1h)
mock_engine.circuit_breaker = MockCircuitBreaker(mock_engine)

# Simulate
mask = (df_5m.index >= '2026-01-02') & (df_5m.index <= '2026-01-11 23:59:59')
sim_candles = df_5m[mask]

print(f"\n🔄 Simulating {len(sim_candles)} candles...")
print("="*70)

# SCALPING TARGETS
tp_pct = 0.005  # 0.5%
sl_pct = 0.003  # 0.3%

trades = []
current_position = None

for i, (timestamp, row) in enumerate(sim_candles.iterrows()):
    mock_engine.set_time(timestamp)
    
    # Check position
    if current_position is not None:
        entry_price = current_position['price']
        tp_price = current_position['tp']
        sl_price = current_position['sl']
        direction = current_position['dir']
        
        h, l = row['high'], row['low']
        
        if direction == 'LONG':
            if h >= tp_price:
                hold_hours = (timestamp - current_position['time']).total_seconds() / 3600
                trades.append({**current_position, 'outcome': 'WIN', 'hold_hours': hold_hours})
                print(f"   ✅ WIN: {current_position['time'].strftime('%m-%d %H:%M')} ({hold_hours:.1f}h)")
                mock_engine.circuit_breaker.reset()
                current_position = None
                continue
            elif l <= sl_price:
                hold_hours = (timestamp - current_position['time']).total_seconds() / 3600
                trades.append({**current_position, 'outcome': 'LOSS', 'hold_hours': hold_hours})
                print(f"   ❌ LOSS: {current_position['time'].strftime('%m-%d %H:%M')} ({hold_hours:.1f}h)")
                mock_engine.circuit_breaker.record_loss()
                current_position = None
                continue
        continue
    
    # Check circuit breaker
    if mock_engine.circuit_breaker.is_active():
        continue
    
    # Check for signal
    try:
        signal, conf = mock_engine.check_mtf_scalper()
        if signal:
            entry_price = signal['price']
            direction = signal['direction']
            
            if direction == 'LONG':
                tp_p = entry_price * (1+tp_pct)
                sl_p = entry_price * (1-sl_pct)
            else:
                tp_p = entry_price * (1-tp_pct)
                sl_p = entry_price * (1+sl_pct)
            
            current_position = {
                'time': timestamp,
                'dir': direction,
                'conf': conf,
                'price': entry_price,
                'tp': tp_p,
                'sl': sl_p
            }
            
            print(f"\n   📍 {direction} @ ${entry_price:,.0f} | Conf: {conf:.1%}")
    except:
        pass

# Results
print("\n" + "="*70)
print("📊 FINAL RESULTS")
print("="*70)

if trades:
    wins = len([t for t in trades if t['outcome'] == 'WIN'])
    losses = len([t for t in trades if t['outcome'] == 'LOSS'])
    total = len(trades)
    win_rate = wins / total * 100
    avg_hold = sum([t['hold_hours'] for t in trades]) / total
    
    capital = 53
    leverage = 27
    buying_power = capital * leverage
    
    pnl_per_win = buying_power * tp_pct
    pnl_per_loss = buying_power * sl_pct
    total_pnl = (wins * pnl_per_win) - (losses * pnl_per_loss)
    roi = (total_pnl / capital) * 100
    
    print(f"\nTrades: {total}")
    print(f"Wins: {wins} | Losses: {losses}")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"Avg Hold: {avg_hold:.1f}h")
    print(f"\nP&L: ${total_pnl:+.2f}")
    print(f"ROI: {roi:+.1f}%")
    print(f"Final Balance: ${capital + total_pnl:.2f}")
    
    print("\n" + "="*70)
    print("COMPARISON: Swing vs Scalping")
    print("="*70)
    print(f"{'Metric':<15} {'Swing (1.5%)':<15} {'Scalp (0.5%)':<15}")
    print("-"*70)
    print(f"{'Trades':<15} {'7':<15} {total:<15}")
    print(f"{'Win Rate':<15} {'71.4%':<15} {f'{win_rate:.1f}%':<15}")
    print(f"{'Avg Hold':<15} {'10h':<15} {f'{avg_hold:.1f}h':<15}")
    print(f"{'ROI':<15} {'+159%':<15} {f'{roi:+.1f}%':<15}")
    print("="*70)
else:
    print("\n❌ No trades completed")

print("\n✅ BACKTEST COMPLETE!")
