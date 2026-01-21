#!/usr/bin/env python3
"""
Generate MTF features for Jan 2026 data and run V8 Enhanced backtest
"""

import pandas as pd
import numpy as np
import sys
import os

# Add paths for feature engineering
sys.path.insert(0, 'EXPORT')
sys.path.insert(0, 'training')

print("="*70)
print("🔧 GENERATING MTF FEATURES FOR JAN 2026")
print("="*70)

# Load Jan 2026 data
print("\n📥 Loading Jan 2026 data...")
df = pd.read_csv('training/data/BTC_5m_2025_enriched.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Filter to Jan 2-14, 2026
df_jan = df[
    (df['timestamp'] >= '2026-01-02') &
    (df['timestamp'] <= '2026-01-14 23:59:59')
].copy()

print(f"✅ Loaded {len(df_jan)} candles")
print(f"   Period: {df_jan['timestamp'].min()} to {df_jan['timestamp'].max()}")

# Generate MTF features using existing feature generator
print("\n🔧 Generating MTF features...")

try:
    from utils.mtf_features import generate_mtf_features
    df_mtf = generate_mtf_features(df_jan)
    print(f"✅ MTF features generated: {len(df_mtf.columns)} columns")
except:
    print("⚠️  Using training feature generator...")
    from feature_generator import FeatureGenerator
    
    fg = FeatureGenerator()
    df_mtf = fg.generate_features(df_jan)
    print(f"✅ Features generated: {len(df_mtf.columns)} columns")

# Save
output_file = 'training/data/BTC_5m_jan2_14_2026_mtf.csv'
df_mtf.to_csv(output_file, index=False)
print(f"\n💾 Saved to {output_file}")

print("\n" + "="*70)
print("✅ FEATURE GENERATION COMPLETE")
print("="*70)
print(f"\nReady to backtest on {len(df_mtf)} candles!")
