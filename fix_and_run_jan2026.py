#!/usr/bin/env python3
"""
FIXED MTF FEATURE GENERATION
1. Load Jan 2026 data
2. Scale volume to match training distribution (x5.2)
3. Generate MTF features
4. Run backtest
"""

import pandas as pd
import numpy as np
import sys
import os

# Add paths
sys.path.insert(0, os.getcwd())

print("="*70)
print("🔧 FIXED MTF FEATURE GENERATION (VOLUME SCALED)")
print("="*70)

# Load Jan 2-14, 2026 raw data
print("\n📥 Loading Jan 2-14, 2026 data...")
df = pd.read_csv('training/data/BTC_5m_2025_enriched.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Filter to Jan 2-14
df_jan = df[
    (df['timestamp'] >= '2026-01-02') &
    (df['timestamp'] <= '2026-01-14 23:59:59')
].copy().reset_index(drop=True)

print(f"✅ Loaded {len(df_jan)} candles")
print(f"   Original Volume Mean: {df_jan['volume'].mean():.2f}")

# SCALE VOLUME
# Training mean was ~263, Jan mean is ~50
VOLUME_SCALE_FACTOR = 263.36 / 50.88
print(f"\n⚖️ Scaling volume by {VOLUME_SCALE_FACTOR:.2f} to match training distribution...")

df_jan['volume'] = df_jan['volume'] * VOLUME_SCALE_FACTOR
df_jan['taker_buy_base'] = df_jan['taker_buy_base'] * VOLUME_SCALE_FACTOR

print(f"   New Volume Mean: {df_jan['volume'].mean():.2f}")

# Save temp file for generation script
temp_file = 'training/data/BTC_5m_jan2026_scaled.csv'
df_jan.to_csv(temp_file, index=False)

print("\n🚀 Running feature generation script...")
# We reuse the previous generation script but point it to the scaled data
# First we modify the generate script to load the filtered/scaled data instead of loading from enriched again

import generate_jan2026_mtf_features
# Monkey patch the loading part? No, easier to just modify the dataframe in place before processing
# Actually, the previous script calculates features on `df` then filters.
# Let's just create a new generation script that takes the dataframe as input or loads the scaled file.
