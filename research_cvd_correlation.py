
import pandas as pd
import sys
import os
import joblib

# Add root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.v5_feature_engineer import generate_v5_features

def research_cvd_correlation():
    print("🔎 Analyzing CVD Direction during High Volatility...")
    
    # 1. Load Data
    data_path = 'training/data/BTC_5m_2025_enriched.csv'
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Filter for Jan 2026
    df = df[df['timestamp'] >= '2026-01-01'].copy().reset_index(drop=True)
    
    # 2. Load Model
    model = joblib.load('model_engines/v6_grid/weights/vol_model.pkl')
    
    # 3. Features
    print("   🧠 Generating Features...")
    df_enriched = generate_v5_features(df)
    
    drop_cols_engine = ['timestamp', 'target', 'open', 'high', 'low', 'close', 
                 'taker_buy_base', 'taker_sell_base', 'future_high', 'future_low', 'future_range_pct',
                 'prob_low', 'prob_high']
    features = [c for c in df_enriched.columns if c not in drop_cols_engine]
    
    # Predict High Vol
    probs = model.predict_proba(df_enriched[features])
    df_enriched['prob_high_vol'] = probs[:, 2]
    
    # 4. Correlation Analysis
    threshold = 0.70
    high_vol_indices = df_enriched[df_enriched['prob_high_vol'] > threshold].index
    
    match_count = 0
    total_count = 0
    
    print("\n   📊 Correlation: CVD Trend vs Price Trend (Next 2h)")
    
    for idx in high_vol_indices:
        if idx >= len(df_enriched) - 24: continue
        
        row = df_enriched.iloc[idx]
        future = df_enriched.iloc[idx+1:idx+25] # Next 2 hours
        
        # Price Trend
        start_price = row['close']
        end_price = future.iloc[-1]['close']
        price_delta = end_price - start_price
        price_direction = 1 if price_delta > 0 else -1
        
        # CVD Trend (Is money flowing IN or OUT?)
        # We look at the CVD feature (cvd_1h) or just sum volume delta for the *event*?
        # Let's look at the CVD slope *leading up to* the event.
        cvd_val = row['cvd_1h'] 
        cvd_direction = 1 if cvd_val > 0 else -1
        
        # Or better: Global CVD Trend?
        
        if price_direction == cvd_direction:
            match_count += 1
            
        total_count += 1
        
    print(f"   Events: {total_count}")
    print(f"   CVD Matches Price Direction: {match_count} ({match_count/total_count:.1%})")
    
    # 5. What if we only trade if CVD is STRONG?
    print("\n   💪 Strong CVD Filter stats...")
    strong_match = 0
    strong_total = 0
    
    for idx in high_vol_indices:
        if idx >= len(df_enriched) - 24: continue
        row = df_enriched.iloc[idx]
        future = df_enriched.iloc[idx+1:idx+25]
        
        # Check 'Strong' CVD (e.g. > 100 or < -100) - arbitrary unit check
        # Actually cvd_1h is sum of volume delta.
        # Let's assess magnitude relative to average.
        
        cvd_abs = abs(row['cvd_1h'])
        # Simple check: Is it clearly non-zero?
        if cvd_abs < 50: continue # Noise
        
        start_price = row['close']
        end_price = future.iloc[-1]['close']
        price_direction = 1 if (end_price - start_price) > 0 else -1
        cvd_direction = 1 if row['cvd_1h'] > 0 else -1
        
        if price_direction == cvd_direction:
            strong_match += 1
        strong_total += 1
        
    if strong_total > 0:
        print(f"   Strong CVD Events: {strong_total}")
        print(f"   Accuracy: {strong_match/strong_total:.1%}")

if __name__ == "__main__":
    research_cvd_correlation()
