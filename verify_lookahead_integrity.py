
import pandas as pd
import numpy as np

# Feature Logic (Copied exactly from bundle)
PERIOD = 21

def add_features(df):
    df = df.copy()
    high = df['high'].rolling(PERIOD).max()
    low = df['low'].rolling(PERIOD).min()
    denom = (high - low).replace(0, np.nan)
    df['williams_r'] = -100 * (high - df['close']) / denom
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi_14'] = 100 - (100 / (1 + rs))
    
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift(1)).abs()
    tr3 = (df['low'] - df['close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr_14'] = tr.rolling(14).mean()
    
    df['vol_change'] = df['volume'].pct_change()
    
    ema = df['close'].ewm(span=200, adjust=False).mean()
    df['ema_200_dist'] = (df['close'] - ema) / ema
    
    return df

def run_lookahead_check():
    print("🕵️ STARTING LOOKAHEAD BIAS CHECK...")
    
    # Create synthetic data
    dates = pd.date_range(start='2024-01-01', periods=500, freq='5min')
    df = pd.DataFrame({
        'timestamp': dates,
        'open': np.random.randn(500).cumsum() + 100,
        'high': np.random.randn(500).cumsum() + 105,
        'low': np.random.randn(500).cumsum() + 95,
        'close': np.random.randn(500).cumsum() + 100,
        'volume': np.random.randint(100, 1000, 500)
    })
    
    # scenario 1: Calculate features on full dataset
    df_full = add_features(df)
    
    # scenario 2: Drop the last row, calculate features
    df_dropped = df.iloc[:-1].copy()
    df_dropped_feats = add_features(df_dropped)
    
    print("   Comparing Feature Values at index N-1...")
    
    # Compare the last common row (index 498)
    idx_check = 498
    
    cols_to_check = ['williams_r', 'rsi_14', 'atr_14', 'vol_change', 'ema_200_dist']
    
    all_passed = True
    
    for col in cols_to_check:
        val_full = df_full.iloc[idx_check][col]
        val_dropped = df_dropped_feats.iloc[idx_check][col]
        
        # Check equality (with float tolerance)
        if np.isnan(val_full) and np.isnan(val_dropped):
             match = True
        else:
             match = np.isclose(val_full, val_dropped, rtol=1e-09)
        
        if match:
            print(f"   ✅ {col}: Pass ({val_full:.4f} == {val_dropped:.4f})")
        else:
            print(f"   ❌ {col}: FAIL! ({val_full:.4f} != {val_dropped:.4f})")
            all_passed = False
            
    if all_passed:
        print("\n✅ PASSED: No Lookahead Bias detected.")
        print("   Removing future data did NOT change past feature values.")
    else:
        print("\n❌ FAILED: Lookahead Bias detected! Future data affected past calculations.")

if __name__ == "__main__":
    run_lookahead_check()
