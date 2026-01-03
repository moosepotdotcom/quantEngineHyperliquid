#!/usr/bin/env python3
"""
Train Winner Hunter (1H) model with proper validation and calibration
"""
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import classification_report, roc_auc_score, precision_recall_curve
import matplotlib.pyplot as plt
import json

def main():
    print("="*70)
    print("🎯 MTF SCALPER (5M) MODEL TRAINING")
    print("="*70)
    
    # Load labeled data
    print("\n📊 Loading labeled data...")
    df = pd.read_csv('training/data/BTC_5m_mtf_labeled.csv')
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
    print(f"   Positive samples: {np.sum(y):,} ({np.sum(y)/len(y)*100:.2f}%)")
    
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
    
    print(f"   Train: {len(X_train):,} samples ({np.sum(y_train)/len(y_train)*100:.2f}% positive)")
    print(f"   Val:   {len(X_val):,} samples ({np.sum(y_val)/len(y_val)*100:.2f}% positive)")
    print(f"   Test:  {len(X_test):,} samples ({np.sum(y_test)/len(y_test)*100:.2f}% positive)")
    
    # Train XGBoost model
    print("\n🤖 Training XGBoost model...")
    
    # Calculate scale_pos_weight for class imbalance
    scale_pos_weight = len(y_train[y_train == 0]) / len(y_train[y_train == 1])
    print(f"   Scale pos weight: {scale_pos_weight:.2f}")
    
    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        n_jobs=-1,
        early_stopping_rounds=20
    )
    
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False
    )
    
    print(f"   ✅ Training complete!")
    print(f"   Best iteration: {model.best_iteration}")
    
    # Evaluate on validation set
    print("\n📊 Validation Set Performance:")
    y_val_pred = model.predict(X_val)
    y_val_proba = model.predict_proba(X_val)[:, 1]
    
    print(classification_report(y_val, y_val_pred, target_names=['Loss', 'Win']))
    print(f"   ROC AUC: {roc_auc_score(y_val, y_val_proba):.4f}")
    
    # Calibrate probabilities
    print("\n🎯 Calibrating probabilities...")
    calibrated_model = CalibratedClassifierCV(model, method='sigmoid', cv='prefit')
    calibrated_model.fit(X_val, y_val)
    print("   ✅ Calibration complete!")
    
    # Get calibrated probabilities
    y_val_proba_cal = calibrated_model.predict_proba(X_val)[:, 1]
    
    # Find optimal threshold
    print("\n🎯 Finding optimal threshold...")
    precisions, recalls, thresholds = precision_recall_curve(y_val, y_val_proba_cal)
    
    # Calculate F1 scores
    f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-10)
    optimal_idx = np.argmax(f1_scores)
    optimal_threshold = thresholds[optimal_idx]
    
    print(f"   Optimal threshold (max F1): {optimal_threshold:.4f}")
    print(f"   Precision at threshold: {precisions[optimal_idx]:.4f}")
    print(f"   Recall at threshold: {recalls[optimal_idx]:.4f}")
    print(f"   F1 score: {f1_scores[optimal_idx]:.4f}")
    
    # Find threshold for 90% precision
    precision_90_idx = np.where(precisions >= 0.90)[0]
    if len(precision_90_idx) > 0:
        threshold_90 = thresholds[precision_90_idx[0]]
        print(f"\n   Threshold for 90% precision: {threshold_90:.4f}")
        print(f"   Recall at 90% precision: {recalls[precision_90_idx[0]]:.4f}")
    
    # Analyze confidence distribution
    print("\n📊 Confidence Distribution (Validation Set):")
    print(f"   Mean: {np.mean(y_val_proba_cal):.4f}")
    print(f"   Median: {np.median(y_val_proba_cal):.4f}")
    print(f"   Min: {np.min(y_val_proba_cal):.4f}")
    print(f"   Max: {np.max(y_val_proba_cal):.4f}")
    print(f"   95th percentile: {np.percentile(y_val_proba_cal, 95):.4f}")
    
    # Count samples above various thresholds
    print("\n📊 Samples above thresholds:")
    for thresh in [0.05, 0.10, 0.15, 0.20, 0.30, 0.50, 0.70, 0.90]:
        count = np.sum(y_val_proba_cal >= thresh)
        pct = (count / len(y_val_proba_cal)) * 100
        print(f"   {thresh:.0%}: {count:,} samples ({pct:.2f}%)")
    
    # Save model
    print("\n💾 Saving model...")
    model_path = 'training/models/mtf_scalper_5m_v2.json'
    model.save_model(model_path)
    print(f"   ✅ Saved to {model_path}")
    
    # Save calibrated model (using pickle)
    import pickle
    calibrated_path = 'training/models/mtf_scalper_5m_v2_calibrated.pkl'
    with open(calibrated_path, 'wb') as f:
        pickle.dump(calibrated_model, f)
    print(f"   ✅ Saved calibrated model to {calibrated_path}")
    
    # Save metadata
    metadata = {
        'model': 'MTF Scalper (5M)',
        'version': 'v2',
        'train_samples': int(len(X_train)),
        'val_samples': int(len(X_val)),
        'test_samples': int(len(X_test)),
        'features': len(feature_cols),
        'win_rate_train': float(np.sum(y_train) / len(y_train)),
        'win_rate_val': float(np.sum(y_val) / len(y_val)),
        'optimal_threshold': float(optimal_threshold),
        'threshold_90_precision': float(threshold_90) if len(precision_90_idx) > 0 else None,
        'val_roc_auc': float(roc_auc_score(y_val, y_val_proba_cal)),
        'confidence_mean': float(np.mean(y_val_proba_cal)),
        'confidence_95th': float(np.percentile(y_val_proba_cal, 95))
    }
    
    metadata_path = 'training/models/mtf_scalper_5m_v2_metadata.json'
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"   ✅ Saved metadata to {metadata_path}")
    
    # Final summary
    print("\n" + "="*70)
    print("✅ MTF SCALPER TRAINING COMPLETE!")
    print("="*70)
    print(f"Model: {model_path}")
    print(f"Optimal threshold: {optimal_threshold:.4f}")
    print(f"Recommended threshold (90% precision): {threshold_90:.4f}" if len(precision_90_idx) > 0 else "")
    print("="*70)

if __name__ == '__main__':
    main()
