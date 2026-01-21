#!/usr/bin/env python3
"""
PHASE 2 STEP 2: Train Scalping Models (Simplified)
Uses pandas for indicators instead of TA-Lib
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("\n" + "🚀"*35)
print("PHASE 2 STEP 2: TRAINING SCALPING MODELS")
print("🚀"*35)

# Step 1: Load labeled data
print("\n📥 Loading labeled data...")
df = pd.read_csv('/Users/alifiyaa/Downloads/quantEngineHyperliquid/training/data/scalping_labels_0.5pct.csv')
print(f"✅ Loaded {len(df):,} samples")

# Step 2: Add simple indicators
print("\n🔧 Adding technical indicators...")

def add_simple_indicators(df):
    """Add basic technical indicators using pandas"""
    df = df.copy()
    
    # Moving averages
    df['sma_10'] = df['close'].rolling(10).mean()
    df['sma_20'] = df['close'].rolling(20).mean()
    df['sma_50'] = df['close'].rolling(50).mean()
    df['ema_10'] = df['close'].ewm(span=10).mean()
    df['ema_20'] = df['close'].ewm(span=20).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi_14'] = 100 - (100 / (1 + rs))
    
    # Volatility
    df['atr_14'] = (df['high'] - df['low']).rolling(14).mean()
    df['volatility'] = df['close'].pct_change().rolling(20).std()
    
    # Price features
    df['price_change'] = df['close'].pct_change()
    df['high_low_ratio'] = df['high'] / df['low']
    df['close_open_ratio'] = df['close'] / df['open']
    
    # Volume
    df['volume_sma'] = df['volume'].rolling(20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_sma']
    
    # Momentum
    df['momentum_5'] = df['close'] / df['close'].shift(5) - 1
    df['momentum_10'] = df['close'] / df['close'].shift(10) - 1
    
    return df

df_features = add_simple_indicators(df)
print(f"✅ Added indicators. Shape: {df_features.shape}")

# Step 3: Prepare training data
print("\n📊 Preparing training data...")

# Remove rows with NaN
df_clean = df_features.dropna()
print(f"   After cleaning: {len(df_clean):,} samples")

# Separate features and labels
exclude_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'label']
feature_cols = [c for c in df_clean.columns if c not in exclude_cols]

X = df_clean[feature_cols].values
y = df_clean['label'].values

# Handle any remaining NaN/inf
X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

print(f"   Features: {len(feature_cols)}")
print(f"   Samples: {len(X):,}")
print(f"   Labels: LONG={np.sum(y==1):,}, SHORT={np.sum(y==2):,}, NEUTRAL={np.sum(y==0):,}")

# Step 4: Train/Test split
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"\n📊 Train/Test Split:")
print(f"   Training: {len(X_train):,} samples")
print(f"   Testing: {len(X_test):,} samples")

# Step 5: Train XGBoost
print("\n🤖 Training XGBoost...")
import xgboost as xgb

xgb_model = xgb.XGBClassifier(
    n_estimators=200,
    max_depth=5,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    n_jobs=-1,
    eval_metric='mlogloss'
)

xgb_model.fit(X_train, y_train, verbose=False)
print("✅ XGBoost trained!")

# Evaluate
from sklearn.metrics import accuracy_score

y_pred_xgb = xgb_model.predict(X_test)
acc_xgb = accuracy_score(y_test, y_pred_xgb)
print(f"   Test Accuracy: {acc_xgb*100:.2f}%")

# Step 6: Train LightGBM
print("\n🤖 Training LightGBM...")
import lightgbm as lgb

lgb_model = lgb.LGBMClassifier(
    n_estimators=200,
    max_depth=5,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    n_jobs=-1,
    verbose=-1
)

lgb_model.fit(X_train, y_train)
print("✅ LightGBM trained!")

y_pred_lgb = lgb_model.predict(X_test)
acc_lgb = accuracy_score(y_test, y_pred_lgb)
print(f"   Test Accuracy: {acc_lgb*100:.2f}%")

# Step 7: Train CatBoost
print("\n🤖 Training CatBoost...")
from catboost import CatBoostClassifier

cat_model = CatBoostClassifier(
    iterations=200,
    depth=5,
    learning_rate=0.05,
    random_state=42,
    verbose=False
)

cat_model.fit(X_train, y_train)
print("✅ CatBoost trained!")

y_pred_cat = cat_model.predict(X_test)
acc_cat = accuracy_score(y_test, y_pred_cat)
print(f"   Test Accuracy: {acc_cat*100:.2f}%")

# Step 8: Ensemble evaluation
print("\n🎯 Ensemble Evaluation...")

proba_xgb = xgb_model.predict_proba(X_test)
proba_lgb = lgb_model.predict_proba(X_test)
proba_cat = cat_model.predict_proba(X_test)

proba_ensemble = (proba_xgb + proba_lgb + proba_cat) / 3
y_pred_ensemble = np.argmax(proba_ensemble, axis=1)

acc_ensemble = accuracy_score(y_test, y_pred_ensemble)
print(f"   Ensemble Accuracy: {acc_ensemble*100:.2f}%")

# Step 9: Analyze win rate by confidence
print("\n📊 Win Rate by Confidence Threshold:")

max_proba = np.max(proba_ensemble, axis=1)

for threshold in [0.40, 0.45, 0.50, 0.55, 0.60]:
    mask = max_proba >= threshold
    trade_mask = mask & (y_pred_ensemble != 0)
    
    if np.sum(trade_mask) > 0:
        correct = np.sum(y_test[trade_mask] == y_pred_ensemble[trade_mask])
        total = np.sum(trade_mask)
        wr = correct / total * 100
        print(f"   >={threshold*100:.0f}%: {wr:.1f}% WR ({total:,} trades)")

# Step 10: Save models
print("\n💾 Saving models...")

model_dir = '/Users/alifiyaa/Downloads/quantEngineHyperliquid/training/models/scalping'
os.makedirs(model_dir, exist_ok=True)

xgb_model.save_model(f'{model_dir}/xgb_scalper.json')
lgb_model.booster_.save_model(f'{model_dir}/lgb_scalper.txt')
cat_model.save_model(f'{model_dir}/cat_scalper.cbm')

import pickle
with open(f'{model_dir}/feature_names.pkl', 'wb') as f:
    pickle.dump(feature_cols, f)

print(f"   ✅ Saved all models to: {model_dir}")

print("\n✅ PHASE 2 STEP 2 COMPLETE!")
print(f"\n📊 Summary:")
print(f"   Models: XGBoost, LightGBM, CatBoost")
print(f"   Ensemble Accuracy: {acc_ensemble*100:.2f}%")
print(f"   Features: {len(feature_cols)}")
print(f"\n🎯 Ready for backtest!")
