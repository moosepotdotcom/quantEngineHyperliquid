
import sys
import os
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION'))
sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION/utils'))

from quant_engine import TradingEngine, add_all_indicators

def debug_jan7_10():
    print("🕵️‍♂️ DIAGNOSTIC: JAN 7 - JAN 10 BLOCKED TRADES ANALYSIS")
    print("="*100)
    
    engine = TradingEngine()
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
    
    # Target Jan 7 - Jan 10
    start_sim = pd.Timestamp("2026-01-07 00:00:00")
    end_sim = pd.Timestamp("2026-01-10 23:59:59")
    sim_data = df_merged[(df_merged.index >= start_sim) & (df_merged.index <= end_sim)]
    
    print(f"{'TIME':<20} | {'SIDE':<5} | {'CONF':<6} | {'ATR':<6} | {'STATUS':<20} | {'RESULT'}")
    print("-" * 100)
    
    GEM_LIMIT = 52.75
    
    blocked_wins = 0
    blocked_losses = 0
    
    for idx, row in sim_data.iterrows():
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
        
        # Check if there WAS a signal candidates (using relaxed 0.45)
        raw_signal = None
        conf = 0
        if conf_long >= 0.45: raw_signal = 'LONG'; conf = conf_long
        elif conf_short >= 0.45: raw_signal = 'SHORT'; conf = conf_short
        
        if raw_signal:
            atr_val = row.get('atr_14', 100)
            status = "ACCEPTED"
            if atr_val > GEM_LIMIT: status = "BLOCKED (ATR)"
            
            # Determine hypothetical outcome
            entry_price = row['close']
            tp = entry_price * (1.015 if raw_signal == 'LONG' else 0.985)
            sl = entry_price * (0.992 if raw_signal == 'LONG' else 1.008)
            
            outcome = "OPEN"
            future_data = df_raw[df_raw.index > idx]
            for _, f_row in future_data.iterrows():
                h, l = f_row['high'], f_row['low']
                if raw_signal == 'LONG':
                    if h >= tp: outcome = "WIN"; break
                    if l <= sl: outcome = "LOSS"; break
                else:
                    if l <= tp: outcome = "WIN"; break
                    if h >= sl: outcome = "LOSS"; break
            
            if status == "BLOCKED (ATR)":
                if outcome == "WIN": blocked_wins += 1
                if outcome == "LOSS": blocked_losses += 1
            
            print(f"{str(idx):<20} | {raw_signal:<5} | {conf:<6.2f} | {atr_val:<6.1f} | {status:<20} | {outcome}")

    print("\n" + "="*100)
    print(f"📊 BLOCKED TRADES SUMMARY (What we missed)")
    print(f"   Blocked Wins:   {blocked_wins}")
    print(f"   Blocked Losses: {blocked_losses}")
    if blocked_wins + blocked_losses > 0:
        avoided_loss_ratio = blocked_losses / (blocked_wins + blocked_losses)
        print(f"   Loss Avoidance: {avoided_loss_ratio:.1%} of blocked trades were LOSSES")
    print("="*100)

if __name__ == "__main__":
    debug_jan7_10()
