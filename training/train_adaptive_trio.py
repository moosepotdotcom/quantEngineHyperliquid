#!/usr/bin/env python3
"""
ADAPTIVE TRIO MODEL TRAINER
Uses 4 years of labeled MTF data to train adaptive trading models
Optimized for ONE position at a time
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import warnings
warnings.filterwarnings('ignore')

print("\n" + "="*70)
print("🚀 ADAPTIVE TRIO MODEL TRAINER")
print("Data: 4 years (420K samples) | Features: 238 MTF")
print("="*70)

# Load data
print("\n📥 Loading training data...")
df = pd.read_csv('/Users/alifiyaa/Downloads/quantEngineHyperliquid/training/data/BTC_5m_mtf_labeled.csv')

print(f"✅ Loaded {len(df):,} samples")
print(f"   Columns: {len(df.columns)}")

# Check what we have
if 'label' in df.columns:
    print(f"\n📊 Label distribution:")
    print(df['label'].value_counts())
else:
    print("\n⚠️  No 'label' column found. Checking for alternatives...")
    print(f"   Columns: {df.columns.tolist()[:20]}...")

# Prepare features
print("\n🔧 Preparing features...")

# Exclude non-feature columns
exclude_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'label', 
                'outcome', 'target', 'direction']
feature_cols = [c for c in df.columns if c not in exclude_cols and not c.startswith('Unnamed')]

print(f"   Features: {len(feature_cols)}")

# Get features and labels
X = df[feature_cols].values
y = df['label'].values if 'label' in df.columns else df.iloc[:, -1].values

# Handle NaN
X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

print(f"   Samples: {len(X):,}")
print(f"   Shape: {X.shape}")

# Train/test split
print("\n📊 Splitting data (80/20)...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"   Train: {len(X_train):,}")
print(f"   Test: {len(X_test):,}")

# Train Model 1: XGBoost Entry Classifier
print("\n🤖 Training Model 1: XGBoost Entry Classifier...")
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
y_pred_xgb = xgb_model.predict(X_test)
acc_xgb = accuracy_score(y_test, y_pred_xgb)

print(f"✅ XGBoost trained!")
print(f"   Accuracy: {acc_xgb*100:.2f}%")

# Train Model 2: LightGBM
print("\n🤖 Training Model 2: LightGBM...")
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
y_pred_lgb = lgb_model.predict(X_test)
acc_lgb = accuracy_score(y_test, y_pred_lgb)

print(f"✅ LightGBM trained!")
print(f"   Accuracy: {acc_lgb*100:.2f}%")

# Train Model 3: CatBoost
print("\n🤖 Training Model 3: CatBoost...")
from catboost import CatBoostClassifier

cat_model = CatBoostClassifier(
    iterations=200,
    depth=6,
    learning_rate=0.05,
    random_state=42,
    verbose=False
)

cat_model.fit(X_train, y_train)
y_pred_cat = cat_model.predict(X_test)
acc_cat = accuracy_score(y_test, y_pred_cat)

print(f"✅ CatBoost trained!")
print(f"   Accuracy: {acc_cat*100:.2f}%")

# Ensemble
print("\n🎯 Creating Ensemble...")

proba_xgb = xgb_model.predict_proba(X_test)
proba_lgb = lgb_model.predict_proba(X_test)
proba_cat = cat_model.predict_proba(X_test)

proba_ensemble = (proba_xgb + proba_lgb + proba_cat) / 3
y_pred_ensemble = np.argmax(proba_ensemble, axis=1)

acc_ensemble = accuracy_score(y_test, y_pred_ensemble)

print(f"✅ Ensemble created!")
print(f"   Accuracy: {acc_ensemble*100:.2f}%")

# Detailed metrics
print("\n📊 Classification Report:")
print(classification_report(y_test, y_pred_ensemble))

# Win rate by confidence
print("\n📈 Win Rate by Confidence Threshold:")

max_proba = np.max(proba_ensemble, axis=1)

for threshold in [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]:
    mask = max_proba >= threshold
    trade_mask = mask & (y_pred_ensemble != 0)
    
    if np.sum(trade_mask) > 0:
        correct = np.sum(y_test[trade_mask] == y_pred_ensemble[trade_mask])
        total = np.sum(trade_mask)
        wr = correct / total * 100
        print(f"   ≥{threshold*100:.0f}%: {wr:.1f}% WR ({total:,} trades)")

# Save models
print("\n💾 Saving models...")

import os
model_dir = '/Users/alifiyaa/Downloads/quantEngineHyperliquid/training/models/adaptive_trio'
os.makedirs(model_dir, exist_ok=True)

xgb_model.save_model(f'{model_dir}/xgb_adaptive.json')
lgb_model.booster_.save_model(f'{model_dir}/lgb_adaptive.txt')
cat_model.save_model(f'{model_dir}/cat_adaptive.cbm')

import pickle
with open(f'{model_dir}/feature_names.pkl', 'wb') as f:
    pickle.dump(feature_cols, f)

print(f"✅ Models saved to: {model_dir}")

print("\n" + "="*70)
print("✅ TRAINING COMPLETE!")
print("="*70)
print(f"\n📊 Summary:")
print(f"   XGBoost: {acc_xgb*100:.2f}%")
print(f"   LightGBM: {acc_lgb*100:.2f}%")
print(f"   CatBoost: {acc_cat*100:.2f}%")
print(f"   Ensemble: {acc_ensemble*100:.2f}%")
print(f"\n🎯 Next: Backtest and deploy!")
