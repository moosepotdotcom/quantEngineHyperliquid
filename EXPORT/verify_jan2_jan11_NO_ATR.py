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

# Define Mock Circuit Breaker
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
        # Clean old losses
        self.losses = [t for t in self.losses if (now - t).total_seconds() < self.window_minutes * 60]
        self.losses.append(now)
        if len(self.losses) >= self.max_losses:
            self.trip()
            
    def trip(self):
        self.cooldown_until = self.engine.current_t + timedelta(hours=self.cooldown_hours)
        print(f"   🛑 CIRCUIT BREAKER TRIGGERED! Pausing trading until {self.cooldown_until}")
        
    def reset(self):
        if not self.is_active():
            self.losses = []

    def is_active(self):
        if self.cooldown_until:
            if self.engine.current_t < self.cooldown_until:
                return True
            else:
                print(f"   🟢 Circuit Breaker Cooldown Expired at {self.engine.current_t}. Resuming.")
                self.cooldown_until = None
                self.losses = []
        return False

# Define the Optimized Backtest Engine Subclass
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

    # OVERRIDE: Check MTF Scalper WITHOUT adding indicators
    def check_mtf_scalper(self):
        # Fetch 5m base (Already has indicators!)
        df_5m = self.fetch_data('5m', 500)
        if df_5m is None or len(df_5m) == 0:
            return None, 0.0
        
        # Hurst
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
            
            atr_val = latest.get('atr_14', 50)
            required_conf = self.mtf_elastic.active_threshold_long if direction == 'LONG' else self.mtf_elastic.active_threshold_short
            
            if atr_val > 70:
                penalty = (atr_val - 70) * 0.002
                required_conf += penalty
                
            if confidence < required_conf:
                return None, confidence

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

def run_bundled_verification():
    print("📦 VERIFYING BUNDLED ENGINE (Jan 2 - Jan 11 2026)")
    print("   Data Source: Hyperliquid API (Live Fetch)")
    print("   🛡️ WITH POSITION MANAGEMENT (One at a time)")
    print("="*70)
    
    engine = TradingEngine()
    
    print("📥 Fetching Data (Limit 4000)...", flush=True)
    df_raw = engine.fetch_data('5m', 4000)
    
    if df_raw is None or len(df_raw) == 0:
        print("❌ API fetch failed.")
        return

    print(f"   Fetched {len(df_raw)} raw candles.")
    df_raw.sort_values('timestamp', inplace=True)
    df_5m = add_all_indicators(df_raw)
    
    print("   Fetching Context...", flush=True)
    df_15m = add_all_indicators(engine.fetch_data('15m', 4000))
    df_1h = add_all_indicators(engine.fetch_data('1h', 4000))
    
    for df in [df_5m, df_15m, df_1h]:
        if df is not None and 'timestamp' in df.columns:
            df.set_index('timestamp', inplace=True)
            
    del engine
    
    print("   Initializing Backtest Sandbox...", flush=True)
    mock_engine = BacktestEngine(df_5m, df_15m, df_1h)
    
    # INJECT MOCK CIRCUIT BREAKER
    mock_cb = MockCircuitBreaker(mock_engine)
    mock_engine.circuit_breaker = mock_cb

    # 3. Run Simulation Loop
    start_date = "2026-01-02 00:00:00"
    end_date = "2026-01-11 23:59:59"
    
    mask = (df_5m.index >= start_date) & (df_5m.index <= end_date)
    sim_candles = df_5m[mask]
    
    print(f"🔄 Simulating {len(sim_candles)} candles from {start_date} to {end_date}...")
    print("="*70)
    
    trades = []
    current_position = None  # Track open position
    
    total_candles = len(sim_candles)
    
    for i, (timestamp, row) in enumerate(sim_candles.iterrows()):
        if i % 100 == 0:
            print(f"   Processing candle {i}/{total_candles}...", end='\r')
            
        mock_engine.set_time(timestamp)
        
        # --- CRITICAL: CHECK IF WE HAVE AN OPEN POSITION ---
        if current_position is not None:
            # We have an open position - check if TP/SL hit
            entry_price = current_position['price']
            tp_price = current_position['tp']
            sl_price = current_position['sl']
            direction = current_position['dir']
            
            # Check current candle for TP/SL
            h, l = row['high'], row['low']
            
            if direction == 'LONG':
                if h >= tp_price:
                    # TP HIT!
                    outcome = 'WIN'
                    current_position['outcome'] = outcome
                    current_position['exit_time'] = timestamp
                    trades.append(current_position.copy())
                    
                    print(f"\n   ✅ WIN: {current_position['time'].strftime('%m-%d %H:%M')} → "
                          f"{timestamp.strftime('%m-%d %H:%M')} | "
                          f"{direction} @ ${entry_price:,.0f} | Conf {current_position['conf']:.3f}")
                    
                    # Report to circuit breaker
                    mock_engine.report_outcome('MTF', outcome)
                    current_position = None
                    continue
                    
                elif l <= sl_price:
                    # SL HIT!
                    outcome = 'LOSS'
                    current_position['outcome'] = outcome
                    current_position['exit_time'] = timestamp
                    trades.append(current_position.copy())
                    
                    print(f"\n   ❌ LOSS: {current_position['time'].strftime('%m-%d %H:%M')} → "
                          f"{timestamp.strftime('%m-%d %H:%M')} | "
                          f"{direction} @ ${entry_price:,.0f} | Conf {current_position['conf']:.3f}")
                    
                    # Report to circuit breaker
                    mock_engine.report_outcome('MTF', outcome)
                    current_position = None
                    continue
            
            else:  # SHORT
                if l <= tp_price:
                    outcome = 'WIN'
                    current_position['outcome'] = outcome
                    current_position['exit_time'] = timestamp
                    trades.append(current_position.copy())
                    
                    print(f"\n   ✅ WIN: {current_position['time'].strftime('%m-%d %H:%M')} → "
                          f"{timestamp.strftime('%m-%d %H:%M')} | "
                          f"{direction} @ ${entry_price:,.0f} | Conf {current_position['conf']:.3f}")
                    
                    mock_engine.report_outcome('MTF', outcome)
                    current_position = None
                    continue
                    
                elif h >= sl_price:
                    outcome = 'LOSS'
                    current_position['outcome'] = outcome
                    current_position['exit_time'] = timestamp
                    trades.append(current_position.copy())
                    
                    print(f"\n   ❌ LOSS: {current_position['time'].strftime('%m-%d %H:%M')} → "
                          f"{timestamp.strftime('%m-%d %H:%M')} | "
                          f"{direction} @ ${entry_price:,.0f} | Conf {current_position['conf']:.3f}")
                    
                    mock_engine.report_outcome('MTF', outcome)
                    current_position = None
                    continue
            
            # Position still open - skip signal check
            continue
        
        # --- NO POSITION - CHECK CIRCUIT BREAKER ---
        if mock_engine.circuit_breaker.is_active():
            continue
        
        # --- NO POSITION - CHECK FOR NEW SIGNALS ---
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
            
            # Open new position
            current_position = {
                'time': timestamp,
                'dir': direction,
                'conf': conf,
                'price': entry_price,
                'tp': tp_p,
                'sl': sl_p,
                'outcome': 'OPEN'
            }
            
            print(f"\n   📍 POSITION OPENED: {timestamp.strftime('%m-%d %H:%M')} | "
                  f"{direction} @ ${entry_price:,.0f} | "
                  f"TP: ${tp_p:,.0f} | SL: ${sl_p:,.0f}")

    # Report
    total = len(trades)
    print("\n" + "="*70)
    if total > 0:
        wins = len([t for t in trades if t['outcome']=='WIN'])
        losses = len([t for t in trades if t['outcome']=='LOSS'])
        win_rate = wins/total*100
        print(f"📊 Result: {wins}/{total} Wins ({win_rate:.1f}%)")
        print(f"   Losses: {losses}")
        print(f"   Win Rate: {win_rate:.1f}%")
    else:
        print("❌ No trades found in this period.")
    print("="*70)

if __name__ == "__main__":
    run_bundled_verification()
