
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
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
        if self.last_loss_time and (timestamp - self.last_loss_time).total_seconds() > 3600:
            self.losses_in_window = 0
        self.losses_in_window += 1
        self.last_loss_time = timestamp
        if self.losses_in_window >= 2:
            self.pause_until = timestamp + pd.Timedelta(hours=4)
            # print(f"   🛑 CB TRIGGER at {timestamp}! Paused 4h.")
            self.losses_in_window = 0
            
    def is_paused(self, timestamp):
        return self.pause_until and timestamp < self.pause_until

def run_adaptive_sim():
    print("🕰️  SIMULATING: ADAPTIVE SHIELD V2 (ATR-70) CONFIG ...")
    print("="*70)
    print("🎯 Target: ~182 Trades, ~92% Win Rate")
    print("⚙️  Formala: Thresh = 0.45 + max(0, (ATR-70)*0.002)")
    
    engine = TradingEngine()
    df_raw = engine.fetch_data('5m', 4000)
    
    # Needs valid ATR! ensure indicators correct
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
    
    print(f"✅ Data Ready: {len(sim_data)} rows. Running...")
    
    cb = CircuitBreakerSim()
    trades = []
    
    for idx, row in sim_data.iterrows():
        # 1. Check Circuit Breaker
        if cb.is_paused(idx): continue
            
        # 2. Predict
        row_vals = row.drop(labels=exclude + ['hurst'], errors='ignore')
        X = row_vals.values.reshape(1, -1)
        X = np.nan_to_num(X, nan=0.0)
        if X.shape[1] > 239: X = X[:, :239]
        
        # Breakdown to check Consensus
        p1 = engine.mtf_xgb.predict_proba(X)[0]
        p2 = engine.mtf_lgb.predict(X)[0]
        p3 = engine.mtf_cat.predict_proba(X)[0]
        
        # Disagreement Check
        std_dev = np.std([p1, p2, p3], axis=0)
        max_disagreement = np.max(std_dev)
        if max_disagreement > 0.15: continue # Filter out
        
        avg_prob = (p1 + p2 + p3) / 3
        conf_long, conf_short = avg_prob[1], avg_prob[2]
        
        # 3. ADAPTIVE LOGIC V2
        # Default 0.45
        # ATR Penalty: Starts at 70
        atr = row.get('atr_14', 50)
        penalty = max(0, (atr - 70) * 0.002)
        
        required_conf = 0.45 + penalty
        
        signal = None
        if conf_long >= required_conf: signal = 'LONG'
        elif conf_short >= required_conf: signal = 'SHORT'
        
        # Hurst Filter (Falling Knife) check
        rsi = row.get('rsi_14', 50)
        hurst = 0.5 # Default 
        if signal == 'LONG' and rsi < 30 and hurst > 0.5:
             signal = None # Blocked
        
        # 4. Result
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
                    
            trades.append({'time': ts, 'type': signal, 'result': outcome, 'pnl': pnl})
            
            # CB Update
            if outcome == "LOSS":
                cb.record_loss(idx)

    print("\n" + "="*70)
    print(f"📊 ADAPTIVE SHIELD V2 RESULTS (Jan 2 - Jan 9)")
    print(f"   Config: ATR-70 Logic + CB + Consensus")
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
    run_adaptive_sim()
