#!/usr/bin/env python3
"""
🔥 MTF Scalper Feature Engineer
Merges multiple timeframes for high-frequency scalping with context awareness.
Base: 1m (execution), Context: 5m, 15m (confirmation)
"""

import os
import pandas as pd
import numpy as np

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

def merge_mtf_features(base_tf='1m', context_tfs=['5m', '15m']):
    """
    Merge multi-timeframe features onto base timeframe.
    Uses forward-fill to avoid lookahead bias.
    """
    
    print(f"🔥 Building MTF Scalper Features...")
    print(f"   Base: {base_tf} | Context: {', '.join(context_tfs)}")
    
    # Load base timeframe
    base_path = os.path.join(DATA_DIR, f'BTC_{base_tf}_features.csv')
    df_base = pd.read_csv(base_path)
    df_base['timestamp'] = pd.to_datetime(df_base['timestamp'])
    df_base.set_index('timestamp', inplace=True)
    
    print(f"   ✅ Loaded {base_tf}: {len(df_base)} bars")
    
    # Merge each context timeframe
    for ctx_tf in context_tfs:
        ctx_path = os.path.join(DATA_DIR, f'BTC_{ctx_tf}_features.csv')
        df_ctx = pd.read_csv(ctx_path)
        df_ctx['timestamp'] = pd.to_datetime(df_ctx['timestamp'])
        df_ctx.set_index('timestamp', inplace=True)
        
        # Select only indicator columns (not OHLCV)
        exclude = ['open', 'high', 'low', 'close', 'volume']
        ctx_cols = [c for c in df_ctx.columns if c not in exclude]
        
        # Rename columns to include timeframe suffix
        df_ctx_renamed = df_ctx[ctx_cols].copy()
        df_ctx_renamed.columns = [f"{c}_{ctx_tf}" for c in ctx_cols]
        
        # Merge using forward-fill (reindex to base timeframe)
        df_ctx_resampled = df_ctx_renamed.reindex(df_base.index, method='ffill')
        
        # Concatenate
        df_base = pd.concat([df_base, df_ctx_resampled], axis=1)
        
        print(f"   ✅ Merged {ctx_tf}: +{len(ctx_cols)} features")
    
    # Drop NaN rows
    df_base.dropna(inplace=True)
    
    # Save merged dataset
    out_path = os.path.join(DATA_DIR, f'BTC_MTF_scalper.csv')
    df_base.reset_index().to_csv(out_path, index=False)
    
    n_features = len([c for c in df_base.columns if c not in ['open', 'high', 'low', 'close', 'volume']])
    print(f"\n🎉 MTF Features Complete!")
    print(f"   Total Features: {n_features}")
    print(f"   Saved to: {out_path}")
    
    return df_base

if __name__ == '__main__':
    merge_mtf_features(base_tf='1m', context_tfs=['5m', '15m'])
