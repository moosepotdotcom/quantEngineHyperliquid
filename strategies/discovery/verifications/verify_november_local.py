
import sys
import os
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION'))
sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION/utils'))

from quant_engine import TradingEngine, add_all_indicators

def run_november_local_verification():
    print("💎 GEM SNIPER: NOVEMBER 2025 VERIFICATION (Local Data)")
    print("="*70)
    
    engine = TradingEngine()
    
    csv_path = 'training/data/BTC_5m_mtf_features.csv'
    # Load only necessary columns: Timestamp, OHLC, Vol
    # File has header: timestamp,open,high,low,close,volume,...
    try:
        # LOAD ALL COLUMNS (Pre-calculated features)
        df_raw = pd.read_csv(csv_path)
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return

    # Parse dates
    df_raw['timestamp'] = pd.to_datetime(df_raw['timestamp'])
    df_raw.set_index('timestamp', inplace=True)
    df_raw.sort_index(inplace=True) # Ensure sorted
    
    # Filter for November 2025 (plus some buffer for indicators)
    start_buffer = pd.Timestamp("2025-10-25 00:00:00") 
    end_data = pd.Timestamp("2025-11-30 23:59:59")
    
    df_raw = df_raw[(df_raw.index >= start_buffer) & (df_raw.index <= end_data)]
    print(f"✅ Data Loaded: {len(df_raw)} rows (Oct 25 - Nov 30).")
    
    # Force Float
    cols = ['open', 'high', 'low', 'close', 'volume']
    for c in cols:
        df_raw[c] = pd.to_numeric(df_raw[c], errors='coerce')
    df_raw.dropna(subset=cols, inplace=True)
    print("dtypes:", df_raw.dtypes.head())
    
    # DEBUG: Inspect Dataframe
    print("\n🔍 DATAFRAME INSPECTION:")
    print(f"Columns: {df_raw.columns.tolist()}")
    print(f"Head:\n{df_raw.head(3)}")
    print(f"Tail:\n{df_raw.tail(3)}")
    print(f"ATR Stats:\n{df_raw['atr_14'].describe() if 'atr_14' in df_raw.columns else 'ATR MISSING'}")
    
    if len(df_raw) == 0:
        print("❌ No November data found in CSV.")
        return

    # Engineer Features (SKIPPED - Using Pre-calculated)
    print("⚡ Using Pre-calculated indicators from CSV...")
    # df_raw = add_all_indicators(df_raw)
    
    # Ensure hurst exists (it might not be in CSV)
    if 'hurst' not in df_raw.columns:
        df_raw['hurst'] = 0.5 
        
    # Resample for Context (15m, 1h) - We will just forward fill 5m features as approx if needed, 
    # OR better: assume strict 5m logic is enough for verification context
    # But the model needs _15m columns.
    # The CSV likely has them? Check headers?
    # The headers show `rsi_7_15m` etc!
    # So we don't need to resample/calculate either!
    
    # We just need to make sure column names match what the bot expects.
    # The bot uses `_15m` suffix which is present in CSV.
    
    # We create df_merged as just df_raw since it has everything?
    df_merged = df_raw.copy()

    
    # Target Strict November
    start_sim = pd.Timestamp("2025-11-01 00:00:00")
    end_sim = pd.Timestamp("2025-11-30 23:59:59")
    sim_data = df_merged[(df_merged.index >= start_sim) & (df_merged.index <= end_sim)]
    
    print(f"✅ Simulation Ready: {len(sim_data)} rows (November 2025).")
    
    limit = 52.75
    
    print(f"\n🔍 GEM SNIPER ULTRA (ATR < {limit}) - NOVEMBER LOG")
    print(f"{'TIME':<20} | {'SIDE':<5} | {'ENTRY':<10} | {'TP':<10} | {'SL':<10} | {'ATR':<6} | {'DUR':<5} | {'PnL':<10} | {'OUTCOME'}")
    print("-" * 110)
    
    trades = []
    total_points = 0.0
    
    for idx, row in sim_data.iterrows():
        atr_val = row.get('atr_14', 100)
        
        # Predict
        row_vals = row.drop(labels=exclude + ['hurst'], errors='ignore')
        
        # DEBUG: Print first row details
        if idx == sim_data.index[0]:
            print(f"DEBUG: First Row Index: {idx}")
            print(f"DEBUG: ATR: {atr_val}")
            print(f"DEBUG: Feature Cols: {row_vals.index.tolist()[:10]} ... ({len(row_vals)} features)")
        
        X = row_vals.values.reshape(1, -1)
        X = np.nan_to_num(X, nan=0.0)
        if X.shape[1] > 239: X = X[:, :239]
        
        p1 = engine.mtf_xgb.predict_proba(X)[0]
        p2 = engine.mtf_lgb.predict(X)[0]
        p3 = engine.mtf_cat.predict_proba(X)[0]
        
        avg_prob = (p1 + p2 + p3) / 3
        conf_long, conf_short = avg_prob[1], avg_prob[2]
        
        if idx == sim_data.index[0]:
             print(f"DEBUG: Probs -> L:{conf_long:.4f} S:{conf_short:.4f}")
        
        if atr_val > limit: continue
        
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
    run_november_local_verification()
