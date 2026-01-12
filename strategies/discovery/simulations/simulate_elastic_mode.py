
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Add path access
sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION'))
sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION/utils'))

from quant_engine import TradingEngine, add_all_indicators, ElasticThresholdManager

def reconstruct_period(target_date_str):
    target_date = pd.Timestamp(target_date_str)
    print(f"\n🔄 RECONSTRUCTING TRADES FOR {target_date.date()} (With Elastic Logic)...")
    print("="*60)
    
    engine = TradingEngine()
    
    # Fetch ample context (2000 candles covers approx 1 week of 5m data)
    print("📥 Fetching historical data (1 Week Context)...")
    df_raw = engine.fetch_data('5m', 2000) 
    
    if df_raw is None or len(df_raw) == 0:
        print("❌ Failed to fetch data")
        return

    # Base Feature Engineering
    df_raw = add_all_indicators(df_raw)
    df_raw['hurst'] = 0.5 # Default for simulation
    df_raw.set_index('timestamp', inplace=True)
    
    # Define Simulation Window (Target Day)
    start_sim = target_date
    end_sim = target_date + pd.Timedelta(hours=24)
    
    # Initialize Elastic Manager
    # Scenario: The bot was running Continuously.
    # So 'last_trade_time' should be set to Jan 7, 07:40 (The last known trade)
    last_known_trade = pd.Timestamp("2026-01-07 07:40:00")
    
    elastic = ElasticThresholdManager(
        "MTF_Sim", 
        surgical_threshold_long=0.50, 
        surgical_threshold_short=0.55, 
        floor_threshold=0.45
    )
    elastic.last_trade_time = last_known_trade
    
    print(f"⚙️  Initialized Elastic Manager.")
    print(f"   Last Trade: {last_known_trade}")
    print(f"   Start Mode: {'ELASTIC' if (start_sim - last_known_trade).total_seconds() > 21600 else 'SURGICAL'}")
    
    # Prepare MTF Context (Expensive but required for accuracy)
    print("📊 Merging MTF Context (15m + 1H)...")
    df_15m = engine.fetch_data('15m', 2000)
    df_1h = engine.fetch_data('1h', 2000)
    
    df_15m = add_all_indicators(df_15m)
    df_1h = add_all_indicators(df_1h)
    df_15m.set_index('timestamp', inplace=True)
    df_1h.set_index('timestamp', inplace=True)
    
    exclude = ['open', 'high', 'low', 'close', 'volume', 'hurst']
    
    # Merge 15m
    ctx_cols_15m = [c for c in df_15m.columns if c not in exclude]
    df_15m_renamed = df_15m[ctx_cols_15m].copy()
    df_15m_renamed.columns = [f"{c}_15m" for c in ctx_cols_15m]
    df_15m_resampled = df_15m_renamed.reindex(df_raw.index, method='ffill')
    df_MTF = pd.concat([df_raw, df_15m_resampled], axis=1)
    
    # Merge 1h
    ctx_cols_1h = [c for c in df_1h.columns if c not in exclude]
    df_1h_renamed = df_1h[ctx_cols_1h].copy()
    df_1h_renamed.columns = [f"{c}_1h" for c in ctx_cols_1h]
    df_1h_resampled = df_1h_renamed.reindex(df_raw.index, method='ffill')
    df_MTF = pd.concat([df_MTF, df_1h_resampled], axis=1)
    
    # Slice for Target Day
    day_data = df_MTF[(df_MTF.index >= start_sim) & (df_MTF.index < end_sim)]
    print(f"✅ Data Prepared. Simulating {len(day_data)} candles...")
    
    signals_found = 0
    
    # SIMULATION LOOP
    for idx, row in day_data.iterrows():
        # 1. Update Elastic Logic based on ELAPSED TIME
        # We need to manually update the 'mode' because the class relies on datetime.now()
        # So we have to Monkey-Patch or specific logic.
        # Actually, let's just calculate logic here:
        
        hours_since_last = (idx - elastic.last_trade_time).total_seconds() / 3600
        is_elastic = hours_since_last >= 6
        
        active_long = elastic.floor_threshold if is_elastic else elastic.surgical_threshold_long
        active_short = elastic.floor_threshold if is_elastic else elastic.surgical_threshold_short
        
        # 2. Get Prediction
        row_vals = row.drop(labels=exclude + ['hurst'], errors='ignore')
        X = row_vals.values.reshape(1, -1)
        X = np.nan_to_num(X, nan=0.0)
        if X.shape[1] > 239: X = X[:, :239]
        
        p1 = engine.mtf_xgb.predict_proba(X)[0]
        p2 = engine.mtf_lgb.predict(X)[0]
        p3 = engine.mtf_cat.predict_proba(X)[0]
        avg_prob = (p1 + p2 + p3) / 3
        
        prob_long = avg_prob[1]
        prob_short = avg_prob[2]
        
        # 3. Check Signal
        ts = idx.strftime('%H:%M')
        mode_str = "ELASTIC" if is_elastic else "SURGICAL"
        
        if prob_long >= active_long:
             print(f"⏰ {ts} | 🟢 LONG TRIGGER! Conf {prob_long:.2%} >= {active_long:.2%} ({mode_str})")
             signals_found += 1
             elastic.last_trade_time = idx # Update trade time
             
        elif prob_short >= active_short:
             print(f"⏰ {ts} | 🔴 SHORT TRIGGER! Conf {prob_short:.2%} >= {active_short:.2%} ({mode_str})")
             signals_found += 1
             elastic.last_trade_time = idx # Update trade time

    if signals_found == 0:
        print(f"\n✅ RESULT: Zero trades found for {target_date.date()}.")
        print("   Market never crossed the active threshold.")
    else:
        print(f"\n⚠️ RESULT: {signals_found} trades found.")

if __name__ == "__main__":
    reconstruct_period("2026-01-08")
    reconstruct_period("2026-01-09")
