import pandas as pd
import numpy as np

# Load working data (Training/Dec 2025)
print("Loading reference data...")
df_ref = pd.read_csv('training/data/BTC_5m_mtf_labeled.csv')
features = [x for x in df_ref.columns if 'rsi' in x or 'adx' in x or 'volume' in x][:5]

# Load new data (Jan 2026)
print("Loading new data...")
df_new = pd.read_csv('training/data/BTC_5m_jan2_14_2026_mtf_full.csv')

print("\n--- Feature Statistics Comparison ---")
columns_to_check = ['rsi_14', 'adx', 'close', 'volume']
# Add some MTF columns if they exist common to both
common_cols = [c for c in df_ref.columns if c in df_new.columns and np.issubdtype(df_ref[c].dtype, np.number)]
check_cols = common_cols[:10] + ['rsi_14', 'adx', 'rsi_14_1h', 'adx_1h'] 
check_cols = list(set([c for c in check_cols if c in df_new.columns]))

for col in check_cols:
    ref_mean = df_ref[col].mean()
    ref_std = df_ref[col].std()
    new_mean = df_new[col].mean()
    new_std = df_new[col].std()
    
    print(f"\nFeature: {col}")
    print(f"  Ref Mean: {ref_mean:.4f} | Std: {ref_std:.4f}")
    print(f"  New Mean: {new_mean:.4f} | Std: {new_std:.4f}")
    
    if abs(ref_mean - new_mean) > ref_std:
        print("  ⚠️  SIGNIFICANT MEAN SHIFT")
    if abs(ref_std - new_std) > (ref_std * 0.5):
        print("  ⚠️  SIGNIFICANT VARIANCE SHIFT")

