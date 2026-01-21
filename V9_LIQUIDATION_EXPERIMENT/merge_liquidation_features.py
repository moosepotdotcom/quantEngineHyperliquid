#!/usr/bin/env python3
"""
Merge liquidation features with enriched 2025 data
"""

import pandas as pd
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.v5_feature_engineer import generate_v5_features

print("🔄 Merging Liquidation Features with Enriched Data")
print("="*70)

# Load enriched data
print("📥 Loading enriched 2025 data...")
df_enriched = pd.read_csv('../training/data/BTC_5m_2025_enriched.csv')
df_enriched['timestamp'] = pd.to_datetime(df_enriched['timestamp'])

# Generate features
print("🧠 Generating V5 features...")
df_enriched = generate_v5_features(df_enriched)

# Load liquidation proxy
print("📥 Loading liquidation proxy...")
df_liq = pd.read_csv('BTC_5m_2025_with_liquidation_proxy.csv')
df_liq['timestamp'] = pd.to_datetime(df_liq['timestamp'])

# Merge on timestamp
print("🔗 Merging datasets...")
liq_cols = ['timestamp', 'liq_proxy_score', 'liq_direction', 'liq_cluster', 
            'liq_cluster_count', 'vol_surge', 'wick_ratio', 'is_vol_spike', 'is_long_wick']

# Only keep liquidation-specific columns
df_liq_features = df_liq[liq_cols]

# Merge
df_merged = pd.merge(df_enriched, df_liq_features, on='timestamp', how='left')

print(f"\n✅ Merged dataset:")
print(f"   Rows: {len(df_merged)}")
print(f"   Columns: {len(df_merged.columns)}")
print(f"   Liquidation features: {len(liq_cols)-1}")

# Save
output_file = '../training/data/BTC_5m_2025_enriched_with_liquidations.csv'
df_merged.to_csv(output_file, index=False)
print(f"\n💾 Saved to {output_file}")

# Show sample
print(f"\n📋 Sample with liquidation features:")
sample_cols = ['timestamp', 'close', 'cvd_1h', 'rsi_15m', 'ema_50_15m', 
               'liq_proxy_score', 'liq_direction', 'vol_surge']
available_cols = [c for c in sample_cols if c in df_merged.columns]
print(df_merged[available_cols].head(10).to_string(index=False))
