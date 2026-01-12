#!/usr/bin/env python3
"""
Verify Model Consistency (V2 Calibrated Pickle)
Feeds features from the live log into the V2 Calibrated model to confirm it reproduces the prediction.
"""

import json
import numpy as np
import pandas as pd
import joblib
from utils.feature_engineer import add_all_indicators

print("=" * 70)
print("🔬 VERIFYING MODEL CONSISTENCY (V2 CALIBRATED)")
print("=" * 70)

# 1. Load the live log entry
target_time_str = "2026-01-08T00:32:31"
log_entry = None

with open('logs/trades/predictions_20260108.jsonl', 'r') as f:
    for line in f:
        if target_time_str in line and "MTF Scalper" in line:
            log_entry = json.loads(line)
            break

if not log_entry:
    print("❌ Log entry not found")
    exit(1)

live_features = log_entry['features']
live_conf = log_entry['confidence']
print(f"✅ Found log entry")
print(f"   Live Confidence: {live_conf:.4%}")

# 2. Load V2 Calibrated Model
print("\n🤖 Loading V2 Calibrated Model (Pickle)...")
try:
    mtf_calibrated = joblib.load('models/mtf_scalper_5m_v2_calibrated.pkl')
    print("✅ V2 Calibrated Model loaded")
except Exception as e:
    print(f"❌ Failed to load pickle: {e}")
    exit(1)

# 3. Prepare Feature Vector (Reconstruct Order)
# Generate canonical feature list order
dummy_data = {
    'open': [100.0]*50, 'high': [105.0]*50, 'low': [95.0]*50, 'close': [100.0]*50, 'volume': [1000]*50,
    'timestamp': pd.date_range(start='2026-01-01', periods=50, freq='5T')
}
df_dummy = pd.DataFrame(dummy_data)
df_dummy = add_all_indicators(df_dummy)
exclude = ['open', 'high', 'low', 'close', 'volume']
cols = [c for c in df_dummy.columns if c not in exclude]
cols_15m = [f"{c}_15m" for c in cols]
cols_1h = [f"{c}_1h" for c in cols]
all_features_ordered = cols + cols_15m + cols_1h
all_features_ordered = [c for c in all_features_ordered if 'hurst' not in c and 'timestamp' not in c]

print(f"   Constructed ordered feature list: {len(all_features_ordered)} items")

# Check log keys
log_keys = set(live_features.keys())
expected = set(all_features_ordered)
missing = expected - log_keys
extra = log_keys - expected
if missing: print(f"⚠️ Missing features in log: {len(missing)}")
if extra: print(f"⚠️ Extra features in log: {len(extra)}")

# Construct input vector
X_values = []
for feat in all_features_ordered:
    X_values.append(live_features.get(feat, 0.0))

X = np.array(X_values).reshape(1, -1)

# 4. Predict
print("\n🔮 Running Prediction (V2 Calibrated)...")
try:
    probas = mtf_calibrated.predict_proba(X)
    print(f"   Probas Shape: {probas.shape}")
    print(f"   Probas: {probas[0]}")
    
    prob_class0 = float(probas[0][0])
    prob_class1 = float(probas[0][1])
    
    print(f"\n   Re-calculated Class 0: {prob_class0:.4%}")
    print(f"   Re-calculated Class 1: {prob_class1:.4%}")
    print(f"   Original Logged Confidence: {live_conf:.4%}")
    
    match_diff = min(abs(prob_class0 - live_conf), abs(prob_class1 - live_conf))
    
    if match_diff < 0.0001:
        print("\n✅ PERFECT MATCH! The live bot was using the V2 Calibrated model.")
        if abs(prob_class1 - live_conf) < 0.0001:
            print("   👉 The signal was for Class 1 (Likely LONG/TRADE).")
        else:
            print("   👉 The signal was for Class 0 (Likely NO TRADE).")
    else:
        print("\n❌ MISMATCH! Still different.")

except Exception as e:
    print(f"\n❌ Prediction failed: {e}")

print("=" * 70)
