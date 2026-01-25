import pandas as pd
import numpy as np
import os
import sys

# Set up paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.feature_engineer import add_all_indicators

def forensic_leakage_test():
    print("🔬 INITIALIZING FORENSIC INTEGRITY AUDIT (SHIFT-1 SECURE)")
    
    # 1. Load a chunk of real data
    data_path = 'training/data/BTC_5m_aug2025_blind.csv'
    df_raw = pd.read_csv(data_path).head(500)
    
    # 2. Baseline Calculation (The Truth at Time T)
    df_baseline = add_all_indicators(df_raw.copy())
    
    # 3. The "Lookahead" Perturbation
    # We will pick a specific timestamp T, and then CORRUPT all data at T+1, T+2, T+3
    # If the indicators at T change, it means there is a "Peek" (Lookahead Leakage)
    T_idx = 250
    target_ts = df_raw.iloc[T_idx]['timestamp']
    print(f"   Target Audit Time: {target_ts} (Row {T_idx})")
    
    df_corrupted = df_raw.copy()
    # Replace future highs/lows with impossible values
    df_corrupted.loc[T_idx+1:, 'high'] = 999999.0 
    df_corrupted.loc[T_idx+1:, 'low'] = 1.0
    df_corrupted.loc[T_idx+1:, 'close'] = 500000.0
    
    # 4. Recalculate indicators on corrupted future
    df_audit = add_all_indicators(df_corrupted)
    
    # 5. Verify Integrity
    exclude = ['timestamp', 'high', 'low', 'close', 'open', 'volume']
    test_cols = [c for c in df_baseline.columns if c not in exclude]
    
    leakage_detected = False
    print(f"   Auditing {len(test_cols)} features for future dependency...")
    
    for col in test_cols:
        val_baseline = df_baseline.iloc[T_idx][col]
        val_audit = df_audit.iloc[T_idx][col]
        
        # Check for delta
        if not np.isclose(val_baseline, val_audit, atol=1e-8):
            print(f"   ❌ LEAKAGE DETECTED in feature: {col}")
            print(f"      Baseline: {val_baseline} | Corrupted Future: {val_audit}")
            leakage_detected = True
            
    if not leakage_detected:
        print("\n🏆 VERDICT: 100% SECURE. Indicators at Time T have ZERO knowledge of Future T+1.")
        print("   The Renaissance Engine is mathematically blind to the future.")
    else:
        print("\n⚠️ ALERT: Lookahead bias found in internal engine math.")

if __name__ == "__main__":
    forensic_leakage_test()
