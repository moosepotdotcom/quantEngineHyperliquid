
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
from utils.feature_engineer import add_all_indicators

def slice_data(df, current_time, limit=500):
    if df is None: return None
    # Assuming df is sorted by index (timestamp)
    # Use searchsorted for speed if possible, or just boolean mask
    # Boolean mask is fast enough for 4000 rows
    mask = df.index <= current_time
    return df[mask].tail(limit).copy()

class BacktestEngine(TradingEngine):
    def __init__(self, d5_basic, d5_adv, d15_basic, d15_adv, d1h_basic, d1h_adv):
        super().__init__()
        self.d5_basic = d5_basic
        self.d5_adv = d5_adv
        self.d15_basic = d15_basic
        self.d15_adv = d15_adv
        self.d1h_basic = d1h_basic
        self.d1h_adv = d1h_adv
        
        self.current_t = None
        self.circuit_breaker_active_until = None
        self.losses = []

    def set_time(self, t):
        self.current_t = t

    def check_circuit_breaker(self):
        # Simple mock CB
        if self.circuit_breaker_active_until:
             if self.current_t < self.circuit_breaker_active_until:
                 return True
             else:
                 self.circuit_breaker_active_until = None
                 self.losses = []
        return False

    def report_outcome(self, model, outcome):
        if outcome == 'LOSS':
             now = self.current_t
             self.losses = [t for t in self.losses if (now - t).total_seconds() < 3600]
             self.losses.append(now)
             if len(self.losses) >= 2:
                 self.circuit_breaker_active_until = now + timedelta(hours=4)
        elif outcome == 'WIN':
             self.losses = []

    # ------------------------------------------------------------------
    # OPTIMIZED OVERRIDES
    # ------------------------------------------------------------------

    def check_winner_hunter(self):
        # Uses BASIC features (use_advanced=False) for everything to match 231 limit
        
        # 1. Fetch 1H Base (Basic)
        df_1h = slice_data(self.d1h_basic, self.current_t)
        if df_1h is None or len(df_1h) == 0: return None, 0.0
        # Already has indicators!
        
        # 2. Fetch 5m Context (Basic) - Used for resampling
        df_5m = slice_data(self.d5_basic, self.current_t)
        if df_5m is not None and len(df_5m) > 0:
            exclude = ['open', 'high', 'low', 'close', 'volume']
            ctx_cols_5m = [c for c in df_5m.columns if c not in exclude]
            df_5m_ctx = df_5m[ctx_cols_5m].copy()
            df_5m_ctx.columns = [f"{c}_5m" for c in ctx_cols_5m]
            df_5m_resampled = df_5m_ctx.reindex(df_1h.index, method='ffill')
            df_1h = pd.concat([df_1h, df_5m_resampled], axis=1)

        # 3. Fetch 15m Context (Basic)
        df_15m = slice_data(self.d15_basic, self.current_t)
        if df_15m is not None and len(df_15m) > 0:
            ctx_cols_15m = [c for c in df_15m.columns if c not in exclude]
            df_15m_ctx = df_15m[ctx_cols_15m].copy()
            df_15m_ctx.columns = [f"{c}_15m" for c in ctx_cols_15m]
            df_15m_resampled = df_15m_ctx.reindex(df_1h.index, method='ffill')
            df_1h = pd.concat([df_1h, df_15m_resampled], axis=1)

        df_1h.dropna(inplace=True)
        if len(df_1h) == 0: return None, 0.0

        exclude_cols = ['open', 'high', 'low', 'close', 'volume']
        features = [c for c in df_1h.columns if c not in exclude_cols]
        latest = df_1h.iloc[-1]
        X = latest[features].values.reshape(1, -1)
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

        # Predict
        try:
             probas = self.get_ensemble_proba('WH', X)[0]
             # (Simplified logic from original)
             prob_long = float(probas[1])
             prob_short = float(probas[2])
             
             direction = None
             confidence = max(prob_long, prob_short)
             
             # Using hardcoded thresholds from logs or metadata to match engine
             # WH Thresholds: L:0.3278, S:0.4089
             if prob_long >= 0.3278: direction = 'LONG'
             elif prob_short >= 0.4089: direction = 'SHORT'
             
             if direction:
                 return {
                     'model': 'Winner Hunter (1H)',
                     'price': float(latest['close']),
                     'direction': direction,
                     'confidence': confidence
                 }, confidence
             return None, confidence
        except Exception:
             return None, 0.0

    def check_mtf_scalper(self):
        # Uses ADVANCED features (use_advanced=True)
        
        # 1. Fetch 5m Base (Advanced)
        df_5m = slice_data(self.d5_adv, self.current_t)
        if df_5m is None or len(df_5m) == 0: return None, 0.0
        # Already has indicators + Hurst!
        
        # 2. Fetch 15m Context (Advanced)
        df_15m = slice_data(self.d15_adv, self.current_t)
        if df_15m is not None and len(df_15m) > 0:
            exclude = ['open', 'high', 'low', 'close', 'volume']
            ctx_cols = [c for c in df_15m.columns if c not in exclude]
            renamed = df_15m[ctx_cols].copy()
            renamed.columns = [f"{c}_15m" for c in ctx_cols]
            resampled = renamed.reindex(df_5m.index, method='ffill')
            df_5m = pd.concat([df_5m, resampled], axis=1)
            
        # 3. Fetch 1h Context (Advanced)
        df_1h = slice_data(self.d1h_adv, self.current_t)
        if df_1h is not None and len(df_1h) > 0:
            ctx_cols = [c for c in df_1h.columns if c not in exclude]
            renamed = df_1h[ctx_cols].copy()
            renamed.columns = [f"{c}_1h" for c in ctx_cols]
            resampled = renamed.reindex(df_5m.index, method='ffill')
            df_5m = pd.concat([df_5m, resampled], axis=1)
            
        df_5m.dropna(inplace=True)
        if len(df_5m) == 0: return None, 0.0
        
        # Features
        all_exclude = exclude + ['timestamp', 'hurst']
        features = [c for c in df_5m.columns if c not in all_exclude]
        latest = df_5m.iloc[-1]
        X = latest[features].values.reshape(1, -1)
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        
        # Trimming for MTF Scalper (Known requirement)
        if X.shape[1] > 239: X = X[:, :239]
        
        probas = self.get_ensemble_proba('MTF', X)[0]
        prob_long, prob_short = float(probas[1]), float(probas[2])
        
        direction = None
        confidence = max(prob_long, prob_short)
        
        # Thresholds: L:0.45, S:0.45 (Default)
        base_thresh = 0.45
        
        # Adaptive Shield Logic
        atr_val = latest.get('atr_14', 50)
        required = base_thresh
        if atr_val > 70:
            required += (atr_val - 70) * 0.002
            
        if confidence < required:
            return None, confidence
            
        # Direction
        if prob_long >= required: direction = 'LONG'
        elif prob_short >= required: direction = 'SHORT'
        
        # Filters
        if direction == 'LONG':
             rsi = latest.get('rsi_14', 50)
             hurst = latest.get('hurst', 0.5)
             if rsi < 30 and hurst > 0.5: return None, confidence
             
        if direction == 'SHORT':
             rsi7 = latest.get('rsi_7', 50)
             if rsi7 < 25: return None, confidence
             
        if direction:
             return {
                 'model': 'MTF Scalper (5M)',
                 'price': float(latest['close']),
                 'direction': direction,
                 'confidence': confidence
             }, confidence
             
        return None, confidence

def run_opt_backtest():
    print("🚀 OPTIMIZED BACKTEST (Jan 2 - Jan 9 2026)")
    
    # 1. Fetch Raw Data
    print("📥 Fetching Data...", flush=True)
    temp = TradingEngine()
    # Need Jan 2 to Jan 9. 7 days.
    # 7 * 24 * 12 = 2016 candles. fetch 4000.
    raw5 = temp.fetch_data('5m', 4000)
    raw15 = temp.fetch_data('15m', 4000)
    raw1h = temp.fetch_data('1h', 4000)
    
    # 2. Pre-Calculate Features
    print("⚙️ Pre-calculating Features (This runs ONCE)...", flush=True)
    
    # helper
    def prep(df, adv):
        res = add_all_indicators(df, use_advanced=adv)
        if 'timestamp' in res.columns: res.set_index('timestamp', inplace=True)
        return res
        
    d5_basic = prep(raw5, False)
    d5_adv   = prep(raw5, True)
    d15_basic= prep(raw15, False)
    d15_adv  = prep(raw15, True)
    d1h_basic= prep(raw1h, False)
    d1h_adv  = prep(raw1h, True)
    
    print("✅ Feature Calculation Complete.")
    
    # 3. Init Engine
    engine = BacktestEngine(d5_basic, d5_adv, d15_basic, d15_adv, d1h_basic, d1h_adv)
    
    # 4. Loop
    start_date = "2026-01-02 00:00:00"
    end_date = "2026-01-07 23:59:59"
    
    # Loop over 5m index
    mask = (d5_basic.index >= start_date) & (d5_basic.index <= end_date)
    sim_candles = d5_basic[mask]
    
    print(f"🔄 Simulating {len(sim_candles)} candles (Jan 2 - Jan 7)...", flush=True)
    
    trades = []
    
    for i, (timestamp, row) in enumerate(sim_candles.iterrows()):
        if i % 200 == 0: print(f"   Processing {timestamp}...", end='\r')
        
        engine.set_time(timestamp)
        if engine.check_circuit_breaker(): continue
        
        # Checks
        wh_s, _ = engine.check_winner_hunter()
        mtf_s, _ = engine.check_mtf_scalper()
        
        active = wh_s or mtf_s
        # Priority to WH? Or create separate trades?
        # Logic: If both trigger, prioritize WH (bigger timeframe).
        if wh_s and mtf_s: active = wh_s 
        
        if active:
            price = active['price']
            direction = active['direction']
            model = active['model']
            
            # Outcome Check
            outcome = 'OPEN'
            tp = price * 1.015 if direction == 'LONG' else price * 0.985
            sl = price * 0.992 if direction == 'LONG' else price * 1.008
            
            future = d5_basic[d5_basic.index > timestamp]
            for _, f_row in future.iterrows():
                h, l = f_row['high'], f_row['low']
                if direction == 'LONG':
                    if h >= tp: outcome='WIN'; break
                    if l <= sl: outcome='LOSS'; break
                else:
                    if l <= tp: outcome='WIN'; break
                    if h >= sl: outcome='LOSS'; break
            
            engine.report_outcome(model, outcome)
            
            # print(f"   🚨 {timestamp} | {model} {direction} @ {price:.0f} | {outcome}")
            trades.append({
                'time': timestamp,
                'model': model, 
                'dir': direction,
                'price': price,
                'res': outcome,
                'tp': tp,
                'sl': sl
            })
            
    # Save to CSV
    if trades:
        import csv
        with open('trades_jan2_jan7.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['time', 'model', 'dir', 'price', 'res', 'tp', 'sl'])
            writer.writeheader()
            writer.writerows(trades)
        print(f"\n✅ Saved {len(trades)} trades to trades_jan2_jan7.csv")

    # Report
    print("\n" + "="*70)
    print("📊 FINAL REPORT (Jan 2 - Jan 7)")
    wins = len([t for t in trades if t['res']=='WIN'])
    losses = len([t for t in trades if t['res']=='LOSS']) # Count losses specifically
    total = len(trades)
    print(f"Total Trades: {total}")
    print(f"Wins: {wins}")
    print(f"Losses: {losses}")
    if total > 0:
        print(f"Win Rate: {wins/total*100:.1f}%")
        pnl = (wins * 1.5) - (losses * 0.8)
        print(f"Estimated PnL: {pnl:.1f}%")

if __name__ == "__main__":
    run_opt_backtest()
