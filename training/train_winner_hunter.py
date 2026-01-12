#!/usr/bin/env python3
"""
Train Winner Hunter (1H) model with "The Trio" (XGBoost, LightGBM, CatBoost)
Focusing on maximum precision (Targeting 100% Win Rate)
"""
import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
from sklearn.model_selection import train_test_split
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import classification_report, roc_auc_score, precision_recall_curve
import matplotlib.pyplot as plt
import json
import pickle
import os

def main():
    print("="*70)
    print("🏆 WINNER HUNTER (1H) - THE TRIO TRAINING")
    print("="*70)
    
    # Create models directory (root level)
    os.makedirs('models', exist_ok=True)
    
    # Load labeled data
    print("\n📊 Loading labeled data...")
    df = pd.read_csv('training/data/BTC_1h_labeled.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    print(f"   Loaded {len(df):,} rows")
    
    # Prepare features and labels
    print("\n🔧 Preparing features and labels...")
    exclude = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'label']
    feature_cols = [c for c in df.columns if c not in exclude]
    
    X = df[feature_cols].values
    y = df['label'].values
    
    # Clean data - replace inf and NaN
    print("   Cleaning data (replacing inf/NaN with 0)...")
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    
    print(f"   Features: {len(feature_cols)}")
    print(f"   Samples: {len(X):,}")
    
    # Class distribution
    unique, counts = np.unique(y, return_counts=True)
    print(f"   Class Distribution:")
    for cls, cnt in zip(unique, counts):
        cls_name = ['Neutral', 'Long', 'Short'][int(cls)]
        print(f"      {cls_name} ({cls}): {cnt:,} ({cnt/len(y)*100:.2f}%)")
    
    # Split data (chronological)
    print("\n📊 Splitting data (chronological)...")
    train_size = int(len(X) * 0.70)
    val_size = int(len(X) * 0.15)
    
    X_train = X[:train_size]
    y_train = y[:train_size]
    
    X_val = X[train_size:train_size+val_size]
    y_val = y[train_size:train_size+val_size]
    
    X_test = X[train_size+val_size:]
    y_test = y[train_size+val_size:]
    
    print(f"   Train: {len(X_train):,} samples")
    print(f"   Val:   {len(X_val):,} samples")
    print(f"   Test:  {len(X_test):,} samples")
    
    # --- 1. XGBoost ---
    print("\n🤖 Training 1/3: XGBoost...")
    from sklearn.utils.class_weight import compute_class_weight
    
    # Compute class weights for imbalanced data
    class_weights = compute_class_weight('balanced', classes=np.unique(y_train), y=y_train)
    sample_weights = np.array([class_weights[int(label)] for label in y_train])
    
    xgb_model = xgb.XGBClassifier(
        n_estimators=600,
        max_depth=7,
        learning_rate=0.03,
        subsample=0.85,
        colsample_bytree=0.85,
        objective='multi:softprob',
        num_class=3,
        random_state=42,
        n_jobs=-1,
        early_stopping_rounds=50
    )
    xgb_model.fit(X_train, y_train, sample_weight=sample_weights, eval_set=[(X_val, y_val)], verbose=False)
    
    # --- 2. LightGBM ---
    print("🤖 Training 2/3: LightGBM...")
    lgb_model = lgb.LGBMClassifier(
        n_estimators=1000,
        max_depth=7,
        learning_rate=0.02,
        subsample=0.85,
        colsample_bytree=0.85,
        objective='multiclass',
        num_class=3,
        random_state=42,
        n_jobs=-1,
        importance_type='gain',
        class_weight='balanced'
    )
    # Using feature names to avoid warnings
    lgb_model.fit(
        X_train, y_train, 
        eval_set=[(X_val, y_val)], 
        feature_name=feature_cols,
        callbacks=[lgb.early_stopping(100), lgb.log_evaluation(period=0)]
    )
    
    # --- 3. CatBoost ---
    print("🤖 Training 3/3: CatBoost...")
    cat_model = CatBoostClassifier(
        iterations=700,
        depth=7,
        learning_rate=0.03,
        loss_function='MultiClass',
        random_state=42,
        verbose=False,
        early_stopping_rounds=50,
        auto_class_weights='Balanced'
    )
    cat_model.fit(X_train, y_train, eval_set=(X_val, y_val))
    
    print(f"   ✅ All models trained!")
    
    # --- Ensemble Validation ---
    print("\n🎯 Evaluating Ensemble (Consensus)...")
    
    def get_ensemble_proba(X_data):
        # Returns [prob_class0, prob_class1, prob_class2]
        p1 = xgb_model.predict_proba(X_data)
        p2 = lgb_model.predict_proba(X_data)
        p3 = cat_model.predict_proba(X_data)
        return (p1 + p2 + p3) / 3

    y_val_proba = get_ensemble_proba(X_val)
    
    # Find thresholds for maximum precision (Long = Class 1)
    precisions_l, recalls_l, thresholds_l = precision_recall_curve((y_val == 1).astype(int), y_val_proba[:, 1])
    # Find thresholds for maximum precision (Short = Class 2)
    precisions_s, recalls_s, thresholds_s = precision_recall_curve((y_val == 2).astype(int), y_val_proba[:, 2])
    
    def find_best_threshold(prec, recall, thresh, target_name):
        high_precision_mask = (prec[:-1] >= 0.95) # Lowered to 95% for dual direction complexity
        if np.any(high_precision_mask):
            idx = np.where(high_precision_mask)[0]
            best_idx = idx[np.argmax(recall[idx])]
            return float(thresh[best_idx]), float(prec[best_idx]), float(recall[best_idx])
        else:
            best_idx = np.argmax(prec[:-1])
            return float(thresh[best_idx]), float(prec[best_idx]), float(recall[best_idx])

    thresh_long, prec_long, recall_long = find_best_threshold(precisions_l, recalls_l, thresholds_l, "Long")
    thresh_short, prec_short, recall_short = find_best_threshold(precisions_s, recalls_s, thresholds_s, "Short")
    
    print(f"   🏆 Long Threshold:  {thresh_long:.4f} (Prec: {prec_long:.1%}, Recall: {recall_long:.2%})")
    print(f"   🏆 Short Threshold: {thresh_short:.4f} (Prec: {prec_short:.1%}, Recall: {recall_short:.2%})")

    # --- Save Models ---
    print("\n💾 Saving models to root models/ directory...")
    prefix = 'models/winner_hunter_1h_trio_'
    
    xgb_model.save_model(f'{prefix}xgb.json')
    lgb_model.booster_.save_model(f'{prefix}lgb.json')
    cat_model.save_model(f'{prefix}cat.json')
    print(f"   ✅ Saved XGBoost to {prefix}xgb.json")
    print(f"   ✅ Saved LightGBM to {prefix}lgb.json")
    print(f"   ✅ Saved CatBoost to {prefix}cat.json")
    
    # Save ensemble metadata
    metadata = {
        'model': 'Winner Hunter (1H) Trio Ensemble',
        'models': ['XGBoost', 'LightGBM', 'CatBoost'],
        'date_trained': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'),
        'feature_count': len(feature_cols),
        'target_precision_threshold_long': thresh_long,
        'target_precision_threshold_short': thresh_short,
        'expected_precision_long': prec_long,
        'expected_precision_short': prec_short,
        'val_auc': float(roc_auc_score(pd.get_dummies(y_val), y_val_proba, multi_class='ovr'))
    }
    
    with open(f'{prefix}metadata.json', 'w') as f:
        json.dump(metadata, f, indent=4)
        
    print(f"   ✅ All models and metadata saved to training/models/")

    # --- Final Test ---
    print("\n📊 Final Test Set Performance:")
    y_test_proba = get_ensemble_proba(X_test)
    
    long_trades = np.sum(y_test_proba[:, 1] >= thresh_long)
    short_trades = np.sum(y_test_proba[:, 2] >= thresh_short)
    
    print(f"   Test Longs identified:  {long_trades}")
    print(f"   Test Shorts identified: {short_trades}")

    print("\n" + "="*70)
    print("✅ WINNER HUNTER TRIO TRAINING COMPLETE")
    print("="*70)

if __name__ == '__main__':
    main()
