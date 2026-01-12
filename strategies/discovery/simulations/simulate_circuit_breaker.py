
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION'))
sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION/utils'))

from quant_engine import TradingEngine, add_all_indicators

class CircuitBreakerSim:
    def __init__(self):
        self.losses_in_window = 0
        self.last_loss_time = None
        self.pause_until = None
        
    def record_loss(self, timestamp):
        # Reset count if > 60 mins since last loss
        if self.last_loss_time and (timestamp - self.last_loss_time).total_seconds() > 3600:
            self.losses_in_window = 0
            
        self.losses_in_window += 1
        self.last_loss_time = timestamp
        
        if self.losses_in_window >= 2:
            self.pause_until = timestamp + pd.Timedelta(hours=4)
            print(f"   🛑 CIRCUIT BREAKER TRIGGERED at {timestamp}! Paused until {self.pause_until}")
            self.losses_in_window = 0 # Reset? or keep strict? Implementation says reset after cooldown.
            
    def is_paused(self, timestamp):
        if self.pause_until and timestamp < self.pause_until:
            return True
        return False

def run_cb_simulation():
    print("🕰️  SIMULATING: ELASTIC THRESHOLD (0.45) + CIRCUIT BREAKER ONLY ...")
    print("="*70)
    
    engine = TradingEngine()
    df_raw = engine.fetch_data('5m', 4000)
    df_raw = add_all_indicators(df_raw)
    df_raw['hurst'] = 0.5 
    df_raw.set_index('timestamp', inplace=True)
    
    # Context
    df_15m = add_all_indicators(engine.fetch_data('15m', 4000))
    df_1h = add_all_indicators(engine.fetch_data('1h', 4000))
    df_15m.set_index('timestamp', inplace=True)
    df_1h.set_index('timestamp', inplace=True)
    
    exclude = ['open', 'high', 'low', 'close', 'volume', 'hurst']
    
    c15 = [c for c in df_15m.columns if c not in exclude]
    df15_r = df_15m[c15].copy()
    df15_r.columns = [f"{c}_15m" for c in c15]
    df_merged = pd.concat([df_raw, df15_r.reindex(df_raw.index, method='ffill')], axis=1)
    
    c1h = [c for c in df_1h.columns if c not in exclude]
    df1h_r = df_1h[c1h].copy()
    df1h_r.columns = [f"{c}_1h" for c in c1h]
    df_merged = pd.concat([df_merged, df1h_r.reindex(df_raw.index, method='ffill')], axis=1)
    
    start_sim = pd.Timestamp("2026-01-02 00:00:00")
    end_sim = pd.Timestamp("2026-01-09 23:59:59")
    sim_data = df_merged[(df_merged.index >= start_sim) & (df_merged.index <= end_sim)]
    
    print(f"✅ Data Ready: {len(sim_data)} rows.")
    
    cb = CircuitBreakerSim()
    trades = []
    
    for idx, row in sim_data.iterrows():
        # Check Circuit Breaker
        if cb.is_paused(idx):
            continue
            
        row_vals = row.drop(labels=exclude + ['hurst'], errors='ignore')
        X = row_vals.values.reshape(1, -1)
        X = np.nan_to_num(X, nan=0.0)
        if X.shape[1] > 239: X = X[:, :239]
        
        avg_prob = (engine.mtf_xgb.predict_proba(X)[0] + engine.mtf_lgb.predict(X)[0] + engine.mtf_cat.predict_proba(X)[0]) / 3
        conf_long, conf_short = avg_prob[1], avg_prob[2]
        
        threshold = 0.45
        signal = None
        if conf_long >= threshold: signal = 'LONG'
        elif conf_short >= threshold: signal = 'SHORT'
        
        if signal:
            ts = idx.strftime('%d-%H:%M')
            entry_price = row['close']
            tp = entry_price * (1.015 if signal == 'LONG' else 0.985)
            sl = entry_price * (0.992 if signal == 'LONG' else 1.008)
            
            outcome = "OPEN"
            pnl = 0.0
            
            future_data = df_raw[df_raw.index > idx]
            for _, f_row in future_data.iterrows():
                h, l = f_row['high'], f_row['low']
                if signal == 'LONG':
                    if h >= tp: outcome = "WIN"; pnl = 1.5; break
                    if l <= sl: outcome = "LOSS"; pnl = -0.8; break
                else:
                    if l <= tp: outcome = "WIN"; pnl = 1.5; break
                    if h >= sl: outcome = "LOSS"; pnl = -0.8; break
            
            if outcome == "WIN":
                # Reset bad streak? logic says count only losses
                pass
            elif outcome == "LOSS":
                cb.record_loss(idx)
                
            trades.append({'time': ts, 'type': signal, 'result': outcome, 'pnl': pnl})

    print("\n" + "="*70)
    print(f"📊 CB SIMULATION RESULTS (Jan 2 - Jan 9)")
    print(f"   Config: Threshold 0.45 + Circuit Breaker ONLY")
    print(f"   Total Trades: {len(trades)}")
    
    wins = [t for t in trades if t['result'] == 'WIN']
    
    if len(trades) > 0:
        wr = len(wins) / len(trades)
        print(f"   🎯 Win Rate: {wr:.1%}")
    else:
        print(f"   🎯 Win Rate: 0%")
        
    total_pnl = sum(t['pnl'] for t in trades)
    print(f"   💰 Total  PnL: {total_pnl:+.2f}%")
    print("="*70)

if __name__ == "__main__":
    run_cb_simulation()
