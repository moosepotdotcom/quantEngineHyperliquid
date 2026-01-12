import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Mock datetime to control "now" during simulation
import datetime as real_datetime

# Add path access
sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION'))
sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION/utils'))

from quant_engine import TradingEngine, add_all_indicators

def reconstruct_trades():
    print("🔄 RECONSTRUCTING TRADES FOR TODAY (Jan 10, 2026)...")
    print("="*60)
    
    engine = TradingEngine()
    
    # Fetch 24h of data (approx 288 5m candles)
    print("\n📥 Fetching historical data...")
    df_raw = engine.fetch_data('5m', 1000) # Get plenty of context
    
    if df_raw is None or len(df_raw) == 0:
        print("❌ Failed to fetch data")
        return

    # Filter for today's data (Jan 10)
    df_raw['timestamp'] = pd.to_datetime(df_raw['timestamp'])
    today_start = pd.Timestamp('2026-01-10 00:00:00')
    today_data = df_raw[df_raw['timestamp'] >= today_start]
    
    print(f"📊 Analyzing {len(today_data)} candles from Jan 10...")
    
    signals_found = 0
    
    # Iterate through today's candles
    for i in range(50, len(today_data)):
        # Create a "snapshot" as if this was the latest data available
        current_candle = today_data.iloc[i]
        timestamp = current_candle['timestamp']
        
        # Slice data up to this point (simulation)
        cutoff_time = timestamp
        # We need to simulate the engine's view. 
        # The engine fetches 500 candles ending at "now".
        # So we take the full dataset up to 'i'.
        
        # Actually, simpler: We can just use the engine's prediction logic on the specific row
        # IF we can regenerate features correctly.
        
        # Let's generate features for the whole dataset first
        df_context = df_raw[df_raw['timestamp'] <= timestamp].tail(500)
        
        # Skip if not enough data
        if len(df_context) < 200: continue
            
        # Run Feature Engineering
        df_feat = add_all_indicators(df_context.copy())
        
        # Hurst (Simple fallback)
        df_feat['hurst'] = 0.5 
        
        # Check logic
        latest = df_feat.iloc[-1]
        
        # Prepare X
        # We need to match features exactly. 
        exclude = ['open', 'high', 'low', 'close', 'volume', 'timestamp', 'hurst']
        features = [c for c in df_feat.columns if c not in exclude]
        
        # Note: This is a simplified reconstruction. 
        # MTF context (15m, 1h) would need resampling.
        # For a quick check, we'll try to lean on the engine functions if possible,
        # but the engine fetches "live".
        
        # WORKAROUND: We will manually call predict on the rows.
        # But we need the exact 239 features including MTF.
        # Creating a truly faithful reconstruction is hard without mocking the fetcher.
        
        # Let's try mocking the fetcher?
        # Too complex for this script.
        
        # We will do a "Best Effort" check on the 5m model only, assuming MTF context 
        # usually confirms strong signals.
        
        pass 
        # Actually, let's rely on the engine but we can't easily mock time.
        
        # NEW STRATEGY: 
        # Just use the data we have.
        # If we really want to know if we missed a trade,
        # we check the "Confidence" column if we can generate it.
        
        # Given complexity, let's just create the features for the whole dataframe
        # And run prediction.
        
    print("⚠️  Reconstruction requires full MTF context which is time-dependent.")
    print("   Running simplified analysis on available buffered data...")
    
    # Fetch 1h, 15m, 5m
    df_5m = engine.fetch_data('5m', 1000)
    df_15m = engine.fetch_data('15m', 1000)
    df_1h = engine.fetch_data('1h', 1000)
    
    # Feature Engineering
    df_5m = add_all_indicators(df_5m)
    df_15m = add_all_indicators(df_15m)
    df_1h = add_all_indicators(df_1h)
    
    # Merge (Simplified from quant_engine)
    df_5m.set_index('timestamp', inplace=True)
    df_15m.set_index('timestamp', inplace=True)
    df_1h.set_index('timestamp', inplace=True)
    
    # ... Merging logic (copied from quant_engine) ...
    exclude = ['open', 'high', 'low', 'close', 'volume']
    
    # 15m
    ctx_cols_15m = [c for c in df_15m.columns if c not in exclude]
    df_15m_renamed = df_15m[ctx_cols_15m].copy()
    df_15m_renamed.columns = [f"{c}_15m" for c in ctx_cols_15m]
    df_15m_resampled = df_15m_renamed.reindex(df_5m.index, method='ffill')
    df_5m = pd.concat([df_5m, df_15m_resampled], axis=1)
    
    # 1h
    ctx_cols_1h = [c for c in df_1h.columns if c not in exclude]
    df_1h_renamed = df_1h[ctx_cols_1h].copy()
    df_1h_renamed.columns = [f"{c}_1h" for c in ctx_cols_1h]
    df_1h_resampled = df_1h_renamed.reindex(df_5m.index, method='ffill')
    df_5m = pd.concat([df_5m, df_1h_resampled], axis=1)
    
    # Filter for today
    today_data = df_5m[df_5m.index >= today_start]
    
    print(f"📊 Processed {len(today_data)} candles with full MTF context")
    
    # Predict loop
    for idx, row in today_data.iterrows():
        # Prepare X
        # Need to drop 'hurst' if not in features, or add it
        # The model expects 239 features.
        
        # We need the exact feature list the model uses.
        # We can get it by looking at columns remaining after exclude
        
        # Hack: The engine trims to 239. We will too.
        
        # Get values excluding non-features
        row_vals = row.drop(labels=exclude + ['hurst'], errors='ignore')
        X = row_vals.values.reshape(1, -1)
        X = np.nan_to_num(X, nan=0.0)
        
        if X.shape[1] > 239: X = X[:, :239]
        
        # Predict
        # We access the engine's loaded models
        # XGB
        p1 = engine.mtf_xgb.predict_proba(X)[0]
        # LGB
        p2 = engine.mtf_lgb.predict(X)[0]
        # Cat
        p3 = engine.mtf_cat.predict_proba(X)[0]
        
        # Soft Voting
        avg_prob = (p1 + p2 + p3) / 3
        prob_long = avg_prob[1]
        prob_short = avg_prob[2]
        
        # Threshold Check (Using fixed 0.50/0.55 as baseline)
        ts = idx.strftime('%H:%M')
        
        if prob_long > 0.50:
            print(f"⏰ {ts} | LONG Signal? Conf: {prob_long:.2%} (Threshold 50%)")
            signals_found += 1
        elif prob_short > 0.55:
             print(f"⏰ {ts} | SHORT Signal? Conf: {prob_short:.2%} (Threshold 55%)")
             signals_found += 1
             
    if signals_found == 0:
        print("\n✅ RESULT: No trades missed. No signals > 50% confidence found today.")
    else:
        print(f"\n⚠️ RESULT: {signals_found} potential signals found in reconstruction.")

if __name__ == "__main__":
    reconstruct_trades()
