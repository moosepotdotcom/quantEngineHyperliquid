
import sys
import os
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION'))
sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION/utils'))

from quant_engine import TradingEngine, add_all_indicators

def run_platinum_tuning():
    print("💎 PLATINUM TUNING: OPTIMIZING BASE THRESHOLD")
    print("="*70)
    
    engine = TradingEngine()
    df_raw = engine.fetch_data('5m', 4000)
    df_raw = add_all_indicators(df_raw)
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
    
    print(f"✅ Data Ready: {len(sim_data)} rows. Testing...")
    
    # We test Base Thresholds with the PROVEN Adaptive Formula
    # Formula: Req = Base + max(0, (ATR-70)*0.002)
    bases = [0.45, 0.48, 0.50, 0.52, 0.55]
    
    for base in bases:
        trades = []
        # Simple simulation without CB state (approximation for speed/WR check)
        # Actually CB is crucial for WR. Let's assume CB is ON but checking raw stats first.
        
        for idx, row in sim_data.iterrows():
             # Predict
            row_vals = row.drop(labels=exclude + ['hurst'], errors='ignore')
            X = row_vals.values.reshape(1, -1)
            X = np.nan_to_num(X, nan=0.0)
            if X.shape[1] > 239: X = X[:, :239]
            
            p1 = engine.mtf_xgb.predict_proba(X)[0]
            p2 = engine.mtf_lgb.predict(X)[0]
            p3 = engine.mtf_cat.predict_proba(X)[0]
            
            # Consensus
            if np.max(np.std([p1, p2, p3], axis=0)) > 0.15: continue
            
            avg_prob = (p1 + p2 + p3) / 3
            conf_long, conf_short = avg_prob[1], avg_prob[2]
            
            # Adaptive Logic
            atr = row.get('atr_14', 50)
            penalty = max(0, (atr - 70) * 0.002)
            required = base + penalty
            
            signal = None
            if conf_long >= required: signal = 'LONG'
            elif conf_short >= required: signal = 'SHORT'
            
            if signal:
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
                
                trades.append(outcome)
        
        total = len(trades)
        wins = trades.count("WIN")
        wr = (wins/total * 100) if total > 0 else 0
        loss_count = total - wins
        pnl = (wins * 1.5) - (loss_count * 0.8)
        
        print(f"⚙️  Base {base:.2f}: {total:3d} Trades | WR: {wr:5.1f}% | PnL: {pnl:+.1f}%")

if __name__ == "__main__":
    run_platinum_tuning()
