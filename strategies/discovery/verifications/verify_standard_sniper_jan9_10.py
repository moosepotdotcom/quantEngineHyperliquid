
import sys
import os
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION'))
sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION/utils'))

from quant_engine import TradingEngine, add_all_indicators

def run_standard_simulation_jan9_10():
    print("💎 GEM SNIPER STANDARD (ATR < 60.00): JAN 9 - JAN 10")
    print("="*70)
    
    engine = TradingEngine()
    
    # 1. Fetch Data
    print("📥 Fetching Jan 2026 Data...")
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
    
    # 2. Filter Date Range (Jan 9 - 10)
    start_sim = pd.Timestamp("2026-01-09 00:00:00")
    end_sim = pd.Timestamp("2026-01-10 23:59:59")
    sim_data = df_merged[(df_merged.index >= start_sim) & (df_merged.index <= end_sim)]
    
    # 3. Standard ATR Limit
    limit = 60.00
    
    print(f"\n🔍 VERIFYING STANDARD CONFIG (ATR < {limit})")
    print(f"   Period: {start_sim} to {end_sim}")
    print(f"{'TIME':<20} | {'SIDE':<5} | {'ENTRY':<10} | {'TP':<10} | {'SL':<10} | {'ATR':<6} | {'DUR':<5} | {'OUTCOME'}")
    print("-" * 100)
    
    trades = []
    total_points = 0.0
    
    for idx, row in sim_data.iterrows():
        atr_val = row.get('atr_14', 100)
        
        # STANDARD FILTER
        if atr_val > limit: continue
        
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
        
        if signal:
            entry_price = row['close']
            tp = entry_price * (1.015 if signal == 'LONG' else 0.985)
            sl = entry_price * (0.992 if signal == 'LONG' else 1.008)
            
            outcome = "OPEN"
            points = 0.0
            duration = 0
            
            future_data = df_raw[df_raw.index > idx]
            for f_idx, f_row in future_data.iterrows():
                duration += 5
                h, l = f_row['high'], f_row['low']
                
                if signal == 'LONG':
                    if h >= tp: 
                        outcome = "WIN"
                        points = tp - entry_price
                        break
                    if l <= sl: 
                        outcome = "LOSS"
                        points = sl - entry_price
                        break
                else:
                    if l <= tp: 
                        outcome = "WIN"
                        points = entry_price - tp
                        break
                    if h >= sl: 
                        outcome = "LOSS"
                        points = entry_price - sl
                        break
            
            if outcome != "OPEN":
                trades.append(outcome)
                total_points += points
                
                # Format
                pnl_str = f"+{points:.2f}" if outcome == "WIN" else f"{points:.2f}"
                out_icon = "✅ WIN " if outcome == "WIN" else "❌ LOSS"
                
                print(f"{str(idx):<20} | {signal:<5} | {entry_price:<10.2f} | {tp:<10.2f} | {sl:<10.2f} | {atr_val:<6.1f} | {duration:<3}m | {out_icon}")
    
    total = len(trades)
    wins = trades.count("WIN")
    losses = trades.count("LOSS")
    wr = (wins/total * 100) if total > 0 else 0
    avg_points = total_points / total if total > 0 else 0
    
    print("\n" + "="*70)
    print(f"📊 STANDARD VERIFICATION RESULTS (Jan 9 - Jan 10)")
    print(f"   Trades: {total}")
    print(f"   Win Rate: {wr:.1f}% ({wins} W / {losses} L)")
    print(f"   Avg Points: ${avg_points:.2f}")
    print("="*70)

if __name__ == "__main__":
    run_standard_simulation_jan9_10()
