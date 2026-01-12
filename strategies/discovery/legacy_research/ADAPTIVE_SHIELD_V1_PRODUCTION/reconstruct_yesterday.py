import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add path access
sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION'))
sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION/utils'))

from quant_engine import TradingEngine, add_all_indicators

def reconstruct_trades():
    print("🔄 RECONSTRUCTING TRADES FOR YESTERDAY (Jan 9, 2026)...")
    print("="*60)
    
    engine = TradingEngine()
    
    # Define Date Range
    start_date = pd.Timestamp('2026-01-09 00:00:00')
    end_date = pd.Timestamp('2026-01-10 00:00:00')
    
    print(f"\n📥 Fetching historical data covering {start_date.date()}...")
    
    # Fetch ample data (1500 candles ~ 5 days) to ensure full cover + context
    df_raw = engine.fetch_data('5m', 1500) 
    
    if df_raw is None or len(df_raw) == 0:
        print("❌ Failed to fetch data")
        return

    print("⚠️  Reconstruction requires full MTF context.")
    print("   Running analysis on buffered historical data...")
    
    # Fetch 1h, 15m, 5m (Historical buffer)
    # 1500 candles is enough to cover Jan 9 + Jan 10 + context
    df_5m = engine.fetch_data('5m', 1500)
    df_15m = engine.fetch_data('15m', 1500)
    df_1h = engine.fetch_data('1h', 1500)
    
    # Feature Engineering
    print("   🔧 Generating indicators...")
    df_5m = add_all_indicators(df_5m)
    df_15m = add_all_indicators(df_15m)
    df_1h = add_all_indicators(df_1h)
    
    # Merge (MTF Logic)
    df_5m.set_index('timestamp', inplace=True)
    df_15m.set_index('timestamp', inplace=True)
    df_1h.set_index('timestamp', inplace=True)
    
    exclude = ['open', 'high', 'low', 'close', 'volume']
    
    # 15m Merge
    ctx_cols_15m = [c for c in df_15m.columns if c not in exclude]
    df_15m_renamed = df_15m[ctx_cols_15m].copy()
    df_15m_renamed.columns = [f"{c}_15m" for c in ctx_cols_15m]
    df_15m_resampled = df_15m_renamed.reindex(df_5m.index, method='ffill')
    df_5m = pd.concat([df_5m, df_15m_resampled], axis=1)
    
    # 1h Merge
    ctx_cols_1h = [c for c in df_1h.columns if c not in exclude]
    df_1h_renamed = df_1h[ctx_cols_1h].copy()
    df_1h_renamed.columns = [f"{c}_1h" for c in ctx_cols_1h]
    df_1h_resampled = df_1h_renamed.reindex(df_5m.index, method='ffill')
    df_5m = pd.concat([df_5m, df_1h_resampled], axis=1)
    
    # Filter for TARGET DATE (Jan 9)
    target_data = df_5m[(df_5m.index >= start_date) & (df_5m.index < end_date)]
    
    print(f"📊 Analyzing {len(target_data)} candles from Jan 9...")
    
    signals_found = 0
    high_conf_list = []
    
    # Predict loop
    for idx, row in target_data.iterrows():
        # Clean Features
        row_vals = row.drop(labels=exclude + ['hurst'], errors='ignore')
        X = row_vals.values.reshape(1, -1)
        X = np.nan_to_num(X, nan=0.0)
        
        # Trim to model expected shape (239)
        if X.shape[1] > 239: X = X[:, :239]
        
        # Ensemble Prediction
        p1 = engine.mtf_xgb.predict_proba(X)[0]
        p2 = engine.mtf_lgb.predict(X)[0]
        p3 = engine.mtf_cat.predict_proba(X)[0]
        
        # Soft Voting
        avg_prob = (p1 + p2 + p3) / 3
        prob_long = avg_prob[1]
        prob_short = avg_prob[2]
        
        ts = idx.strftime('%H:%M')
        
        # Threshold Check (> 50%)
        if prob_long > 0.50:
            print(f"⏰ {ts} | 🟢 LONG Signal | Conf: {prob_long:.2%} (Threshold 50%)")
            signals_found += 1
            high_conf_list.append((ts, 'LONG', prob_long))
        elif prob_short > 0.55:
             print(f"⏰ {ts} | 🔴 SHORT Signal | Conf: {prob_short:.2%} (Threshold 55%)")
             signals_found += 1
             high_conf_list.append((ts, 'SHORT', prob_short))
        
        # Also log near misses for context
        elif prob_long > 0.45 or prob_short > 0.45:
             # print(f"   (Near Miss) {ts}: L:{prob_long:.2%} S:{prob_short:.2%}")
             pass
             
    if signals_found == 0:
        print("\n✅ RESULT: No trades identified for Jan 9.")
        print("   Max Confidence observed did not exceed 50%.")
    else:
        print(f"\n⚠️ RESULT: {signals_found} trades would have triggered on Jan 9.")
        print("   Note: These occurred before the circuit breaker/shields might have intervened if active.")

if __name__ == "__main__":
    reconstruct_trades()
