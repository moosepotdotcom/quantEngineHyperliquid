import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime
import json

# Add path to access existing utils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quant_engine import TradingEngine, add_all_indicators, MTF_FEATURE_LIST
from utils.advanced_features import generate_advanced_features

def run_fast_signal_generation():
    print("="*60)
    print("🚀 GENERATING SIGNALS DATABASE (10 Months)")
    print("="*60)
    
    # Initialize Engine
    engine = TradingEngine()
    
    # Load Data
    print("🔄 Loading MASTER_TRAINING_DATA.csv...")
    df = pd.read_csv("MASTER_TRAINING_DATA.csv")
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Limit to reasonable size for speed if needed, but we want all 11 months
    # df = df.tail(50000) 
    
    print(f"   📊 Processing {len(df)} candles...")
    
    # Feature Engineering
    df = add_all_indicators(df)
    df = generate_advanced_features(df) # Add our new Alpha features too
    
    # Resample for MTF (Simplified for speed - assume strict alignment)
    # real production engine does proper resampling. Here we simulate it.
    # For speed, we will just use the 5m data and "fake" the MTF by using rolling windows
    # which is close enough for finding TP/SL optima.
    # ACTUALLY: The engine needs specific MTF columns. We must generate them or the model fails.
    
    print("🔧 Generating MTF Context...")
    df.set_index('timestamp', inplace=True)
    
    # Resample 15m
    df15 = df.resample('15T').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
    df15 = add_all_indicators(df15)
    
    # Resample 1h
    df1h = df.resample('1H').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
    df1h = add_all_indicators(df1h)
    
    # Merge back to 5m
    exclude = ['open', 'high', 'low', 'close', 'volume']
    
    ctx15 = [c for c in df15.columns if c not in exclude]
    df15_renamed = df15[ctx15].rename(columns={c: f"{c}_15m" for c in ctx15})
    df = pd.concat([df, df15_renamed.reindex(df.index, method='ffill')], axis=1)
    
    ctx1h = [c for c in df1h.columns if c not in exclude]
    df1h_renamed = df1h[ctx1h].rename(columns={c: f"{c}_1h" for c in ctx1h})
    df = pd.concat([df, df1h_renamed.reindex(df.index, method='ffill')], axis=1)
    
    df.dropna(inplace=True)
    print(f"✅ Data Ready: {len(df)} rows")
    
    signals = []
    
    print("⚡ Running Inference...")
    # Pre-calculate features matrix for batch inference? 
    # XGBoost is fast with batch. 
    
    # Extract features
    try:
        X_df = pd.DataFrame()
        for feature in MTF_FEATURE_LIST:
            X_df[feature] = df[feature]
            
        X = X_df.values
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        
        # Get Probabilities in Batch (Much faster)
        # Note: engine.get_ensemble_proba expects single sample or batch?
        # XGBoost supports batch.
        
        # We need to access the underlying models directly to do batch
        print("   🤖 Batch Predicting MTF Scalper...")
        
        # MTF Models
        p1 = engine.mtf_xgb.predict_proba(X)
        p2 = engine.mtf_lgb.predict(X)
        p3 = engine.mtf_cat.predict_proba(X)
        
        # Average
        # p1 shape (N, 3), p2 shape (N, 3), p3 shape (N, 3)
        ensemble_proba = (p1 + p2 + p3) / 3.0
        
        # Iterate and store potential signals
        print("   💾 storing signals...")
        
        # Thresholds to consider "Potential"
        # We store anything > 0.40 so we can optimize the threshold later
        
        long_candidates = np.where(ensemble_proba[:, 1] > 0.40)[0]
        short_candidates = np.where(ensemble_proba[:, 2] > 0.40)[0]
        
        print(f"   Found {len(long_candidates)} Long candidates")
        print(f"   Found {len(short_candidates)} Short candidates")
        
        # Helper to record outcome
        # We look ahead 1000 candles (approx 3.5 days) max
        
        def record_signal(idx, direction, confidence):
            entry_price = df['close'].iloc[idx]
            entry_time = df.index[idx]
            atr = df['atr_14'].iloc[idx]
            
            # Future data slice
            future = df.iloc[idx+1 : idx+145] # 12 hours max
            
            if len(future) < 10: return
            
            # Record max excursion
            if direction == 'LONG':
                max_profit = (future['high'].max() - entry_price) / entry_price
                max_loss = (entry_price - future['low'].min()) / entry_price
            else:
                max_profit = (entry_price - future['low'].min()) / entry_price
                max_loss = (future['high'].max() - entry_price) / entry_price
                
            signals.append({
                'timestamp': entry_time,
                'direction': direction,
                'confidence': confidence,
                'price': entry_price,
                'atr': atr,
                'max_profit': max_profit,
                'max_loss': max_loss,
                # Store extra features for ML filtering later
                'rsi': df['rsi_14'].iloc[idx],
                'vol_regime': df['vol_regime'].iloc[idx] if 'vol_regime' in df else 0,
                'hour': entry_time.hour
            })
            
        for idx in long_candidates:
            record_signal(idx, 'LONG', ensemble_proba[idx, 1])
            
        for idx in short_candidates:
            record_signal(idx, 'SHORT', ensemble_proba[idx, 2])
            
        # Save to CSV
        res_df = pd.DataFrame(signals)
        res_df.to_csv("SIGNALS_DB.csv", index=False)
        print(f"✅ Saved {len(res_df)} potential signals to SIGNALS_DB.csv")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_fast_signal_generation()
