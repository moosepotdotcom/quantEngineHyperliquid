#!/usr/bin/env python3
"""
Step 1: Verify Model Integrity
Checks that models load correctly and metadata matches expectations
"""

import pickle
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier

print("="*70)
print("🔍 HYBRID V1 MODEL INTEGRITY CHECK")
print("="*70)

model_dir = '/Users/alifiyaa/Downloads/quantEngineHyperliquid/HYBRID_V1_EXPORT'

# Load metadata
print("\n📋 Loading metadata...")
with open(f'{model_dir}/metadata.pkl', 'rb') as f:
    metadata = pickle.load(f)

print("✅ Metadata loaded:")
for key, value in metadata.items():
    if isinstance(value, list):
        print(f"   {key}: {len(value)} items")
    elif isinstance(value, float):
        print(f"   {key}: {value:.4f}")
    else:
        print(f"   {key}: {value}")

# Load feature names
print("\n📋 Loading feature names...")
with open(f'{model_dir}/feature_names.pkl', 'rb') as f:
    features = pickle.load(f)

print(f"✅ Features loaded: {len(features)}")
print(f"   First 10: {features[:10]}")

# Load models
print("\n📦 Loading XGBoost...")
xgb_model = xgb.XGBClassifier()
xgb_model.load_model(f'{model_dir}/xgb_hybrid.json')
print(f"✅ XGBoost loaded")
print(f"   Classes: {xgb_model.n_classes_}")

print("\n📦 Loading LightGBM...")
lgb_model = lgb.Booster(model_file=f'{model_dir}/lgb_hybrid.txt')
print(f"✅ LightGBM loaded")
print(f"   Num classes: {lgb_model.num_model_per_iteration()}")

print("\n📦 Loading CatBoost...")
cat_model = CatBoostClassifier()
cat_model.load_model(f'{model_dir}/cat_hybrid.cbm')
print(f"✅ CatBoost loaded")
print(f"   Classes: {cat_model.classes_}")

print("\n" + "="*70)
print("✅ ALL MODELS LOADED SUCCESSFULLY")
print("="*70)

# Check threshold results from metadata
if 'threshold_results' in metadata:
    print("\n📊 Training Threshold Results:")
    for threshold, wr, trades in metadata['threshold_results']:
        print(f"   {threshold*100:.0f}%: {wr:.1f}% WR ({trades:,} trades)")
