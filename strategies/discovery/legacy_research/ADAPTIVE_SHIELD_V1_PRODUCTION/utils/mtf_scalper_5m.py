#!/usr/bin/env python3
"""
🔥 MTF Scalper Feature Engineer (5m Base)
Merges 5m (base) with 15m, 1h (context) for high-frequency scalping.
"""

import os
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

def merge_mtf_scalper_5m():
    """Merge 5m base with 15m/1h context"""
    
    print("🔥 Building MTF Scalper Features (5m base)...")
    
    # Load base
    df_base = pd.read_csv(os.path.join(DATA_DIR, 'BTC_5m_features.csv'))
    df_base['timestamp'] = pd.to_datetime(df_base['timestamp'])
    df_base.set_index('timestamp', inplace=True)
    print(f"   ✅ Loaded 5m: {len(df_base)} bars")
    
    # Merge 15m context
    df_15m = pd.read_csv(os.path.join(DATA_DIR, 'BTC_15m_features.csv'))
    df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])
    df_15m.set_index('timestamp', inplace=True)
    
    exclude = ['open', 'high', 'low', 'close', 'volume']
    ctx_cols_15m = [c for c in df_15m.columns if c not in exclude]
    df_15m_renamed = df_15m[ctx_cols_15m].copy()
    df_15m_renamed.columns = [f"{c}_15m" for c in ctx_cols_15m]
    df_15m_resampled = df_15m_renamed.reindex(df_base.index, method='ffill')
    df_base = pd.concat([df_base, df_15m_resampled], axis=1)
    print(f"   ✅ Merged 15m: +{len(ctx_cols_15m)} features")
    
    # Merge 1h context
    df_1h = pd.read_csv(os.path.join(DATA_DIR, 'BTC_1h_features.csv'))
    df_1h['timestamp'] = pd.to_datetime(df_1h['timestamp'])
    df_1h.set_index('timestamp', inplace=True)
    
    ctx_cols_1h = [c for c in df_1h.columns if c not in exclude]
    df_1h_renamed = df_1h[ctx_cols_1h].copy()
    df_1h_renamed.columns = [f"{c}_1h" for c in ctx_cols_1h]
    df_1h_resampled = df_1h_renamed.reindex(df_base.index, method='ffill')
    df_base = pd.concat([df_base, df_1h_resampled], axis=1)
    print(f"   ✅ Merged 1h: +{len(ctx_cols_1h)} features")
    
    # Save
    df_base.dropna(inplace=True)
    out_path = os.path.join(DATA_DIR, 'BTC_MTF_scalper_5m.csv')
    df_base.reset_index().to_csv(out_path, index=False)
    
    n_features = len([c for c in df_base.columns if c not in ['open', 'high', 'low', 'close', 'volume']])
    print(f"\n🎉 MTF Features Complete!")
    print(f"   Total Features: {n_features}")
    print(f"   Saved to: {out_path}")

if __name__ == '__main__':
    merge_mtf_scalper_5m()
