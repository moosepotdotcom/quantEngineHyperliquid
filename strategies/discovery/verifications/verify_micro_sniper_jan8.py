
import sys
import os
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION'))
sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION/utils'))

from quant_engine import TradingEngine, add_all_indicators

def run_micro_jan8():
    print("💎 GEM SNIPER: MICRO STRATEGY (TARGET 400 PTS) - JAN 8")
    print("="*70)
    print("🎯 TP: 400 Points | SL: 200 Points")
    print("🛡️  ATR < 52.75 (Ultra Safety)")
    
    engine = TradingEngine()
    
    # 1. Fetch Data
    print("📥 Fetching Jan 2026 Data...", flush=True)
    df_raw = engine.fetch_data('5m', 4000)
    df_raw = add_all_indicators(df_raw)
    
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
    
    # 2. Filter Date Range (Jan 8)
    start_sim = pd.Timestamp("2026-01-08 00:00:00")
    end_sim = pd.Timestamp("2026-01-08 23:59:59")
    sim_data = df_merged[(df_merged.index >= start_sim) & (df_merged.index <= end_sim)]
    
    print(f"📊 Jan 8 Data: {len(sim_data)} candles", flush=True)
    
    # 3. Ultra ATR Limit
    limit = 52.75
    
    trades = []
    
    # DEBUG COUNTERS
    blocked_atr = 0
    low_confidence = 0
    
    for idx, row in sim_data.iterrows():
        atr_val = row.get('atr_14', 100)
        
        # ULTRA FILTER
        if atr_val > limit: 
            blocked_atr += 1
            if idx.minute == 0:
                 print(f"DEBUG: {idx} | ATR {atr_val:.1f} > {limit} (BLOCKED)", flush=True)
            continue
        
        # Predict
        row_vals = row.drop(labels=exclude + ['hurst'], errors='ignore')
        X = row_vals.values.reshape(1, -1)
        X = np.nan_to_num(X, nan=0.0)
        if X.shape[1] > 239: X = X[:, :239]
        
        p1 = engine.mtf_xgb.predict_proba(X)[0]
        p2 = engine.mtf_lgb.predict(X)[0]
        p3 = engine.mtf_cat.predict_proba(X)[0]
        
        avg_prob = (p1 + p2 + p3) / 3
        conf_long, conf_short = avg_prob[1], avg_prob[2]
        
        th = 0.45 
        
        signal = None
        if conf_long >= th: signal = 'LONG'
        elif conf_short >= th: signal = 'SHORT'
        else:
            low_confidence += 1
            if idx.minute == 0:
                 print(f"DEBUG: {idx} | ATR {atr_val:.1f} (OK) | CONF {max(conf_long, conf_short):.2f} < {th}", flush=True)
        
        if signal:
            entry_price = row['close']
            
            # FIXED POINT TARGETS (MICRO)
            TARGET_POINTS = 400
            STOP_POINTS = 200
            
            tp = entry_price + TARGET_POINTS if signal == 'LONG' else entry_price - TARGET_POINTS
            sl = entry_price - STOP_POINTS if signal == 'LONG' else entry_price + STOP_POINTS
            
            outcome = "OPEN"
            points = 0.0
            
            future_data = df_raw[df_raw.index > idx]
            for f_idx, f_row in future_data.iterrows():
                h, l = f_row['high'], f_row['low']
                
                if signal == 'LONG':
                    if h >= tp: 
                        outcome = "WIN"
                        points = TARGET_POINTS
                        break
                    if l <= sl: 
                        outcome = "LOSS"
                        points = -STOP_POINTS
                        break
                else:
                    if l <= tp: 
                        outcome = "WIN"
                        points = TARGET_POINTS
                        break
                    if h >= sl: 
                        outcome = "LOSS"
                        points = -STOP_POINTS
                        break
            
            if outcome != "OPEN":
                trades.append(outcome)
                out_icon = "✅ WIN " if outcome == "WIN" else "❌ LOSS"
                print(f"{str(idx):<20} | {signal:<5} | {entry_price:<10.2f} | {out_icon}", flush=True)
    
    total = len(trades)
    wins = trades.count("WIN")
    losses = trades.count("LOSS")
    wr = (wins/total * 100) if total > 0 else 0
    
    print("\n" + "="*70)
    print(f"📊 MICRO SNIPER RESULTS (Jan 8)")
    print(f"   Trades: {total}")
    print(f"   Win Rate: {wr:.1f}%")
    print(f"   Debug Info:")
    print(f"     - Candles Blocked by ATR: {blocked_atr}")
    print(f"     - Candles Blocked by Low Conf: {low_confidence}")
    print("="*70)

if __name__ == "__main__":
    run_micro_jan8()
