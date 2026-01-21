#!/usr/bin/env python3
"""
HYBRID MODEL TRAINER
Uses 420K pre-labeled samples with regime detection and optimized thresholds
Optimized for ONE position at a time
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import warnings
warnings.filterwarnings('ignore')

print("\n" + "="*70)
print("🚀 HYBRID MODEL TRAINER")
print("Data: 420K samples (4 years) | Features: 238 MTF")
print("Goal: 75-80% WR, Optimized for 1 position at a time")
print("="*70)

# Load data
print("\n📥 Loading training data (this may take a minute)...")
df = pd.read_csv('/Users/alifiyaa/Downloads/quantEngineHyperliquid/training/data/BTC_5m_mtf_labeled.csv')

print(f"✅ Loaded {len(df):,} samples")
print(f"   Columns: {len(df.columns)}")
print(f"   Memory: {df.memory_usage(deep=True).sum() / 1024**2:.1f} MB")

# Check labels
print(f"\n📊 Label distribution:")
if 'label' in df.columns:
    label_counts = df['label'].value_counts()
    print(label_counts)
    total = len(df)
    for label, count in label_counts.items():
        print(f"   {label}: {count:,} ({count/total*100:.1f}%)")
else:
    print("   ⚠️  No 'label' column - checking alternatives...")
    print(f"   Available columns: {df.columns.tolist()[:10]}...")

# Prepare features
print("\n🔧 Preparing features...")

# Exclude non-feature columns
exclude_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'label', 
                'outcome', 'target', 'direction', 'Unnamed: 0']
feature_cols = [c for c in df.columns if c not in exclude_cols and not c.startswith('Unnamed')]

print(f"   Feature columns: {len(feature_cols)}")

# Sample for faster training (use 50% of data = 210K samples)
print(f"\n⚡ Sampling data for faster training...")
df_sample = df.sample(frac=0.5, random_state=42)
print(f"   Using {len(df_sample):,} samples (50%)")

# Get features and labels
X = df_sample[feature_cols].values
y = df_sample['label'].values if 'label' in df_sample.columns else df_sample.iloc[:, -1].values

# Handle NaN/inf
print(f"\n🧹 Cleaning data...")
X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

print(f"   Final shape: {X.shape}")
print(f"   Labels: {np.unique(y, return_counts=True)}")

# Train/test split
print("\n📊 Splitting data (80/20)...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"   Train: {len(X_train):,} samples")
print(f"   Test: {len(X_test):,} samples")

# Train XGBoost
print("\n🤖 Training XGBoost (Model 1/3)...")
import xgboost as xgb

xgb_model = xgb.XGBClassifier(
    n_estimators=300,
    max_depth=7,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    n_jobs=-1,
    eval_metric='mlogloss'
)

print("   Training... (this will take 2-3 minutes)")
xgb_model.fit(X_train, y_train, verbose=False)

y_pred_xgb = xgb_model.predict(X_test)
acc_xgb = accuracy_score(y_test, y_pred_xgb)

print(f"✅ XGBoost complete!")
print(f"   Accuracy: {acc_xgb*100:.2f}%")

# Train LightGBM
print("\n🤖 Training LightGBM (Model 2/3)...")
import lightgbm as lgb

lgb_model = lgb.LGBMClassifier(
    n_estimators=300,
    max_depth=7,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    n_jobs=-1,
    verbose=-1
)

print("   Training... (this will take 2-3 minutes)")
lgb_model.fit(X_train, y_train)

y_pred_lgb = lgb_model.predict(X_test)
acc_lgb = accuracy_score(y_test, y_pred_lgb)

print(f"✅ LightGBM complete!")
print(f"   Accuracy: {acc_lgb*100:.2f}%")

# Train CatBoost
print("\n🤖 Training CatBoost (Model 3/3)...")
from catboost import CatBoostClassifier

cat_model = CatBoostClassifier(
    iterations=300,
    depth=7,
    learning_rate=0.05,
    random_state=42,
    verbose=False
)

print("   Training... (this will take 2-3 minutes)")
cat_model.fit(X_train, y_train)

y_pred_cat = cat_model.predict(X_test)
acc_cat = accuracy_score(y_test, y_pred_cat)

print(f"✅ CatBoost complete!")
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

# Win rate by confidence
print("\n📈 Win Rate by Confidence Threshold:")

max_proba = np.max(proba_ensemble, axis=1)

threshold_results = []
for threshold in [0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]:
    mask = max_proba >= threshold
    trade_mask = mask & (y_pred_ensemble != 0)
    
    if np.sum(trade_mask) > 0:
        correct = np.sum(y_test[trade_mask] == y_pred_ensemble[trade_mask])
        total = np.sum(trade_mask)
        wr = correct / total * 100
        print(f"   ≥{threshold*100:.0f}%: {wr:.1f}% WR ({total:,} trades, {total/len(y_test)*100:.1f}% of data)")
        threshold_results.append((threshold, wr, total))

# Find optimal threshold (target 75%+ WR)
print(f"\n🎯 Optimal Threshold Analysis:")
for threshold, wr, trades in threshold_results:
    if wr >= 75.0:
        print(f"   ✅ {threshold*100:.0f}% confidence → {wr:.1f}% WR ({trades:,} trades)")

# Save models
print("\n💾 Saving models...")

import os
model_dir = '/Users/alifiyaa/Downloads/quantEngineHyperliquid/training/models/hybrid_v1'
os.makedirs(model_dir, exist_ok=True)

xgb_model.save_model(f'{model_dir}/xgb_hybrid.json')
lgb_model.booster_.save_model(f'{model_dir}/lgb_hybrid.txt')
cat_model.save_model(f'{model_dir}/cat_hybrid.cbm')

import pickle
with open(f'{model_dir}/feature_names.pkl', 'wb') as f:
    pickle.dump(feature_cols, f)

# Save metadata
metadata = {
    'training_date': pd.Timestamp.now().isoformat(),
    'samples_trained': len(X_train),
    'samples_tested': len(X_test),
    'xgb_accuracy': float(acc_xgb),
    'lgb_accuracy': float(acc_lgb),
    'cat_accuracy': float(acc_cat),
    'ensemble_accuracy': float(acc_ensemble),
    'threshold_results': threshold_results,
    'feature_count': len(feature_cols)
}

with open(f'{model_dir}/metadata.pkl', 'wb') as f:
    pickle.dump(metadata, f)

print(f"✅ Models saved to: {model_dir}")

print("\n" + "="*70)
print("✅ HYBRID MODEL TRAINING COMPLETE!")
print("="*70)
print(f"\n📊 Final Results:")
print(f"   XGBoost: {acc_xgb*100:.2f}%")
print(f"   LightGBM: {acc_lgb*100:.2f}%")
print(f"   CatBoost: {acc_cat*100:.2f}%")
print(f"   Ensemble: {acc_ensemble*100:.2f}%")

# Find best threshold
best_threshold = None
for threshold, wr, trades in threshold_results:
    if wr >= 75.0 and trades >= 1000:
        best_threshold = threshold
        break

if best_threshold:
    print(f"\n🎯 Recommended Threshold: {best_threshold*100:.0f}%")
    print(f"   Expected Win Rate: {[wr for t,wr,_ in threshold_results if t==best_threshold][0]:.1f}%")
else:
    print(f"\n⚠️  No threshold achieved 75%+ WR with sufficient trades")
    print(f"   Best: {threshold_results[0][0]*100:.0f}% → {threshold_results[0][1]:.1f}% WR")

print(f"\n🚀 Next: Backtest on Jan 2-11 to verify performance!")
