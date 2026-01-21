#!/usr/bin/env python3
"""
FULL BACKTEST: Jan 2-11, 2026
Uses EXPORT 93% model to generate ALL signals with 0.5% TP / 0.3% SL
"""

import sys
import os
sys.path.insert(0, '/Users/alifiyaa/Downloads/quantEngineHyperliquid/EXPORT')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("\n" + "="*70)
print("🚀 FULL BACKTEST: JAN 2-11, 2026")
print("Model: EXPORT 93% Engine | TP: 0.5% | SL: 0.3% | NO ATR")
print("="*70)

# Import after path is set
from quant_engine import TradingEngine, add_all_indicators

# Fetch data
print("\n📡 Fetching data from Hyperliquid API...")
engine = TradingEngine()

try:
    df_5m_raw = engine.fetch_data('5m', 4000)
    df_15m_raw = engine.fetch_data('15m', 4000)
    df_1h_raw = engine.fetch_data('1h', 4000)
    
    if df_5m_raw is None:
        raise Exception("Failed to fetch 5m data")
    
    print(f"✅ Fetched data: {len(df_5m_raw)} 5m candles")
    
    # Add indicators
    print("🔧 Adding indicators...")
    df_5m = add_all_indicators(df_5m_raw)
    df_15m = add_all_indicators(df_15m_raw)
    df_1h = add_all_indicators(df_1h_raw)
    
    # Set index
    for df in [df_5m, df_15m, df_1h]:
        if 'timestamp' in df.columns:
            df.set_index('timestamp', inplace=True)
    
    print("✅ Indicators added")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nCannot proceed without data. Exiting...")
    sys.exit(1)

# Backtest engine
class BacktestEngine(TradingEngine):
    def __init__(self, d5, d15, d1h):
        super().__init__()
        self.d5, self.d15, self.d1h = d5, d15, d1h
        self.current_t = None
        
    def set_time(self, t):
        self.current_t = t
        
    def fetch_data(self, interval='5m', limit=500):
        df = self.d5 if interval=='5m' else (self.d15 if interval=='15m' else self.d1h)
        if df is None: return None
        return df[df.index <= self.current_t].tail(limit).reset_index()

# Circuit breaker
class MockCB:
    def __init__(self, e):
        self.engine, self.losses, self.cooldown_until = e, [], None
    def record_loss(self):
        self.losses.append(self.engine.current_t)
        if len(self.losses) >= 2:
            self.cooldown_until = self.engine.current_t + timedelta(hours=4)
    def reset(self):
        if not self.is_active(): self.losses = []
    def is_active(self):
        if self.cooldown_until and self.engine.current_t < self.cooldown_until: return True
        if self.cooldown_until: self.cooldown_until, self.losses = None, []
        return False

# Initialize
be = BacktestEngine(df_5m, df_15m, df_1h)
be.circuit_breaker = MockCB(be)

# Filter to Jan 2-11
mask = (df_5m.index >= '2026-01-02') & (df_5m.index <= '2026-01-11 23:59:59')
sim = df_5m[mask]

print(f"\n🔄 Simulating {len(sim)} candles (Jan 2-11)...")
print("="*70)

# SCALPING TARGETS
tp_pct, sl_pct = 0.005, 0.003

trades, pos, signal_count = [], None, 0

for i, (ts, row) in enumerate(sim.iterrows()):
    if i % 500 == 0:
        print(f"Progress: {i}/{len(sim)} ({i/len(sim)*100:.0f}%)", end='\r')
    
    be.set_time(ts)
    
    # Check position
    if pos:
        h, l = row['high'], row['low']
        if pos['dir'] == 'LONG':
            if h >= pos['tp']:
                ht = (ts - pos['time']).total_seconds() / 3600
                trades.append({**pos, 'outcome': 'WIN', 'exit_time': ts, 'hold_hours': ht})
                print(f"\n✅ WIN: {pos['time'].strftime('%m-%d %H:%M')} ({ht:.1f}h)")
                be.circuit_breaker.reset()
                pos = None
                continue
            elif l <= pos['sl']:
                ht = (ts - pos['time']).total_seconds() / 3600
                trades.append({**pos, 'outcome': 'LOSS', 'exit_time': ts, 'hold_hours': ht})
                print(f"\n❌ LOSS: {pos['time'].strftime('%m-%d %H:%M')} ({ht:.1f}h)")
                be.circuit_breaker.record_loss()
                pos = None
                continue
        continue
    
    if be.circuit_breaker.is_active():
        continue
    
    # Get signal
    try:
        sig, conf = be.check_mtf_scalper()
        if sig:
            signal_count += 1
            ep, d = sig['price'], sig['direction']
            tp_p = ep * (1+tp_pct) if d=='LONG' else ep * (1-tp_pct)
            sl_p = ep * (1-sl_pct) if d=='LONG' else ep * (1+sl_pct)
            pos = {'time': ts, 'dir': d, 'conf': conf, 'price': ep, 'tp': tp_p, 'sl': sl_p}
            print(f"\n📍 Signal #{signal_count}: {d} @ ${ep:,.0f} | {conf:.1%}")
    except:
        pass

# Results
print("\n\n" + "="*70)
print("📊 BACKTEST RESULTS - JAN 2-11, 2026")
print("="*70)

print(f"\nSignals Generated: {signal_count}")
print(f"Trades Completed: {len(trades)}")

if trades:
    w = len([t for t in trades if t['outcome']=='WIN'])
    l = len([t for t in trades if t['outcome']=='LOSS'])
    wr = w/len(trades)*100
    ah = sum([t['hold_hours'] for t in trades])/len(trades)
    
    cap, lev = 53, 27
    bp = cap * lev
    
    pnl = (w * bp * tp_pct) - (l * bp * sl_pct)
    roi = pnl/cap*100
    
    print(f"\nWins: {w} | Losses: {l}")
    print(f"Win Rate: {wr:.1f}%")
    print(f"Avg Hold: {ah:.1f}h")
    print(f"\nP&L: ${pnl:+.2f}")
    print(f"ROI: {roi:+.1f}%")
    print(f"Final: ${cap+pnl:.2f}")
    
    print("\n" + "="*70)
    print("COMPARISON")
    print("="*70)
    print(f"{'Metric':<15} {'Swing':<15} {'Scalp':<15} {'Change':<15}")
    print("-"*70)
    print(f"{'Trades':<15} {'7':<15} {len(trades):<15} {f'{len(trades)-7:+d}':<15}")
    print(f"{'Win Rate':<15} {'71.4%':<15} {f'{wr:.1f}%':<15} {f'{wr-71.4:+.1f}%':<15}")
    print(f"{'Avg Hold':<15} {'10h':<15} {f'{ah:.1f}h':<15} {f'{ah-10:.1f}h':<15}")
    print(f"{'ROI':<15} {'+159%':<15} {f'{roi:+.1f}%':<15} {f'{roi-159:+.1f}%':<15}")
    print("="*70)
else:
    print("\n❌ No trades completed")

print("\n✅ BACKTEST COMPLETE!")
