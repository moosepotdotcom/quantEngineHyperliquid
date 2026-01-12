#!/usr/bin/env python3
"""
⚡ MTF Scalper Trainer
Trains a high-frequency scalper using 1m data with 5m/15m context.
Target: Quick profits (0.5-1.0%) with high win rate.
"""

import os
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import precision_score
import warnings
warnings.filterwarnings('ignore')

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')
os.makedirs(MODEL_DIR, exist_ok=True)

def create_scalper_labels(df, lookahead=10, tp_pct=0.003, sl_pct=0.002):
    """
    Create labels for scalping (faster, smaller targets).
    Lookahead: 10 bars (10 minutes on 1m chart)
    TP: 0.3% | SL: 0.2%
    """
    labels = []
    closes = df['close'].values
    highs = df['high'].values
    lows = df['low'].values
    
    for i in range(len(df) - lookahead):
        entry_price = closes[i]
        tp_price = entry_price * (1 + tp_pct)
        sl_price = entry_price * (1 - sl_pct)
        
        outcome = 0
        
        for j in range(1, lookahead + 1):
            if i + j >= len(highs):
                break
            future_high = highs[i + j]
            future_low = lows[i + j]
            
            if future_low <= sl_price:
                outcome = 0
                break
            if future_high >= tp_price:
                outcome = 1
                break
        
        labels.append(outcome)
    
    return labels

def train_mtf_scalper():
    """Train MTF Scalper model"""
    
    print("="*60)
    print("⚡ TRAINING MTF SCALPER")
    print("="*60)
    
    # Load MTF data
    data_path = os.path.join(DATA_DIR, 'BTC_MTF_scalper.csv')
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    print(f"\n📊 Dataset: {len(df)} bars")
    
    # Create labels
    print("🏷️ Labeling for scalping (TP: 0.3%, SL: 0.2%, Lookahead: 10min)...")
    labels = create_scalper_labels(df, lookahead=10, tp_pct=0.003, sl_pct=0.002)
    
    df = df.iloc[:-10].copy()
    df['target'] = labels
    df.dropna(inplace=True)
    
    # Feature selection
    exclude_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'target']
    feature_cols = [c for c in df.columns if c not in exclude_cols]
    
    X = df[feature_cols]
    y = df['target']
    
    print(f"📈 Features: {len(feature_cols)}")
    print(f"📊 Samples: {len(X)} | Base Win Rate: {y.mean():.2%}")
    
    # Train/Test Split (time-series)
    split = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]
    
    # XGBoost optimized for scalping
    model = xgb.XGBClassifier(
        n_estimators=400,
        max_depth=7,
        learning_rate=0.02,
        subsample=0.85,
        colsample_bytree=0.85,
        min_child_weight=3,
        gamma=0.05,
        scale_pos_weight=(y_train == 0).sum() / (y_train == 1).sum(),
        eval_metric='logloss',
        use_label_encoder=False
    )
    
    print("\n🎓 Training model...")
    model.fit(X_train, y_train, verbose=False)
    
    # Evaluate
    train_score = model.score(X_train, y_train)
    test_score = model.score(X_test, y_test)
    
    print(f"✅ Train Accuracy: {train_score:.2%}")
    print(f"✅ Test Accuracy: {test_score:.2%}")
    
    # Precision at different thresholds
    probs_test = model.predict_proba(X_test)[:, 1]
    
    print("\n📈 Precision by Threshold:")
    for thresh in [0.5, 0.7, 0.8, 0.9, 0.95]:
        preds = (probs_test >= thresh).astype(int)
        if preds.sum() > 0:
            prec = precision_score(y_test, preds, zero_division=0)
            count = preds.sum()
            print(f"   {thresh:.0%}: Precision={prec:.2%} | Signals={count}")
    
    # Save model
    model_path = os.path.join(MODEL_DIR, 'mtf_scalper.json')
    model.save_model(model_path)
    print(f"\n💾 Model saved: {model_path}")
    
    # Feature importance
    importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("\n🌟 Top 15 Features:")
    for i, row in importance.head(15).iterrows():
        print(f"   {row['feature']}: {row['importance']:.4f}")
    
    return model, feature_cols

if __name__ == '__main__':
    train_mtf_scalper()
