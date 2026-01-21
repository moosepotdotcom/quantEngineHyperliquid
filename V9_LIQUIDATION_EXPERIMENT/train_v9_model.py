#!/usr/bin/env python3
"""
V9 Model Training - Liquidation-Enhanced XGBoost
Trains on 2025 data with liquidation features
"""

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import joblib

def train_v9_model():
    print("🚀 V9 Model Training - Liquidation-Enhanced")
    print("="*70)
    
    # Load labeled data
    df = pd.read_csv('../training/data/BTC_5m_2025_v9_labeled.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    print(f"✅ Loaded {len(df)} labeled candles")
    
    # Feature selection - include liquidation features
    base_features = [
        'rsi_7', 'rsi_14', 'rsi_21',
        'ema_5', 'ema_10', 'ema_20', 'ema_50',
        'atr_7', 'atr_14', 'atr_21',
        'macd', 'macd_signal', 'macd_hist',
        'adx', 'adx_pos', 'adx_neg',
        'bb_high', 'bb_low', 'bb_mid', 'bb_width',
        'volume', 'obv', 'mfi',
        'cvd_1h', 'volume_delta',
        'hurst', 'atr_pct'
    ]
    
    # NEW: Liquidation features
    liq_features = [
        'liq_proxy_score',
        'liq_direction',
        'liq_cluster_count',
        'vol_surge',
        'wick_ratio',
        'is_vol_spike',
        'is_long_wick'
    ]
    
    feature_cols = base_features + liq_features
    
    # Filter available features
    available_features = [f for f in feature_cols if f in df.columns]
    print(f"\n📊 Using {len(available_features)} features (including {len([f for f in liq_features if f in available_features])} liquidation features)")
    
    # Prepare data
    X = df[available_features].fillna(0)
    y = df['v9_label']
    
    # Remap labels: 1→0 (Long), 2→1 (Short), 3→2 (Neutral)
    label_map = {1: 0, 2: 1, 3: 2}
    y = y.map(label_map)
    
    # Train/val split
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"\n📈 Training set: {len(X_train):,} samples")
    print(f"   Validation set: {len(X_val):,} samples")
    
    # Class weights (handle imbalance)
    class_counts = y_train.value_counts()
    max_count = class_counts.max()
    weights = {cls: max_count / class_counts[cls] for cls in class_counts.index}
    sample_weights = y_train.map(weights)
    
    print(f"\n⚖️  Class Weights:")
    for cls in sorted(weights.keys()):
        print(f"   Class {cls}: {weights[cls]:.2f}")
    
    # Train XGBoost
    print(f"\n🎯 Training V9 XGBoost Model...")
    
    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=8,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        eval_metric='mlogloss'
    )
    
    model.fit(
        X_train, y_train,
        sample_weight=sample_weights,
        eval_set=[(X_val, y_val)],
        verbose=50
    )
    
    # Evaluate
    print(f"\n📊 Validation Results:")
    y_pred = model.predict(X_val)
    
    print("\nClassification Report:")
    print(classification_report(y_val, y_pred, 
                                target_names=['Long', 'Short', 'Neutral'],
                                labels=[1, 2, 3]))
    
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_val, y_pred, labels=[1, 2, 3]))
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': available_features,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print(f"\n🔝 Top 15 Features:")
    print(feature_importance.head(15).to_string(index=False))
    
    # Check liquidation feature importance
    liq_importance = feature_importance[feature_importance['feature'].isin(liq_features)]
    if len(liq_importance) > 0:
        print(f"\n💥 Liquidation Feature Importance:")
        print(liq_importance.to_string(index=False))
    
    # Save model
    model_path = 'v9_liquidation_model.pkl'
    joblib.dump(model, model_path)
    print(f"\n💾 Model saved to {model_path}")
    
    # Save feature names
    with open('v9_feature_names.txt', 'w') as f:
        for feat in available_features:
            f.write(f"{feat}\n")
    print(f"   Features saved to v9_feature_names.txt")
    
    return model, available_features

if __name__ == "__main__":
    model, features = train_v9_model()
