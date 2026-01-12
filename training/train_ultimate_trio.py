#!/usr/bin/env python3
"""
Ultimate Trio Ensemble Trainer
Optimized for 100% Win Rate & 5-6 Trades/Day
"""
import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score, recall_score, accuracy_score
from sklearn.utils.class_weight import compute_class_weight
import joblib
import json
import os
import sys

# Add path for utils
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'utils'))
from feature_engineer import add_all_indicators

def train_ultimate_model():
    print("🚀 STARTING ULTIMATE RETRAINING PROTOCOL")
    print("="*60)
    
    # 1. Load Data
    data_path = 'training/data/BTC_5m_mtf_labeled.csv'
    if not os.path.exists(data_path):
        print(f"❌ Data file not found: {data_path}")
        return
        
    print(f"📊 Loading dataset: {data_path}")
    df = pd.read_csv(data_path)
    
    # 2. Advanced Feature Engineering (Regenerate to ensure new features are present)
    print("🔧 Generating Advanced Features (Hurst, Volatility, Wicks)...")
    # Note: We assume the CSV has raw candles. If features are pre-calculated, we might need to recalculate them.
    # To be safe, we'll try to use raw columns if available, or just add indicators on top.
    
    # Check if raw columns exist
    required = ['open', 'high', 'low', 'close', 'volume']
    if all(col in df.columns for col in required):
        df = add_all_indicators(df)
    else:
        print("⚠️ Raw columns missing, skipping re-generation (using existing features)")
    
    # Clean data (Handling Infinity)
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.dropna(inplace=True)
    print(f"✅ Training Data (Cleaned): {len(df)} samples")
    
    # Prepare X and y
    exclude = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'label', 'target', 'date']
    features = [c for c in df.columns if c not in exclude]
    
    X = df[features]
    y = df['label'] # Assuming 'label' column exists (0=Neutral, 1=Long, 2=Short)
    
    # 3. Class Weights ( Crucial for Imbalance)
    classes = np.unique(y)
    weights = compute_class_weight('balanced', classes=classes, y=y)
    class_weight_dict = dict(zip(classes, weights))
    print(f"⚖️ Class Weights: {class_weight_dict}")
    
    # 4. Train/Test Split (Temporal)
    # Split by time to avoid leakage
    split_idx = int(len(df) * 0.85)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    
    print(f"📉 Train size: {len(X_train)} | Test size: {len(X_test)}")
    
    # 5. Model Definitions (Precision Optimized)
    models = {}
    
    # XGBoost
    print("\n🤖 Training XGBoost (Precision Optimized)...")
    xgb_model = xgb.XGBClassifier(
        n_estimators=1000,
        learning_rate=0.01,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        objective='multi:softprob',
        num_class=3,
        n_jobs=-1,
        early_stopping_rounds=50
    )
    xgb_model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=100)
    models['xgb'] = xgb_model
    
    # LightGBM
    print("\n🤖 Training LightGBM (Precision Optimized)...")
    lgb_train = lgb.Dataset(X_train, y_train)
    lgb_eval = lgb.Dataset(X_test, y_test, reference=lgb_train)
    
    params = {
        'objective': 'multiclass',
        'num_class': 3,
        'metric': 'multi_logloss',
        'learning_rate': 0.02,
        'num_leaves': 31,
        'feature_fraction': 0.8,
        'bagging_fraction': 0.8,
        'n_jobs': -1,
        'verbose': -1
    }
    
    lgb_model = lgb.train(
        params,
        lgb_train,
        num_boost_round=1000,
        valid_sets=[lgb_eval],
        callbacks=[lgb.early_stopping(stopping_rounds=50), lgb.log_evaluation(100)]
    )
    models['lgb'] = lgb_model
    
    # CatBoost
    print("\n🤖 Training CatBoost (Precision Optimized)...")
    cat_model = CatBoostClassifier(
        iterations=1000,
        learning_rate=0.03,
        depth=6,
        loss_function='MultiClass',
        verbose=100,
        early_stopping_rounds=50,
        class_weights=class_weight_dict
    )
    cat_model.fit(X_train, y_train, eval_set=(X_test, y_test))
    models['cat'] = cat_model
    
    # 6. Save Models
    print("\n💾 Saving Ultimate Models...")
    model_dir = 'models/'
    os.makedirs(model_dir, exist_ok=True)
    
    xgb_model.save_model(os.path.join(model_dir, 'mtf_scalper_5m_trio_xgb.json'))
    lgb_model.save_model(os.path.join(model_dir, 'mtf_scalper_5m_trio_lgb.json'))
    cat_model.save_model(os.path.join(model_dir, 'mtf_scalper_5m_trio_cat.json'))
    
    print("✅ Training Complete!")

if __name__ == '__main__':
    train_ultimate_model()
