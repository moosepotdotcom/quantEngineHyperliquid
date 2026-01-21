#!/usr/bin/env python3
"""
TRAIN BRAIN V7 MODELS
Ensemble: XGBoost + LightGBM + CatBoost
Data: Jan 2026 (Fresh)
Target: High Precision for V7 Targets (0.5% TP / 0.3% SL)
"""
import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score, precision_recall_curve
import json
import os
import sys

# Add utils path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def main():
    print("="*70)
    print("🧠 BRAIN V7 MODEL TRAINING")
    print("="*70)
    
    os.makedirs('models', exist_ok=True)
    
    # 1. Load Data
    print("\n📊 Loading V7 Dataset...")
    df = pd.read_csv('training/data/BTC_5m_jan2026_mtf_labeled.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    print(f"   Loaded {len(df):,} rows")
    
    # 2. Prepare
    exclude = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'label']
    feature_cols = [c for c in df.columns if c not in exclude]
    
    X = df[feature_cols].values
    y = df['label'].values
    
    # Clean
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    
    # Split (Chronological)
    train_size = int(len(X) * 0.70)
    val_size = int(len(X) * 0.15)
    
    X_train = X[:train_size]
    y_train = y[:train_size]
    
    X_val = X[train_size:train_size+val_size]
    y_val = y[train_size:train_size+val_size]
    
    X_test = X[train_size+val_size:]
    y_test = y[train_size+val_size:]
    
    print(f"   Train: {len(X_train)} | Val: {len(X_val)} | Test: {len(X_test)}")
    
    # 3. Training
    from sklearn.utils.class_weight import compute_class_weight
    class_weights = compute_class_weight('balanced', classes=np.unique(y_train), y=y_train)
    sample_weights = np.array([class_weights[int(label)] for label in y_train])
    
    # XGBoost
    print("\n🤖 Training XGBoost...")
    xgb_model = xgb.XGBClassifier(
        n_estimators=500, max_depth=6, learning_rate=0.03,
        subsample=0.8, colsample_bytree=0.8,
        objective='multi:softprob', num_class=3,
        random_state=42, n_jobs=-1, early_stopping_rounds=50
    )
    xgb_model.fit(X_train, y_train, sample_weight=sample_weights, eval_set=[(X_val, y_val)], verbose=False)
    
    # LightGBM
    print("🤖 Training LightGBM...")
    lgb_model = lgb.LGBMClassifier(
        n_estimators=800, max_depth=6, learning_rate=0.02,
        subsample=0.8, colsample_bytree=0.8,
        objective='multiclass', num_class=3,
        random_state=42, n_jobs=-1, class_weight='balanced'
    )
    lgb_model.fit(
        X_train, y_train, eval_set=[(X_val, y_val)],
        feature_name=feature_cols,
        callbacks=[lgb.early_stopping(50), lgb.log_evaluation(period=0)]
    )
    
    # CatBoost
    print("🤖 Training CatBoost...")
    cat_model = CatBoostClassifier(
        iterations=600, depth=6, learning_rate=0.03,
        loss_function='MultiClass', random_state=42,
        verbose=False, early_stopping_rounds=50,
        auto_class_weights='Balanced'
    )
    cat_model.fit(X_train, y_train, eval_set=(X_val, y_val))
    
    # 4. Evaluation & Threshold Optimization
    print("\n🎯 Optimizing Thresholds...")
    
    def get_ensemble_proba(X_data):
        p1 = xgb_model.predict_proba(X_data)
        p2 = lgb_model.predict_proba(X_data)
        p3 = cat_model.predict_proba(X_data)
        return (p1 + p2 + p3) / 3

    y_val_proba = get_ensemble_proba(X_val)
    
    # Precision-Recall Curve
    prec_l, rec_l, thresh_l = precision_recall_curve((y_val == 1).astype(int), y_val_proba[:, 1])
    prec_s, rec_s, thresh_s = precision_recall_curve((y_val == 2).astype(int), y_val_proba[:, 2])
    
    def find_best_threshold(prec, recall, thresh):
        # Target 80% Precision minimum, maximize recall
        mask = (prec[:-1] >= 0.80)
        if np.any(mask):
            idx = np.where(mask)[0]
            best_idx = idx[np.argmax(recall[idx])] # Max recall at >80% precision
            return float(thresh[best_idx]), float(prec[best_idx]), float(recall[best_idx])
        else:
            # Fallback: Max precision
            best_idx = np.argmax(prec[:-1])
            return float(thresh[best_idx]), float(prec[best_idx]), float(recall[best_idx])

    th_long, p_long, r_long = find_best_threshold(prec_l, rec_l, thresh_l)
    th_short, p_short, r_short = find_best_threshold(prec_s, rec_s, thresh_s)
    
    print(f"   🏆 Long Threshold: {th_long:.4f} (Prec: {p_long:.1%}, Rec: {r_long:.1%})")
    print(f"   🏆 Short Threshold: {th_short:.4f} (Prec: {p_short:.1%}, Rec: {r_short:.1%})")
    
    # 5. Save
    print("\n💾 Saving Brain V7 Models...")
    prefix = 'models/brain_v7_'
    
    xgb_model.save_model(f'{prefix}xgb.json')
    lgb_model.booster_.save_model(f'{prefix}lgb.json')
    cat_model.save_model(f'{prefix}cat.json')
    
    metadata = {
        'model': 'Brain V7 Trio',
        'train_date': pd.Timestamp.now().strftime('%Y-%m-%d'),
        'thresholds': {
            'long': th_long,
            'short': th_short
        },
        'metrics': {
            'long_prec': p_long,
            'short_prec': p_short,
            'long_recall': r_long,
            'short_recall': r_short
        },
        'features': feature_cols
    }
    
    with open(f'{prefix}metadata.json', 'w') as f:
        json.dump(metadata, f, indent=4)
        
    print(f"   ✅ Saved to {prefix}*")
    
    # 6. Test Set verify
    print("\n📊 Out-Of-Sample Test:")
    y_test_proba = get_ensemble_proba(X_test)
    test_longs = np.sum(y_test_proba[:, 1] >= th_long)
    test_shorts = np.sum(y_test_proba[:, 2] >= th_short)
    
    # Measure actual accuracy on test set
    y_test_pred = np.zeros_like(y_test)
    y_test_pred[y_test_proba[:, 1] >= th_long] = 1
    y_test_pred[y_test_proba[:, 2] >= th_short] = 2 # Short overrides Long if both (rare)
    
    # Calculate precision on test set
    if test_longs > 0:
        correct_longs = np.sum((y_test_pred == 1) & (y_test == 1))
        print(f"   Long Precision (Test): {correct_longs/test_longs:.1%} ({correct_longs}/{test_longs})")
    else:
        print("   Long Precision (Test): N/A (0 signals)")
        
    if test_shorts > 0:
        correct_shorts = np.sum((y_test_pred == 2) & (y_test == 2))
        print(f"   Short Precision (Test): {correct_shorts/test_shorts:.1%} ({correct_shorts}/{test_shorts})")
    else:
        print("   Short Precision (Test): N/A (0 signals)")

if __name__ == "__main__":
    main()
