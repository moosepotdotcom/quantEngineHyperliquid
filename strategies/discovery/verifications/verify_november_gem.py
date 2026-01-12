
import sys
import os
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION'))
sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION/utils'))

from quant_engine import TradingEngine, add_all_indicators

def run_november_verification():
    print("💎 GEM SNIPER: NOVEMBER 2025 VERIFICATION")
    print("="*70)
    
    engine = TradingEngine()
    # Attempting to fetch 50,000 candles to reach back to November
    # 5m: 50,000 * 5 = 250,000 mins / 60 = 4166 hours / 24 = ~173 days.
    # This should cover Nov 2025 easily IF the API allows deep history in one go.
    print("🌐 Fetching deep history (50,000 candles)...")
    df_raw = engine.fetch_data('5m', 50000)
    df_raw = add_all_indicators(df_raw)
    
    try:
        from utils.advanced_features import get_rolling_hurst
        df_raw['hurst'] = get_rolling_hurst(df_raw, window=100)
    except:
        df_raw['hurst'] = 0.5 
        
    df_raw.set_index('timestamp', inplace=True)
    
    # Check what data we actually got
    min_date = df_raw.index.min()
    max_date = df_raw.index.max()
    print(f"📅 Data Retrieved Range: {min_date} to {max_date}")
    
    # Context
    df_15m = add_all_indicators(engine.fetch_data('15m', 50000))
    df_1h = add_all_indicators(engine.fetch_data('1h', 50000))
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
    
    # Target November 2025
    start_sim = pd.Timestamp("2025-11-01 00:00:00")
    end_sim = pd.Timestamp("2025-11-30 23:59:59")
    sim_data = df_merged[(df_merged.index >= start_sim) & (df_merged.index <= end_sim)]
    
    print(f"✅ Simulation Data Ready: {len(sim_data)} rows (November 2025).")
    
    if len(sim_data) == 0:
        print("❌ Error: Could not retrieve November 2025 data. API limit may restrict history.")
        return

    # Gem Sniper Ultra Limit
    limit = 52.75
    
    # Full Table Format
    print(f"\n🔍 GEM SNIPER ULTRA (ATR < {limit}) - NOVEMBER LOG")
    print(f"{'TIME':<20} | {'SIDE':<5} | {'ENTRY':<10} | {'TP':<10} | {'SL':<10} | {'ATR':<6} | {'DUR':<5} | {'PnL':<10} | {'OUTCOME'}")
    print("-" * 110)
    
    trades = []
    total_points = 0.0
    
    for idx, row in sim_data.iterrows():
        atr_val = row.get('atr_14', 100)
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
            pnl_amt = 0.0
            duration = 0
            
            future_data = df_raw[df_raw.index > idx]
            for f_idx, f_row in future_data.iterrows():
                duration += 5
                h, l = f_row['high'], f_row['low']
                
                if signal == 'LONG':
                    if h >= tp: 
                        outcome = "WIN"
                        points = tp - entry_price
                        pnl_amt = points
                        break
                    if l <= sl: 
                        outcome = "LOSS"
                        points = sl - entry_price
                        pnl_amt = points * -1 
                        break
                else:
                    if l <= tp: 
                        outcome = "WIN"
                        points = entry_price - tp
                        pnl_amt = points
                        break
                    if h >= sl: 
                        outcome = "LOSS"
                        points = entry_price - sl
                        pnl_amt = points * -1 
                        break
            
            if outcome != "OPEN":
                trades.append(outcome)
                total_points += pnl_amt
                print(f"{str(idx):<20} | {signal:<5} | {entry_price:<10.2f} | {tp:<10.2f} | {sl:<10.2f} | {atr_val:<6.1f} | {duration:<3}m | {pnl_amt:<+10.2f} | {outcome}")
    
    total = len(trades)
    wins = trades.count("WIN")
    wr = (wins/total * 100) if total > 0 else 0
    avg_points = total_points / total if total > 0 else 0
    
    print("\n" + "="*70)
    print(f"📊 NOVEMBER RESULTS")
    print(f"   Trades: {total}")
    print(f"   Win Rate: {wr:.1f}%")
    print(f"   Total PnL Points: {total_points:.2f}")
    print(f"   Avg Points: ${avg_points:.2f}")
    print("="*70)

if __name__ == "__main__":
    run_november_verification()
