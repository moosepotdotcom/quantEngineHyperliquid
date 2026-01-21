#!/usr/bin/env python3
"""
Proper MTF Feature Calculator
Replicates training's feature generation process
"""

import sys
sys.path.insert(0, '/Users/alifiyaa/Downloads/quantEngineHyperliquid/utils')

import pandas as pd
import numpy as np
from feature_engineer import add_all_indicators

def calculate_mtf_features_proper(df_5m, df_15m, df_1h):
    """
    Calculate 231 MTF features exactly like training data
    
    Args:
        df_5m: 5-minute OHLCV data
        df_15m: 15-minute OHLCV data  
        df_1h: 1-hour OHLCV data
        
    Returns:
        DataFrame with 231 MTF features
    """
    
    print("🔧 Calculating MTF features (proper method)...")
    
    # Calculate indicators for each timeframe
    print("   Calculating 5m indicators...")
    df_5m_ind = add_all_indicators(df_5m.copy())
    if 'timestamp' in df_5m_ind.columns:
        df_5m_ind.set_index('timestamp', inplace=True)
    
    print("   Calculating 15m indicators...")
    df_15m_ind = add_all_indicators(df_15m.copy())
    if 'timestamp' in df_15m_ind.columns:
        df_15m_ind.set_index('timestamp', inplace=True)
    
    print("   Calculating 1h indicators...")
    df_1h_ind = add_all_indicators(df_1h.copy())
    if 'timestamp' in df_1h_ind.columns:
        df_1h_ind.set_index('timestamp', inplace=True)
    
    # Get feature columns (exclude OHLCV)
    exclude = ['open', 'high', 'low', 'close', 'volume']
    
    # 15m context - add suffix and resample to 5m
    print("   Merging 15m context...")
    ctx_cols_15m = [c for c in df_15m_ind.columns if c not in exclude]
    df_15m_ctx = df_15m_ind[ctx_cols_15m].copy()
    df_15m_ctx.columns = [f"{c}_15m" for c in ctx_cols_15m]
    df_15m_resampled = df_15m_ctx.reindex(df_5m_ind.index, method='ffill')
    
    # 1h context - add suffix and resample to 5m
    print("   Merging 1h context...")
    ctx_cols_1h = [c for c in df_1h_ind.columns if c not in exclude]
    df_1h_ctx = df_1h_ind[ctx_cols_1h].copy()
    df_1h_ctx.columns = [f"{c}_1h" for c in ctx_cols_1h]
    df_1h_resampled = df_1h_ctx.reindex(df_5m_ind.index, method='ffill')
    
    # Combine all timeframes
    print("   Combining timeframes...")
    df_mtf = pd.concat([df_5m_ind, df_15m_resampled, df_1h_resampled], axis=1)
    
    # Drop rows with NaN (from indicator calculations)
    df_mtf.dropna(inplace=True)
    
    # Filter to only keep features that were in training data
    # Exclude these 6 advanced features per timeframe (18 total):
    exclude_features = [
        'hurst', 'atr_ratio', 'rsi_slope', 'price_slope', 
        'wick_ratio_upper', 'wick_ratio_lower'
    ]
    
    # Build full list with suffixes
    exclude_all = exclude_features.copy()
    for feat in exclude_features:
        exclude_all.append(f'{feat}_15m')
        exclude_all.append(f'{feat}_1h')
    
    # Drop excluded features
    df_mtf = df_mtf.drop(columns=[c for c in exclude_all if c in df_mtf.columns], errors='ignore')
    
    # Get feature count
    feature_cols = [c for c in df_mtf.columns if c not in exclude]
    
    print(f"✅ MTF features: {len(feature_cols)} features, {len(df_mtf)} candles")
    
    return df_mtf

if __name__ == '__main__':
    # Test the function
    import sys
    sys.path.insert(0, '/Users/alifiyaa/Downloads/quantEngineHyperliquid/EXPORT')
    from quant_engine import TradingEngine
    
    engine = TradingEngine()
    
    print("\n📡 Fetching test data...")
    df_5m = engine.fetch_data('5m', 500)
    df_15m = engine.fetch_data('15m', 200)
    df_1h = engine.fetch_data('1h', 100)
    
    print(f"✅ Fetched: 5m={len(df_5m)}, 15m={len(df_15m)}, 1h={len(df_1h)}")
    
    # Calculate MTF features
    df_mtf = calculate_mtf_features_proper(df_5m, df_15m, df_1h)
    
    # Verify feature count
    exclude = ['open', 'high', 'low', 'close', 'volume']
    features = [c for c in df_mtf.columns if c not in exclude]
    
    print(f"\n📊 Verification:")
    print(f"   Total features: {len(features)}")
    print(f"   Expected: 231")
    print(f"   Match: {'✅' if len(features) == 231 else '❌'}")
    
    # Check for zeros
    zero_count = 0
    for f in features:
        if (df_mtf[f] == 0).all():
            zero_count += 1
    
    print(f"   Zero features: {zero_count}")
    print(f"   Valid: {'✅' if zero_count == 0 else '❌'}")
