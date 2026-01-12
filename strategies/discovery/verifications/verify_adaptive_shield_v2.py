
import sys
import os
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION'))
sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION/utils'))

from quant_engine import TradingEngine, add_all_indicators

def run_adaptive_shield_v2():
    print("🛡️ ADAPTIVE SHIELD V2: SIMULATION (JAN 2 - JAN 9)")
    print("="*70)
    print("Logic:")
    print("  - ATR < 70: Threshold 0.45")
    print("  - ATR > 70: Threshold = 0.45 + ((ATR - 70) * 0.002)")
    
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
    
    # 2. Filter Date Range (Jan 2 - Jan 9)
    start_sim = pd.Timestamp("2026-01-02 00:00:00")
    end_sim = pd.Timestamp("2026-01-09 23:59:59")
    sim_data = df_merged[(df_merged.index >= start_sim) & (df_merged.index <= end_sim)]
    
    print(f"📊 Simulation Candles: {len(sim_data)}", flush=True)
    
    trades = []
    
    # CIRCUIT BREAKER STATE
    loss_timestamps = []
    circuit_breaker_until = None
    
    for idx, row in sim_data.iterrows():
        # 1. Enforce Circuit Breaker
        if circuit_breaker_until:
            if idx < circuit_breaker_until:
                continue
            else:
                # Cooldown expired
                circuit_breaker_until = None
                loss_timestamps = [] # Reset on resume
        
        atr_val = row.get('atr_14', 100)
        
        # DYNAMIC THRESHOLD LOGIC
        base_threshold = 0.45
        required_threshold = base_threshold
        
        if atr_val > 70:
            # Increase by 0.2% per ATR point above 70
            # 0.2% = 0.002
            excess_atr = atr_val - 70
            penalty = excess_atr * 0.002
            required_threshold = base_threshold + penalty
            
            # Cap threshold at reasonable limit (e.g. 0.95) to prevent absurdity, though math handles it
            if required_threshold > 0.95: required_threshold = 0.95
            
        
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
        
        signal = None
        if conf_long >= required_threshold: signal = 'LONG'
        elif conf_short >= required_threshold: signal = 'SHORT'
        
        if signal:
            entry_price = row['close']
            
            # --- MANDALORIAN & AI SMART FILTERS ---
            
            # 1. Falling Knife Detector (Mandalorian)
            # Block Dip Buy (Low RSI) if Trending (High Hurst)
            # If Hurst > 0.5, it's trending. Buying a dip (RSI < 30) is catching a falling knife.
            rsi_val = row.get('rsi_14', 50)
            hurst_val = row.get('hurst', 0.5)
            
            if signal == 'LONG' and rsi_val < 30 and hurst_val > 0.50:
                # print(f"DEBUG: {idx} | Blocked Falling Knife (H={hurst_val:.2f}, RSI={rsi_val:.1f})")
                continue
                
            # 2. AI Smart Filter
            # Don't SHORT if extremely oversold (RSI_7 < 25)
            # We need to ensure rsi_7 is calculated or present
            rsi7_val = row.get('rsi_7', 50) 
            if signal == 'SHORT' and rsi7_val < 25:
                # print(f"DEBUG: {idx} | Blocked Oversold Short (RSI7={rsi7_val:.1f})")
                continue
            
            # --------------------------------------
            
            tp = entry_price * (1.015 if signal == 'LONG' else 0.985)
            sl = entry_price * (0.992 if signal == 'LONG' else 1.008)
            
            outcome = "OPEN"
            points = 0.0
            
            future_data = df_raw[df_raw.index > idx]
            for f_idx, f_row in future_data.iterrows():
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
                # CIRCUIT BREAKER LOGIC
                if outcome == "LOSS":
                    loss_timestamps.append(idx)
                    # Keep only losses in last 60 mins
                    loss_timestamps = [t for t in loss_timestamps if (idx - t).total_seconds() < 3600]
                    
                    if len(loss_timestamps) >= 2:
                        timeout_candles = 48 # 4 hours / 5 min
                        circuit_breaker_until = idx + pd.Timedelta(hours=4)
                        # print(f"🛑 CIRCUIT BREAKER TRIPPED at {idx}! Pausing until {circuit_breaker_until}")
                else:
                    # Reset on WIN? The code says reset(), assuming it clears streaks.
                    loss_timestamps = [] 

                trades.append(outcome)
                out_icon = "✅ WIN " if outcome == "WIN" else "❌ LOSS"
                print(f"{str(idx):<20} | {signal:<5} | ATR: {atr_val:.1f} | {out_icon}", flush=True)
    
    total = len(trades)
    wins = trades.count("WIN")
    losses = trades.count("LOSS")
    wr = (wins/total * 100) if total > 0 else 0
    
    print("\n" + "="*70)
    print(f"📊 ADAPTIVE SHIELD V2 RESULTS (Jan 2 - Jan 9)")
    print(f"   Trades: {total}")
    print(f"   Win Rate: {wr:.1f}% ({wins} W / {losses} L)")
    print("="*70)

if __name__ == "__main__":
    run_adaptive_shield_v2()
