#!/usr/bin/env python3
"""
Generate features for all downloaded datasets
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'utils'))

import pandas as pd
import numpy as np
from feature_engineer import add_all_indicators

def generate_features_1h():
    """Generate features for 1H data (Winner Hunter)"""
    print("\n" + "="*70)
    print("1️⃣ GENERATING FEATURES FOR 1H DATA (Winner Hunter)")
    print("="*70)
    
    # Load data
    print("\n📊 Loading 1H data...")
    df = pd.read_csv('training/data/BTC_1h_10y.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    print(f"   Loaded {len(df):,} candles")
    
    # Generate features
    print("\n🔧 Generating features...")
    df = add_all_indicators(df)
    print(f"   Generated {len(df.columns)} columns")
    
    # Drop NaN rows (from indicator calculations)
    initial_len = len(df)
    df.dropna(inplace=True)
    print(f"   Dropped {initial_len - len(df):,} NaN rows")
    print(f"   Final dataset: {len(df):,} rows")
    
    # Save
    output_file = 'training/data/BTC_1h_features.csv'
    df.to_csv(output_file, index=False)
    print(f"\n✅ Saved to {output_file}")
    
    return df

def generate_features_5m():
    """Generate features for 5M data (MTF Scalper base)"""
    print("\n" + "="*70)
    print("2️⃣ GENERATING FEATURES FOR 5M DATA (MTF Scalper)")
    print("="*70)
    
    # Load data
    print("\n📊 Loading 5M data...")
    df = pd.read_csv('training/data/BTC_5m_10y.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    print(f"   Loaded {len(df):,} candles")
    
    # Generate features
    print("\n🔧 Generating features...")
    df = add_all_indicators(df)
    print(f"   Generated {len(df.columns)} columns")
    
    # Drop NaN rows
    initial_len = len(df)
    df.dropna(inplace=True)
    print(f"   Dropped {initial_len - len(df):,} NaN rows")
    print(f"   Final dataset: {len(df):,} rows")
    
    # Save
    output_file = 'training/data/BTC_5m_features.csv'
    df.to_csv(output_file, index=False)
    print(f"\n✅ Saved to {output_file}")
    
    return df

def generate_features_15m():
    """Generate features for 15M data (MTF Scalper context)"""
    print("\n" + "="*70)
    print("3️⃣ GENERATING FEATURES FOR 15M DATA (MTF Scalper)")
    print("="*70)
    
    # Load data
    print("\n📊 Loading 15M data...")
    df = pd.read_csv('training/data/BTC_15m_10y.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    print(f"   Loaded {len(df):,} candles")
    
    # Generate features
    print("\n🔧 Generating features...")
    df = add_all_indicators(df)
    print(f"   Generated {len(df.columns)} columns")
    
    # Drop NaN rows
    initial_len = len(df)
    df.dropna(inplace=True)
    print(f"   Dropped {initial_len - len(df):,} NaN rows")
    print(f"   Final dataset: {len(df):,} rows")
    
    # Save
    output_file = 'training/data/BTC_15m_features.csv'
    df.to_csv(output_file, index=False)
    print(f"\n✅ Saved to {output_file}")
    
    return df

def merge_mtf_features():
    """Merge multi-timeframe features for MTF Scalper"""
    print("\n" + "="*70)
    print("4️⃣ MERGING MULTI-TIMEFRAME FEATURES (5M Base)")
    print("="*70)
    
    # Load all feature datasets
    print("\n📊 Loading feature datasets...")
    df_5m = pd.read_csv('training/data/BTC_5m_features.csv')
    df_5m['timestamp'] = pd.to_datetime(df_5m['timestamp'])
    df_5m.set_index('timestamp', inplace=True)
    
    df_15m = pd.read_csv('training/data/BTC_15m_features.csv')
    df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])
    df_15m.set_index('timestamp', inplace=True)
    
    df_1h = pd.read_csv('training/data/BTC_1h_features.csv')
    df_1h['timestamp'] = pd.to_datetime(df_1h['timestamp'])
    df_1h.set_index('timestamp', inplace=True)
    
    # Merge context
    print("\n🔧 Merging context...")
    exclude = ['open', 'high', 'low', 'close', 'volume']
    
    # 15M context
    ctx_cols_15m = [c for c in df_15m.columns if c not in exclude]
    df_15m_ctx = df_15m[ctx_cols_15m].copy()
    df_15m_ctx.columns = [f"{c}_15m" for c in ctx_cols_15m]
    df_15m_resampled = df_15m_ctx.reindex(df_5m.index, method='ffill')
    
    # 1H context
    ctx_cols_1h = [c for c in df_1h.columns if c not in exclude]
    df_1h_ctx = df_1h[ctx_cols_1h].copy()
    df_1h_ctx.columns = [f"{c}_1h" for c in ctx_cols_1h]
    df_1h_resampled = df_1h_ctx.reindex(df_5m.index, method='ffill')
    
    # Combine
    df_mtf = pd.concat([df_5m, df_15m_resampled, df_1h_resampled], axis=1)
    df_mtf.dropna(inplace=True)
    
    # Reset index and save
    df_mtf.reset_index(inplace=True)
    output_file = 'training/data/BTC_5m_mtf_features.csv'
    df_mtf.to_csv(output_file, index=False)
    print(f"\n✅ Saved to {output_file}")
    
    return df_mtf

def merge_mtf_features_1h():
    """Merge multi-timeframe features (5m, 15m) into 1H data for Winner Hunter"""
    print("\n" + "="*70)
    print("5️⃣ MERGING MTF FEATURES FOR 1H DATA (Winner Hunter)")
    print("="*70)
    
    # Load feature datasets
    print("\n📊 Loading feature datasets...")
    df_1h = pd.read_csv('training/data/BTC_1h_features.csv')
    df_1h['timestamp'] = pd.to_datetime(df_1h['timestamp'])
    df_1h.set_index('timestamp', inplace=True)
    
    df_5m = pd.read_csv('training/data/BTC_5m_features.csv')
    df_5m['timestamp'] = pd.to_datetime(df_5m['timestamp'])
    df_5m.set_index('timestamp', inplace=True)
    
    df_15m = pd.read_csv('training/data/BTC_15m_features.csv')
    df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])
    df_15m.set_index('timestamp', inplace=True)
    
    # Merge lower timeframe context
    print("\n🔧 Merging lower timeframe context...")
    exclude = ['open', 'high', 'low', 'close', 'volume']
    
    # Aggregate 5M context
    ctx_cols_5m = [c for c in df_5m.columns if c not in exclude]
    df_5m_context = df_5m[ctx_cols_5m].copy()
    df_5m_context.columns = [f"{c}_5m" for c in ctx_cols_5m]
    df_5m_resampled = df_5m_context.reindex(df_1h.index, method='ffill')
    
    # Aggregate 15M context
    ctx_cols_15m = [c for c in df_15m.columns if c not in exclude]
    df_15m_context = df_15m[ctx_cols_15m].copy()
    df_15m_context.columns = [f"{c}_15m" for c in ctx_cols_15m]
    df_15m_resampled = df_15m_context.reindex(df_1h.index, method='ffill')
    
    # Combine
    df_1h_mtf = pd.concat([df_1h, df_5m_resampled, df_15m_resampled], axis=1)
    df_1h_mtf.dropna(inplace=True)
    
    # Reset index and save
    df_1h_mtf.reset_index(inplace=True)
    output_file = 'training/data/BTC_1h_mtf_features.csv'
    df_1h_mtf.to_csv(output_file, index=False)
    print(f"\n✅ Saved to {output_file}")
    
    return df_1h_mtf

def main():
    """Main execution"""
    print("="*70)
    print("🔧 FEATURE ENGINEERING PIPELINE")
    print("="*70)
    
    # Generate base features for each timeframe
    generate_features_1h()
    generate_features_5m()
    generate_features_15m()
    
    # Merge multi-timeframe features
    merge_mtf_features()
    merge_mtf_features_1h()
    
    print("\n" + "="*70)
    print("✅ FEATURE ENGINEERING SUMMARY")
    print("="*70)
    print("1H MTF Features: training/data/BTC_1h_mtf_features.csv")
    print("5M MTF Features: training/data/BTC_5m_mtf_features.csv")
    print("="*70)

if __name__ == '__main__':
    main()
