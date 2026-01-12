#!/usr/bin/env python3
"""
⚡ MTF Scalper Trainer (5m Base)
High-frequency scalper using 5m data with 15m/1h context.
"""

import os
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import precision_score
import warnings
warnings.filterwarnings('ignore')

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')

def create_labels(df, lookahead=8, tp_pct=0.008, sl_pct=0.005):
    """Scalper labels: 0.8% TP, 0.5% SL, 8 bars (40min)"""
    labels = []
    for i in range(len(df) - lookahead):
        entry = df['close'].iloc[i]
        tp = entry * (1 + tp_pct)
        sl = entry * (1 - sl_pct)
        
        outcome = 0
        for j in range(1, lookahead + 1):
            if i + j >= len(df):
                break
            if df['low'].iloc[i + j] <= sl:
                outcome = 0
                break
            if df['high'].iloc[i + j] >= tp:
                outcome = 1
                break
        labels.append(outcome)
    return labels

def train_5m_scalper():
    print("="*60)
    print("⚡ TRAINING 5M MTF SCALPER")
    print("="*60)
    
    # Load data
    df = pd.read_csv(os.path.join(DATA_DIR, 'BTC_MTF_scalper_5m.csv'))
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Create labels
    print("\n🏷️ Labeling (TP: 0.8%, SL: 0.5%, Lookahead: 40min)...")
    labels = create_labels(df)
    df = df.iloc[:-8].copy()
    df['target'] = labels
    df.dropna(inplace=True)
    
    # Features
    exclude = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'target']
    features = [c for c in df.columns if c not in exclude]
    
    X = df[features]
    y = df['target']
    
    print(f"📊 Samples: {len(X)} | Base Win Rate: {y.mean():.2%}")
    
    # Train/Test split
    split = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]
    
    # XGBoost
    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=(y_train == 0).sum() / (y_train == 1).sum(),
        eval_metric='logloss',
        use_label_encoder=False
    )
    
    print("\n🎓 Training...")
    model.fit(X_train, y_train, verbose=False)
    
    print(f"✅ Train Acc: {model.score(X_train, y_train):.2%}")
    print(f"✅ Test Acc: {model.score(X_test, y_test):.2%}")
    
    # Precision analysis
    probs = model.predict_proba(X_test)[:, 1]
    print("\n📈 Precision by Threshold:")
    for thresh in [0.5, 0.7, 0.8, 0.9, 0.95]:
        preds = (probs >= thresh).astype(int)
        if preds.sum() > 0:
            prec = precision_score(y_test, preds, zero_division=0)
            print(f"   {thresh:.0%}: Precision={prec:.2%} | Signals={preds.sum()}")
    
    # Save
    model_path = os.path.join(MODEL_DIR, 'mtf_scalper_5m.json')
    model.save_model(model_path)
    print(f"\n💾 Saved: {model_path}")
    
    # Top features
    importance = pd.DataFrame({
        'feature': features,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("\n🌟 Top 10 Features:")
    for _, row in importance.head(10).iterrows():
        print(f"   {row['feature']}: {row['importance']:.4f}")
    
    return model

if __name__ == '__main__':
    train_5m_scalper()
