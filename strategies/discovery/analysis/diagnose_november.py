
import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION'))
sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION/utils'))

from quant_engine import TradingEngine

def diagnose_november():
    print("🕵️‍♂️ DEEP DIVE: NOVEMBER NO-TRADE DIAGNOSIS", flush=True)
    print("="*60, flush=True)
    
    csv_path = 'training/data/BTC_5m_mtf_features.csv'
    try:
        # Load efficiently
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"❌ Read Error: {e}", flush=True)
        return

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    df.sort_index(inplace=True)
    
    print(f"Data Loaded: {len(df)} rows. Range: {df.index.min()} - {df.index.max()}", flush=True)

    # Force Float for Price Cols (Critical fix)
    cols = ['open', 'high', 'low', 'close', 'volume']
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    
    # Filter November
    start = pd.Timestamp("2025-11-01 00:00:00")
    end = pd.Timestamp("2025-11-30 23:59:59")
    df = df[(df.index >= start) & (df.index <= end)]
    
    print(f"November Data: {len(df)} rows.", flush=True)
    if len(df) == 0: return

    print(f"ATR Min: {df['atr_14'].min():.2f}", flush=True)
    print(f"ATR Max: {df['atr_14'].max():.2f}", flush=True)
    print(f"ATR Mean: {df['atr_14'].mean():.2f}")
    
    # Count "Safe Windows"
    limit = 52.75
    safe_zones = df[df['atr_14'] < limit]
    print(f"\n✅ Safe Windows (ATR < {limit}): {len(safe_zones)} candles ({len(safe_zones)/len(df):.1%})")
    
    if len(safe_zones) == 0:
        print("❌ NO SAFE WINDOWS EXISTED. Case Closed.")
        return

    print("\n🔍 Checking Model Confidence during Safe Windows...")
    engine = TradingEngine()
    
    # Check predictions ONLY for safe zones to save time/print relevant info
    high_conf_signals = 0
    
    # We also want to know if models were active AT ALL (even in high volatility)
    # So let's check a random sample of high volatility too to ensure models work
    
    print(f"{'TIME':<20} | {'ATR':<6} | {'L_CONF':<6} | {'S_CONF':<6} | {'NOTE'}")
    print("-" * 65)
    
    # Iterate all data to find ANY signals
    for idx, row in df.iterrows():
        # Quick predict (skipping full feature re-engineering since columns exist)
        # We need to drop non-feature columns
        exclude = ['open', 'high', 'low', 'close', 'volume', 'hurst', 'timestamp']
        # The dataframe index is timestamp, so standard drop works features are remaining cols
        
        # We need hurst for drop list but it might not be in df cols if pre-calc
        # Actually in verify script we dropped 'hurst' explicitly.
        
        row_vals = row.drop(labels=['open', 'high', 'low', 'close', 'volume', 'hurst'], errors='ignore')
        
        # IMPORTANT: Model expects specific column order/count (239).
        # We must truncate if needed.
        X = row_vals.values.reshape(1, -1)
        X = np.nan_to_num(X, nan=0.0)
        if X.shape[1] > 239: 
            X = X[:, :239]
        elif X.shape[1] < 239:
            # Pad with zeros if features are missing
            X = np.pad(X, ((0,0), (0, 239 - X.shape[1])), 'constant')
        
        p1 = engine.mtf_xgb.predict_proba(X)[0]
        p2 = engine.mtf_lgb.predict(X)[0]
        p3 = engine.mtf_cat.predict_proba(X)[0]
        
        avg_prob = (p1 + p2 + p3) / 3
        conf_long, conf_short = avg_prob[1], avg_prob[2]
        
        atr = row['atr_14']
        is_safe = atr < limit
        is_signal = conf_long > 0.45 or conf_short > 0.45
        
        if is_signal:
            status = "BLOCKED_ATR" if not is_safe else "TRADE_MISSED?"
            print(f"{str(idx):<20} | {atr:<6.1f} | {conf_long:<6.2f} | {conf_short:<6.2f} | {status}")
        
    print("="*60)
    print("Diagnosis Complete.")

if __name__ == "__main__":
    diagnose_november()
