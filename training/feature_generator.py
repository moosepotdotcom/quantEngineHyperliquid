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
    print(f"   Rows: {len(df):,}")
    print(f"   Columns: {len(df.columns)}")
    
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
    print(f"   Rows: {len(df):,}")
    print(f"   Columns: {len(df.columns)}")
    
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
    print(f"   Rows: {len(df):,}")
    print(f"   Columns: {len(df.columns)}")
    
    return df

def merge_mtf_features():
    """Merge multi-timeframe features for MTF Scalper"""
    print("\n" + "="*70)
    print("4️⃣ MERGING MULTI-TIMEFRAME FEATURES")
    print("="*70)
    
    # Load all feature datasets
    print("\n📊 Loading feature datasets...")
    df_5m = pd.read_csv('training/data/BTC_5m_features.csv')
    df_5m['timestamp'] = pd.to_datetime(df_5m['timestamp'])
    df_5m.set_index('timestamp', inplace=True)
    print(f"   5M:  {len(df_5m):,} rows, {len(df_5m.columns)} columns")
    
    df_15m = pd.read_csv('training/data/BTC_15m_features.csv')
    df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])
    df_15m.set_index('timestamp', inplace=True)
    print(f"   15M: {len(df_15m):,} rows, {len(df_15m.columns)} columns")
    
    # Merge 15M context
    print("\n🔧 Merging 15M context...")
    exclude = ['open', 'high', 'low', 'close', 'volume']
    ctx_cols_15m = [c for c in df_15m.columns if c not in exclude]
    df_15m_renamed = df_15m[ctx_cols_15m].copy()
    df_15m_renamed.columns = [f"{c}_15m" for c in ctx_cols_15m]
    df_15m_resampled = df_15m_renamed.reindex(df_5m.index, method='ffill')
    df_mtf = pd.concat([df_5m, df_15m_resampled], axis=1)
    print(f"   After 15M merge: {len(df_mtf.columns)} columns")
    
    # Load 1H data for context (using same as Winner Hunter)
    df_1h = pd.read_csv('training/data/BTC_1h_features.csv')
    df_1h['timestamp'] = pd.to_datetime(df_1h['timestamp'])
    df_1h.set_index('timestamp', inplace=True)
    print(f"   1H:  {len(df_1h):,} rows, {len(df_1h.columns)} columns")
    
    # Merge 1H context
    print("\n🔧 Merging 1H context...")
    ctx_cols_1h = [c for c in df_1h.columns if c not in exclude]
    df_1h_renamed = df_1h[ctx_cols_1h].copy()
    df_1h_renamed.columns = [f"{c}_1h" for c in ctx_cols_1h]
    df_1h_resampled = df_1h_renamed.reindex(df_mtf.index, method='ffill')
    df_mtf = pd.concat([df_mtf, df_1h_resampled], axis=1)
    print(f"   After 1H merge: {len(df_mtf.columns)} columns (MTF complete)")
    
    # Drop NaN rows
    initial_len = len(df_mtf)
    df_mtf.dropna(inplace=True)
    print(f"\n   Dropped {initial_len - len(df_mtf):,} NaN rows")
    print(f"   Final MTF dataset: {len(df_mtf):,} rows")
    
    # Reset index
    df_mtf.reset_index(inplace=True)
    
    # Save
    output_file = 'training/data/BTC_5m_mtf_features.csv'
    df_mtf.to_csv(output_file, index=False)
    print(f"\n✅ Saved to {output_file}")
    print(f"   Rows: {len(df_mtf):,}")
    print(f"   Columns: {len(df_mtf.columns)}")
    
    return df_mtf

def main():
    """Main execution"""
    print("="*70)
    print("🔧 FEATURE ENGINEERING PIPELINE")
    print("="*70)
    
    # Generate features for each timeframe
    df_1h = generate_features_1h()
    df_5m = generate_features_5m()
    df_15m = generate_features_15m()
    
    # Merge multi-timeframe features
    df_mtf = merge_mtf_features()
    
    # Summary
    print("\n" + "="*70)
    print("📊 FEATURE ENGINEERING SUMMARY")
    print("="*70)
    print(f"1H features:  {len(df_1h):,} rows, {len(df_1h.columns)} columns")
    print(f"5M features:  {len(df_5m):,} rows, {len(df_5m.columns)} columns")
    print(f"15M features: {len(df_15m):,} rows, {len(df_15m.columns)} columns")
    print(f"MTF features: {len(df_mtf):,} rows, {len(df_mtf.columns)} columns")
    print("\n✅ All features generated successfully!")
    print("="*70)

if __name__ == '__main__':
    main()
