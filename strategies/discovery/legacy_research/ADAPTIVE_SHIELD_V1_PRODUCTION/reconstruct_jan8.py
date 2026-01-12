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
    print("🔄 RECONSTRUCTING TRADES FOR JAN 8, 2026...")
    print("="*60)
    
    engine = TradingEngine()
    
    # Define Date Range (Jan 8)
    start_date = pd.Timestamp('2026-01-08 00:00:00')
    end_date = pd.Timestamp('2026-01-09 00:00:00')
    
    print(f"\n📥 Fetching historical data covering {start_date.date()}...")
    
    # Fetch ample data (2000 candles ~ 7 days) to ensure we reach back to Jan 8 with context
    limit = 2000
    df_raw = engine.fetch_data('5m', limit) 
    
    if df_raw is None or len(df_raw) == 0:
        print("❌ Failed to fetch data")
        return

    # Fetch 1h, 15m, 5m
    df_5m = engine.fetch_data('5m', limit)
    df_15m = engine.fetch_data('15m', limit)
    df_1h = engine.fetch_data('1h', limit)
    
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
    
    # Filter for TARGET DATE (Jan 8)
    target_data = df_5m[(df_5m.index >= start_date) & (df_5m.index < end_date)]
    
    print(f"📊 Analyzing {len(target_data)} candles from Jan 8...")
    
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
        
             
    if signals_found == 0:
        print("\n✅ RESULT: No trades identified for Jan 8.")
        print("   Max Confidence observed did not exceed 50%.")
    else:
        print(f"\n⚠️ RESULT: {signals_found} trades would have triggered on Jan 8.")
        print("   (Note: See logs above for exact times)")

if __name__ == "__main__":
    reconstruct_trades()
