
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Add path access
sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION'))
sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION/utils'))

from quant_engine import TradingEngine, add_all_indicators

def run_reproduction():
    print("🕰️  STARTING 'NO FILTER' REPRODUCTION (JAN 2 - JAN 9)...")
    print("="*70)
    print("🎯 Target: ~182 Trades, ~92% Win Rate")
    print("⚙️  Settings: Threshold 0.45 (Fixed), Trend Filter DISABLED")
    
    engine = TradingEngine()
    
    # Data Fetch
    print("📥 Fetching historical data...")
    limit = 4000
    df_raw = engine.fetch_data('5m', limit) 
    
    if df_raw is None or len(df_raw) == 0:
        return

    # Base Processing
    df_raw = add_all_indicators(df_raw)
    df_raw['hurst'] = 0.5 
    df_raw.set_index('timestamp', inplace=True)
    
    # Context
    print("📊 Preparing MTF Context...")
    df_15m = add_all_indicators(engine.fetch_data('15m', limit))
    df_1h = add_all_indicators(engine.fetch_data('1h', limit))
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
    
    # Filter Date
    start_sim = pd.Timestamp("2026-01-02 00:00:00")
    end_sim = pd.Timestamp("2026-01-09 23:59:59")
    sim_data = df_merged[(df_merged.index >= start_sim) & (df_merged.index <= end_sim)]
    
    print(f"✅ Simulation Ready: {len(sim_data)} candles")
    
    trades = []
    
    for idx, row in sim_data.iterrows():
        # Predict
        row_vals = row.drop(labels=exclude + ['hurst'], errors='ignore')
        X = row_vals.values.reshape(1, -1)
        X = np.nan_to_num(X, nan=0.0)
        if X.shape[1] > 239: X = X[:, :239]
        
        avg_prob = (engine.mtf_xgb.predict_proba(X)[0] + engine.mtf_lgb.predict(X)[0] + engine.mtf_cat.predict_proba(X)[0]) / 3
        conf_long, conf_short = avg_prob[1], avg_prob[2]
        
        # LOGIC: Fixed 0.45 Threshold, NO Regime Filter
        threshold = 0.45
        signal = None
        
        if conf_long >= threshold: signal = 'LONG'
        elif conf_short >= threshold: signal = 'SHORT'
        
        if signal:
            # NO FILTER CHECK
            # We just take it!
            
            ts = idx.strftime('%d-%H:%M')
            entry_price = row['close']
            tp = entry_price * (1.015 if signal == 'LONG' else 0.985)
            sl = entry_price * (0.992 if signal == 'LONG' else 1.008)
            
            outcome = "OPEN"
            pnl = 0.0
            
            # Future Outcome
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

    print("\n" + "="*70)
    print(f"📊 REPRODUCTION RESULTS (Jan 2 - Jan 9)")
    print(f"   Settings: Threshold 0.45 | Filter: OFF")
    print(f"   Total Trades: {len(trades)}")
    
    wins = [t for t in trades if t['result'] == 'WIN']
    losses = [t for t in trades if t['result'] == 'LOSS']
    
    if len(trades) > 0:
        wr = len(wins) / len(trades)
        print(f"   🎯 Win Rate: {wr:.1%}")
    else:
        print(f"   🎯 Win Rate: 0%")
        
    total_pnl = sum(t['pnl'] for t in trades)
    print(f"   💰 Total  PnL: {total_pnl:+.2f}%")
    print("="*70)

if __name__ == "__main__":
    run_reproduction()
