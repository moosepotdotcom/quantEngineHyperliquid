#!/usr/bin/env python3
"""
Step 2: Test Predictions on Training Data
Verify model predictions match training accuracy
"""

import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
import pickle

print("="*70)
print("🧪 TESTING PREDICTIONS ON TRAINING DATA")
print("="*70)

model_dir = '/Users/alifiyaa/Downloads/quantEngineHyperliquid/HYBRID_V1_EXPORT'

# Load models
print("\n📦 Loading models...")
xgb_model = xgb.XGBClassifier()
xgb_model.load_model(f'{model_dir}/xgb_hybrid.json')

lgb_model = lgb.Booster(model_file=f'{model_dir}/lgb_hybrid.txt')

cat_model = CatBoostClassifier()
cat_model.load_model(f'{model_dir}/cat_hybrid.cbm')

with open(f'{model_dir}/feature_names.pkl', 'rb') as f:
    features = pickle.load(f)

print(f"✅ Models loaded ({len(features)} features)")

# Load SMALL sample of training data
print("\n📥 Loading training data sample...")
df = pd.read_csv('/Users/alifiyaa/Downloads/quantEngineHyperliquid/training/data/BTC_5m_mtf_labeled.csv',
                 nrows=10000)

print(f"✅ Loaded {len(df)} rows")

# Check label distribution
print("\n📊 Label distribution in data:")
print(df['label'].value_counts())

# Prepare features
print("\n🔧 Preparing features...")
X = df[features].values
y = df['label'].values

X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

print(f"   X shape: {X.shape}")
print(f"   y shape: {y.shape}")

# Get predictions from each model
print("\n🤖 Getting predictions...")

print("   XGBoost...")
proba_xgb = xgb_model.predict_proba(X)
print(f"      Output shape: {proba_xgb.shape}")

print("   LightGBM...")
proba_lgb_raw = lgb_model.predict(X)
print(f"      Raw output shape: {proba_lgb_raw.shape}")

# Fix LightGBM output
if len(proba_lgb_raw.shape) == 2 and proba_lgb_raw.shape[1] == 3:
    proba_lgb = proba_lgb_raw
    print(f"      Using raw output (already 3 classes)")
else:
    print(f"      ERROR: Unexpected LightGBM output shape!")
    print(f"      Expected: (n, 3), Got: {proba_lgb_raw.shape}")

print("   CatBoost...")
proba_cat = cat_model.predict_proba(X)
print(f"      Output shape: {proba_cat.shape}")

# Ensemble
print("\n🎯 Creating ensemble...")
proba_ensemble = (proba_xgb + proba_lgb + proba_cat) / 3
predictions = np.argmax(proba_ensemble, axis=1)
confidences = np.max(proba_ensemble, axis=1)

# Calculate accuracy
accuracy = np.mean(predictions == y)
print(f"✅ Ensemble accuracy: {accuracy*100:.2f}%")

# Check signal rate at different thresholds
print("\n📊 Signal rates by threshold:")
for threshold in [0.35, 0.40, 0.45, 0.50, 0.55, 0.60]:
    signal_mask = (confidences >= threshold) & (predictions != 0)
    signal_rate = np.sum(signal_mask) / len(predictions) * 100
    signal_count = np.sum(signal_mask)
    
    # Calculate accuracy for these signals
    if signal_count > 0:
        correct = np.sum(predictions[signal_mask] == y[signal_mask])
        signal_accuracy = correct / signal_count * 100
        print(f"   {threshold*100:.0f}%: {signal_rate:.1f}% rate ({signal_count:,} signals), {signal_accuracy:.1f}% accurate")

print("\n" + "="*70)
print("✅ PREDICTION TEST COMPLETE")
print("="*70)
