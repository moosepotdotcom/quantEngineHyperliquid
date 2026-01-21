#!/usr/bin/env python3
"""
PROPER BACKTEST: Original 93% Model with Scalping Targets
Uses proven EXPORT engine with 0.5% TP / 0.3% SL
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, '/Users/alifiyaa/Downloads/quantEngineHyperliquid/EXPORT')
from quant_engine import TradingEngine, add_all_indicators

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
        print(f"\n   🛑 CIRCUIT BREAKER TRIGGERED! Pausing until {self.cooldown_until.strftime('%H:%M')}")
        
    def reset(self):
        if not self.is_active():
            self.losses = []

    def is_active(self):
        if self.cooldown_until:
            if self.engine.current_t < self.cooldown_until:
                return True
            else:
                print(f"\n   🟢 Circuit Breaker Cooldown Expired. Resuming.")
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

    def check_mtf_scalper(self):
        df_5m = self.fetch_data('5m', 500)
        if df_5m is None or len(df_5m) == 0:
            return None, 0.0
        
        try:
            from utils.advanced_features import get_rolling_hurst
            if 'hurst' not in df_5m.columns:
                df_5m['hurst'] = get_rolling_hurst(df_5m, window=100)
        except ImportError:
            df_5m['hurst'] = 0.5

        if 'timestamp' in df_5m.columns:
            df_5m.set_index('timestamp', inplace=True)
            
        df_15m = self.fetch_data('15m', 500)
        if df_15m is None or len(df_15m) == 0: return None, 0.0
        if 'timestamp' in df_15m.columns: df_15m.set_index('timestamp', inplace=True)
        
        exclude = ['open', 'high', 'low', 'close', 'volume']
        ctx_cols_15m = [c for c in df_15m.columns if c not in exclude]
        df_15m_renamed = df_15m[ctx_cols_15m].copy()
        df_15m_renamed.columns = [f"{c}_15m" for c in ctx_cols_15m]
        df_15m_resampled = df_15m_renamed.reindex(df_5m.index, method='ffill')
        df_5m = pd.concat([df_5m, df_15m_resampled], axis=1)
        
        df_1h = self.fetch_data('1h', 500)
        if df_1h is None or len(df_1h) == 0: return None, 0.0
        if 'timestamp' in df_1h.columns: df_1h.set_index('timestamp', inplace=True)
        
        ctx_cols_1h = [c for c in df_1h.columns if c not in exclude]
        df_1h_renamed = df_1h[ctx_cols_1h].copy()
        df_1h_renamed.columns = [f"{c}_1h" for c in ctx_cols_1h]
        df_1h_resampled = df_1h_renamed.reindex(df_5m.index, method='ffill')
        df_5m = pd.concat([df_5m, df_1h_resampled], axis=1)
        
        df_5m.dropna(inplace=True)
        if len(df_5m) == 0: return None, 0.0
        
        all_exclude = exclude + ['timestamp', 'hurst']
        features = [c for c in df_5m.columns if c not in all_exclude]
        latest = df_5m.iloc[-1]
        X = latest[features].values.reshape(1, -1)
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        
        if X.shape[1] > 239: X = X[:, :239]
        
        probas = self.get_ensemble_proba('MTF', X)[0]
        prob_long = float(probas[1])
        prob_short = float(probas[2])
        
        direction = None
        confidence = 0.0
        
        self.mtf_elastic.update(prob_long, prob_short)
        
        if prob_long >= self.mtf_elastic.active_threshold_long:
            direction = 'LONG'
            confidence = prob_long
        elif prob_short >= self.mtf_elastic.active_threshold_short:
            direction = 'SHORT'
            confidence = prob_short
        
        if direction:
            price = float(latest['close'])
            if not price or price <= 0: return None, confidence
            
            rsi = latest.get('rsi_14', 50)
            hurst = latest.get('hurst', 0.5)
            
            if direction == 'LONG' and rsi < 30 and hurst > 0.50:
                return None, confidence
            
            # NO ATR PENALTY for scalping
            
            rsi7 = latest.get('rsi_7', 50)
            if direction == 'SHORT' and rsi7 < 25:
                return None, confidence
            
            return {
                'model': 'MTF Scalper (5M)',
                'timestamp': self.current_t if self.current_t else datetime.now(),
                'price': price,
                'direction': direction,
                'confidence': confidence,
                'rsi': float(latest.get('rsi_14', 0)),
                'macd': float(latest.get('macd', 0)),
                'atr_pct': (float(latest.get('atr_14', 0)) / price * 100) if price > 0 else 0
            }, confidence
        
        return None, max(prob_long, prob_short)

print("\n" + "🚀"*35)
print("SCALPING BACKTEST - ORIGINAL 93% MODEL")
print("TP: 0.5% | SL: 0.3% | NO ATR PENALTY")
print("🚀"*35)

# Load data
print("\n📥 Loading data...")
engine = TradingEngine()
df_raw = engine.fetch_data('5m', 4000)

if df_raw is None:
    print("❌ Failed to fetch data")
    sys.exit(1)

df_raw.sort_values('timestamp', inplace=True)
df_5m = add_all_indicators(df_raw)
df_15m = add_all_indicators(engine.fetch_data('15m', 4000))
df_1h = add_all_indicators(engine.fetch_data('1h', 4000))

for df in [df_5m, df_15m, df_1h]:
    if df is not None and 'timestamp' in df.columns:
        df.set_index('timestamp', inplace=True)

del engine

print(f"✅ Data loaded")

# Initialize backtest engine
mock_engine = BacktestEngine(df_5m, df_15m, df_1h)
mock_cb = MockCircuitBreaker(mock_engine)
mock_engine.circuit_breaker = mock_cb

# Run simulation
start_date = "2026-01-02 00:00:00"
end_date = "2026-01-11 23:59:59"

mask = (df_5m.index >= start_date) & (df_5m.index <= end_date)
sim_candles = df_5m[mask]

print(f"\n🔄 Simulating {len(sim_candles)} candles...")
print("="*70)

# SCALPING TARGETS
tp_pct = 0.005  # 0.5%
sl_pct = 0.003  # 0.3%

trades = []
current_position = None

for i, (timestamp, row) in enumerate(sim_candles.iterrows()):
    if i % 500 == 0:
        print(f"   Progress: {i}/{len(sim_candles)} ({i/len(sim_candles)*100:.0f}%)", end='\r')
    
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
                trades.append({**current_position, 'outcome': 'WIN', 'exit_time': timestamp, 'hold_hours': hold_hours})
                print(f"\n   ✅ WIN: {current_position['time'].strftime('%m-%d %H:%M')} → {timestamp.strftime('%m-%d %H:%M')} ({hold_hours:.1f}h)")
                mock_engine.report_outcome('MTF', 'WIN')
                current_position = None
                continue
            elif l <= sl_price:
                hold_hours = (timestamp - current_position['time']).total_seconds() / 3600
                trades.append({**current_position, 'outcome': 'LOSS', 'exit_time': timestamp, 'hold_hours': hold_hours})
                print(f"\n   ❌ LOSS: {current_position['time'].strftime('%m-%d %H:%M')} → {timestamp.strftime('%m-%d %H:%M')} ({hold_hours:.1f}h)")
                mock_engine.report_outcome('MTF', 'LOSS')
                current_position = None
                continue
        else:  # SHORT
            if l <= tp_price:
                hold_hours = (timestamp - current_position['time']).total_seconds() / 3600
                trades.append({**current_position, 'outcome': 'WIN', 'exit_time': timestamp, 'hold_hours': hold_hours})
                print(f"\n   ✅ WIN: {current_position['time'].strftime('%m-%d %H:%M')} → {timestamp.strftime('%m-%d %H:%M')} ({hold_hours:.1f}h)")
                mock_engine.report_outcome('MTF', 'WIN')
                current_position = None
                continue
            elif h >= sl_price:
                hold_hours = (timestamp - current_position['time']).total_seconds() / 3600
                trades.append({**current_position, 'outcome': 'LOSS', 'exit_time': timestamp, 'hold_hours': hold_hours})
                print(f"\n   ❌ LOSS: {current_position['time'].strftime('%m-%d %H:%M')} → {timestamp.strftime('%m-%d %H:%M')} ({hold_hours:.1f}h)")
                mock_engine.report_outcome('MTF', 'LOSS')
                current_position = None
                continue
        continue
    
    # Check circuit breaker
    if mock_engine.circuit_breaker.is_active():
        continue
    
    # Check for signals
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

# Results
print("\n\n" + "="*70)
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
    print(f"Final: ${capital + total_pnl:.2f}")
    
    print("\n" + "="*70)
    print("COMPARISON")
    print("="*70)
    print(f"{'Metric':<15} {'Swing (1.5%)':<15} {'Scalp (0.5%)':<15}")
    print("-"*70)
    print(f"{'Trades':<15} {'7':<15} {total:<15}")
    print(f"{'Win Rate':<15} {'71.4%':<15} {f'{win_rate:.1f}%':<15}")
    print(f"{'Avg Hold':<15} {'10h':<15} {f'{avg_hold:.1f}h':<15}")
    print(f"{'ROI':<15} {'+159%':<15} {f'{roi:+.1f}%':<15}")
    print("="*70)
else:
    print("No trades")

print("\n✅ DONE!")
