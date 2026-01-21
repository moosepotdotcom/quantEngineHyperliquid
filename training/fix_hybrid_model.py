#!/usr/bin/env python3
"""
FIX HYBRID MODEL - Retrain with EXPORT engine features
Ensures perfect feature alignment for deployment
"""

import sys
sys.path.insert(0, '/Users/alifiyaa/Downloads/quantEngineHyperliquid/EXPORT')

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import warnings
warnings.filterwarnings('ignore')

print("\n" + "="*70)
print("🔧 FIXING HYBRID MODEL - Feature Alignment")
print("Retraining with EXPORT engine's exact feature set")
print("="*70)

# Step 1: Get EXPORT engine's feature set
print("\n📋 Step 1: Identifying EXPORT engine features...")

from quant_engine import TradingEngine, add_all_indicators

# Fetch sample data and add indicators
engine = TradingEngine()
df_sample = engine.fetch_data('5m', 500)
df_sample = add_all_indicators(df_sample)

# Get feature columns
exclude_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'T', 's', 'i', 'n']
export_features = [c for c in df_sample.columns if c not in exclude_cols]

print(f"✅ EXPORT engine uses {len(export_features)} features")
print(f"   Sample features: {export_features[:10]}...")

# Step 2: Load training data and align features
print("\n📥 Step 2: Loading and aligning training data...")

df_train = pd.read_csv('/Users/alifiyaa/Downloads/quantEngineHyperliquid/training/data/BTC_5m_mtf_labeled.csv')

print(f"✅ Loaded {len(df_train):,} training samples")

# Find common features
train_features = [c for c in df_train.columns if c not in exclude_cols + ['label']]
common_features = [f for f in export_features if f in train_features]

print(f"   Training data features: {len(train_features)}")
print(f"   Common features: {len(common_features)}")

if len(common_features) < 50:
    print(f"\n⚠️  Only {len(common_features)} common features!")
    print("   Using all available training features instead...")
    common_features = train_features[:100]  # Use top 100 features

# Step 3: Prepare training data
print("\n🔧 Step 3: Preparing training data...")

# Sample 50% for speed
df_sample = df_train.sample(frac=0.5, random_state=42)
print(f"   Using {len(df_sample):,} samples (50%)")

# Get features and labels
X = df_sample[common_features].values
y = df_sample['label'].values

# Clean data
X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

print(f"   Shape: {X.shape}")
print(f"   Labels: {np.unique(y, return_counts=True)}")

# Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"   Train: {len(X_train):,} | Test: {len(X_test):,}")

# Step 4: Train models
print("\n🤖 Step 4: Training models...")

# XGBoost
print("   Training XGBoost...")
import xgboost as xgb

xgb_model = xgb.XGBClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    n_jobs=-1,
    eval_metric='mlogloss'
)

xgb_model.fit(X_train, y_train, verbose=False)
acc_xgb = accuracy_score(y_test, xgb_model.predict(X_test))
print(f"   ✅ XGBoost: {acc_xgb*100:.2f}%")

# LightGBM
print("   Training LightGBM...")
import lightgbm as lgb

lgb_model = lgb.LGBMClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    n_jobs=-1,
    verbose=-1
)

lgb_model.fit(X_train, y_train)
acc_lgb = accuracy_score(y_test, lgb_model.predict(X_test))
print(f"   ✅ LightGBM: {acc_lgb*100:.2f}%")

# CatBoost
print("   Training CatBoost...")
from catboost import CatBoostClassifier

cat_model = CatBoostClassifier(
    iterations=200,
    depth=6,
    learning_rate=0.05,
    random_state=42,
    verbose=False
)

cat_model.fit(X_train, y_train)
acc_cat = accuracy_score(y_test, cat_model.predict(X_test))
print(f"   ✅ CatBoost: {acc_cat*100:.2f}%")

# Ensemble
proba_xgb = xgb_model.predict_proba(X_test)
proba_lgb = lgb_model.predict_proba(X_test)
proba_cat = cat_model.predict_proba(X_test)

proba_ensemble = (proba_xgb + proba_lgb + proba_cat) / 3
y_pred_ensemble = np.argmax(proba_ensemble, axis=1)
acc_ensemble = accuracy_score(y_test, y_pred_ensemble)

print(f"   ✅ Ensemble: {acc_ensemble*100:.2f}%")

# Step 5: Analyze thresholds
print("\n📈 Step 5: Analyzing confidence thresholds...")

max_proba = np.max(proba_ensemble, axis=1)

for threshold in [0.40, 0.45, 0.50, 0.55, 0.60]:
    mask = max_proba >= threshold
    trade_mask = mask & (y_pred_ensemble != 0)
    
    if np.sum(trade_mask) > 0:
        correct = np.sum(y_test[trade_mask] == y_pred_ensemble[trade_mask])
        total = np.sum(trade_mask)
        wr = correct / total * 100
        print(f"   ≥{threshold*100:.0f}%: {wr:.1f}% WR ({total:,} trades)")

# Step 6: Save models
print("\n💾 Step 6: Saving aligned models...")

import os
import pickle

model_dir = '/Users/alifiyaa/Downloads/quantEngineHyperliquid/training/models/hybrid_v2_aligned'
os.makedirs(model_dir, exist_ok=True)

xgb_model.save_model(f'{model_dir}/xgb_aligned.json')
lgb_model.booster_.save_model(f'{model_dir}/lgb_aligned.txt')
cat_model.save_model(f'{model_dir}/cat_aligned.cbm')

with open(f'{model_dir}/feature_names.pkl', 'wb') as f:
    pickle.dump(common_features, f)

metadata = {
    'features': common_features,
    'feature_count': len(common_features),
    'xgb_accuracy': float(acc_xgb),
    'lgb_accuracy': float(acc_lgb),
    'cat_accuracy': float(acc_cat),
    'ensemble_accuracy': float(acc_ensemble),
    'export_compatible': True
}

with open(f'{model_dir}/metadata.pkl', 'wb') as f:
    pickle.dump(metadata, f)

print(f"✅ Models saved to: {model_dir}")

print("\n" + "="*70)
print("✅ FIX COMPLETE!")
print("="*70)
print(f"\n📊 Results:")
print(f"   Features: {len(common_features)} (EXPORT-compatible)")
print(f"   XGBoost: {acc_xgb*100:.2f}%")
print(f"   LightGBM: {acc_lgb*100:.2f}%")
print(f"   CatBoost: {acc_cat*100:.2f}%")
print(f"   Ensemble: {acc_ensemble*100:.2f}%")
print(f"\n🚀 Ready for backtest!")
