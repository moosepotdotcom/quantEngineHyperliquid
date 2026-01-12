
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

def run_filter_grid():
    print("🔬 FILTER PRECISION GRID SEARCH")
    print("="*70)
    
    engine = TradingEngine()
    df_raw = engine.fetch_data('5m', 4000)
    df_raw = add_all_indicators(df_raw)
    
    # Hurst
    try:
        from utils.advanced_features import get_rolling_hurst
        df_raw['hurst'] = get_rolling_hurst(df_raw, window=100)
    except:
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
    print("-" * 70)
    
    # Grid Search Params
    # Threshold fixed at 0.50 (since max is 0.56)
    rsi_tests = [30, 25, 20]
    hurst_tests = [0.5, 0.45, 0.40]
    consensus_tests = [0.15, 0.10, 0.05]
    
    best_wr = 0.0
    best_config = ""
    
    # Pre-calculate predictions to speed up grid
    predictions = []
    for idx, row in sim_data.iterrows():
        row_vals = row.drop(labels=exclude + ['hurst'], errors='ignore')
        X = row_vals.values.reshape(1, -1)
        X = np.nan_to_num(X, nan=0.0)
        if X.shape[1] > 239: X = X[:, :239]
        
        p1 = engine.mtf_xgb.predict_proba(X)[0]
        p2 = engine.mtf_lgb.predict(X)[0]
        p3 = engine.mtf_cat.predict_proba(X)[0]
        
        std_dev = np.std([p1, p2, p3], axis=0)
        max_disagreement = np.max(std_dev)
        
        avg_prob = (p1 + p2 + p3) / 3
        conf_long, conf_short = avg_prob[1], avg_prob[2]
        
        predictions.append({
            'idx': idx,
            'row': row,
            'conf_long': conf_long,
            'conf_short': conf_short,
            'disagreement': max_disagreement
        })

    for rsi_lim in rsi_tests:
        for hurst_lim in hurst_tests:
            for cons_lim in consensus_tests:
                
                trades = []
                
                for pred in predictions:
                    idx = pred['idx']
                    row = pred['row']
                    
                    # 1. Consensus
                    if pred['disagreement'] > cons_lim: continue
                    
                    # 2. Threshold 0.50
                    th = 0.50
                    signal = None
                    if pred['conf_long'] >= th: signal = 'LONG'
                    elif pred['conf_short'] >= th: signal = 'SHORT'
                    
                    if not signal: continue
                    
                    # 3. Filters
                    rsi = row.get('rsi_14', 50)
                    hurst = row.get('hurst', 0.5)
                    
                    # Long Filter
                    if signal == 'LONG':
                        if rsi > rsi_lim: continue # Must be Oversold < rsi_lim
                        if hurst > hurst_lim: continue # Must be Mean Reverting < hurst_lim
                        
                    # Short Filter (Flip)
                    if signal == 'SHORT':
                        if rsi < (100 - rsi_lim): continue # Overbought
                        if hurst > hurst_lim: continue
                        
                    # Outcome
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
                losses = trades.count("LOSS")
                wr = (wins/total * 100) if total > 0 else 0
                
                if total > 0:
                    print(f"🔧 RSI<{rsi_lim} | H<{hurst_lim} | D<{cons_lim} -> {total} Trades | WR: {wr:.1f}%")
                    
if __name__ == "__main__":
    run_filter_grid()
