#!/usr/bin/env python3
"""
PHASE 2 STEP 2: Add Indicators & Train Scalping Models
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Add paths
sys.path.insert(0, '/Users/alifiyaa/Downloads/quantEngineHyperliquid/EXPORT')
sys.path.insert(0, '/Users/alifiyaa/Downloads/quantEngineHyperliquid/EXPORT/utils')

# Import feature engineering
import talib
from advanced_features import add_advanced_features

def add_all_indicators(df):
    """Add all technical indicators"""
    df = df.copy()
    
    # Basic indicators
    df['sma_20'] = talib.SMA(df['close'], timeperiod=20)
    df['ema_20'] = talib.EMA(df['close'], timeperiod=20)
    df['rsi_14'] = talib.RSI(df['close'], timeperiod=14)
    df['rsi_7'] = talib.RSI(df['close'], timeperiod=7)
    df['macd'], df['macd_signal'], df['macd_hist'] = talib.MACD(df['close'])
    df['atr_14'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
    df['bbands_upper'], df['bbands_middle'], df['bbands_lower'] = talib.BBANDS(df['close'])
    
    # Advanced features
    df = add_advanced_features(df)
    
    return df

print("\n" + "🚀"*35)
print("PHASE 2 STEP 2: TRAINING SCALPING MODELS")
print("🚀"*35)

# Step 1: Load labeled data
print("\n📥 Loading labeled data...")
df = pd.read_csv('/Users/alifiyaa/Downloads/quantEngineHyperliquid/training/data/scalping_labels_0.5pct.csv')
print(f"✅ Loaded {len(df):,} samples")

# Step 2: Add indicators
print("\n🔧 Adding technical indicators...")
print("   This may take a few minutes...")

df_features = add_all_indicators(df)
print(f"✅ Added indicators. Shape: {df_features.shape}")

# Step 3: Prepare training data
print("\n📊 Preparing training data...")

# Remove rows with NaN (from indicator calculation)
df_clean = df_features.dropna()
print(f"   After cleaning: {len(df_clean):,} samples")

# Separate features and labels
exclude_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'label']
feature_cols = [c for c in df_clean.columns if c not in exclude_cols]

X = df_clean[feature_cols].values
y = df_clean['label'].values

print(f"   Features: {len(feature_cols)}")
print(f"   Samples: {len(X):,}")
print(f"   Labels: LONG={np.sum(y==1):,}, SHORT={np.sum(y==2):,}, NEUTRAL={np.sum(y==0):,}")

# Step 4: Train/Test split
from sklearn.model_selection import train_test_split

# Use 80/20 split
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
    n_estimators=300,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    n_jobs=-1,
    eval_metric='mlogloss'
)

xgb_model.fit(X_train, y_train)
print("✅ XGBoost trained!")

# Evaluate
from sklearn.metrics import accuracy_score, classification_report

y_pred_xgb = xgb_model.predict(X_test)
acc_xgb = accuracy_score(y_test, y_pred_xgb)
print(f"   Test Accuracy: {acc_xgb*100:.2f}%")

# Step 6: Train LightGBM
print("\n🤖 Training LightGBM...")
import lightgbm as lgb

lgb_model = lgb.LGBMClassifier(
    n_estimators=300,
    max_depth=6,
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
    iterations=300,
    depth=6,
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

# Get probabilities
proba_xgb = xgb_model.predict_proba(X_test)
proba_lgb = lgb_model.predict_proba(X_test)
proba_cat = cat_model.predict_proba(X_test)

# Average
proba_ensemble = (proba_xgb + proba_lgb + proba_cat) / 3
y_pred_ensemble = np.argmax(proba_ensemble, axis=1)

acc_ensemble = accuracy_score(y_test, y_pred_ensemble)
print(f"   Ensemble Accuracy: {acc_ensemble*100:.2f}%")

# Detailed report
print("\n📊 Classification Report (Ensemble):")
print(classification_report(y_test, y_pred_ensemble, 
                          target_names=['NEUTRAL', 'LONG', 'SHORT']))

# Step 9: Save models
print("\n💾 Saving models...")

model_dir = '/Users/alifiyaa/Downloads/quantEngineHyperliquid/training/models/scalping'
os.makedirs(model_dir, exist_ok=True)

# Save XGBoost
xgb_model.save_model(f'{model_dir}/xgb_scalper.json')
print(f"   ✅ Saved: xgb_scalper.json")

# Save LightGBM
lgb_model.booster_.save_model(f'{model_dir}/lgb_scalper.txt')
print(f"   ✅ Saved: lgb_scalper.txt")

# Save CatBoost
cat_model.save_model(f'{model_dir}/cat_scalper.cbm')
print(f"   ✅ Saved: cat_scalper.cbm")

# Save feature names
import pickle
with open(f'{model_dir}/feature_names.pkl', 'wb') as f:
    pickle.dump(feature_cols, f)
print(f"   ✅ Saved: feature_names.pkl")

# Step 10: Analyze confidence distribution
print("\n📊 Confidence Distribution Analysis...")

# Get max probability for each prediction
max_proba = np.max(proba_ensemble, axis=1)

print(f"   Mean confidence: {np.mean(max_proba)*100:.1f}%")
print(f"   Median confidence: {np.median(max_proba)*100:.1f}%")
print(f"\n   Confidence bins:")
for threshold in [0.40, 0.45, 0.50, 0.55, 0.60]:
    count = np.sum(max_proba >= threshold)
    pct = count / len(max_proba) * 100
    print(f"      >={threshold*100:.0f}%: {count:,} samples ({pct:.1f}%)")

# Analyze win rate by confidence
print(f"\n   Win rate by confidence threshold:")
for threshold in [0.40, 0.45, 0.50, 0.55, 0.60]:
    mask = max_proba >= threshold
    if np.sum(mask) > 0:
        # Only look at LONG/SHORT predictions (not NEUTRAL)
        trade_mask = mask & (y_pred_ensemble != 0)
        if np.sum(trade_mask) > 0:
            correct = np.sum(y_test[trade_mask] == y_pred_ensemble[trade_mask])
            total = np.sum(trade_mask)
            wr = correct / total * 100
            print(f"      >={threshold*100:.0f}%: {wr:.1f}% WR ({total:,} trades)")

print("\n✅ PHASE 2 STEP 2 COMPLETE!")
print("\n📝 Summary:")
print(f"   Models trained: XGBoost, LightGBM, CatBoost")
print(f"   Ensemble accuracy: {acc_ensemble*100:.2f}%")
print(f"   Models saved to: {model_dir}")
print(f"\n🎯 Next: Backtest with new models!")
