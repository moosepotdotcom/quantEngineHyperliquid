
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import joblib
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def train_v8_unified():
    print("🚀 Training V8 Unified Model...")
    
    # Load labeled data
    data_path = 'training/data/BTC_5m_2025_v8_labeled.csv'
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    print(f"   📊 Loaded {len(df)} labeled candles")
    
    # Filter to 2025 only (train on 2025, validate on 2026)
    df_train = df[df['timestamp'] < '2026-01-01'].copy()
    print(f"   📅 Training set: {len(df_train)} candles (2025)")
    
    # Prepare features
    drop_cols = ['timestamp', 'v8_label', 'target', 'open', 'high', 'low', 'close',
                 'taker_buy_base', 'taker_sell_base', 'future_high', 'future_low', 
                 'future_range_pct', 'prob_low', 'prob_high', 'jackpot_label']
    
    feature_cols = [c for c in df_train.columns if c not in drop_cols]
    
    X = df_train[feature_cols]
    y = df_train['v8_label']
    
    # Remove features that may not be available in all datasets
    exclude_features = [col for col in X.columns if 'taker_sell_base' in col or 'taker_buy_base' in col]
    if exclude_features:
        print(f"   ⚠️  Excluding {len(exclude_features)} incompatible features: {exclude_features}")
        X = X.drop(columns=exclude_features)
        feature_cols = [c for c in feature_cols if c not in exclude_features]
    
    print(f"   🧠 Final Features: {len(feature_cols)}")
    print(f"\n   📊 Label Distribution:")
    print(f"      Class 0 (Grid):    {(y==0).sum():5d} ({(y==0).mean():.1%})")
    print(f"      Class 1 (Long):    {(y==1).sum():5d} ({(y==1).mean():.1%})")
    print(f"      Class 2 (Short):   {(y==2).sum():5d} ({(y==2).mean():.1%})")
    print(f"      Class 3 (Neutral): {(y==3).sum():5d} ({(y==3).mean():.1%})")
    
    # Train/Val split (temporal)
    split_idx = int(len(X) * 0.8)
    X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]
    
    print(f"\n   🔄 Train: {len(X_train)}, Val: {len(X_val)}")
    
    # Handle class imbalance with scale_pos_weight
    class_counts = y_train.value_counts()
    max_count = class_counts.max()
    
    # Calculate weights for each class
    weights = {}
    for cls in [0, 1, 2, 3]:
        if cls in class_counts.index:
            weights[cls] = max_count / class_counts[cls]
        else:
            weights[cls] = 1.0
    
    # Apply sample weights
    sample_weights = y_train.map(weights)
    
    print(f"\n   ⚖️  Class Weights:")
    for cls in [0, 1, 2, 3]:
        print(f"      Class {cls}: {weights[cls]:.2f}")
    
    # Train XGBoost
    print(f"\n   🎯 Training XGBoost Multi-Class Classifier...")
    
    model = xgb.XGBClassifier(
        objective='multi:softprob',
        num_class=4,
        n_estimators=300,
        max_depth=6,
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
    print(f"\n   📊 Validation Results:")
    y_pred = model.predict(X_val)
    
    print("\n   Classification Report:")
    print(classification_report(y_val, y_pred, 
                                target_names=['Grid', 'Long', 'Short', 'Neutral']))
    
    print("\n   Confusion Matrix:")
    print(confusion_matrix(y_val, y_pred))
    
    # Feature importance
    print(f"\n   🔑 Top 10 Features:")
    importances = pd.Series(model.feature_importances_, index=feature_cols).sort_values(ascending=False)
    print(importances.head(10))
    
    # Save model
    output_dir = 'model_engines/v8_unified/weights'
    os.makedirs(output_dir, exist_ok=True)
    model_path = os.path.join(output_dir, 'v8_unified.pkl')
    joblib.dump(model, model_path)
    print(f"\n   ✅ Model saved to {model_path}")
    
    # Save feature names
    feature_path = os.path.join(output_dir, 'feature_names.txt')
    with open(feature_path, 'w') as f:
        f.write('\n'.join(feature_cols))
    print(f"   ✅ Features saved to {feature_path}")
    
    return model

if __name__ == "__main__":
    train_v8_unified()
