#!/usr/bin/env python3
"""
🏆 Winner Hunter - ML Model Training
Trains XGBoost/LightGBM/CatBoost to find trades with near-100% win rate.
"""

import os
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.metrics import precision_score, recall_score, f1_score, classification_report
import warnings
warnings.filterwarnings('ignore')

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')
os.makedirs(MODEL_DIR, exist_ok=True)

def create_labels(df, lookahead=12, tp_pct=0.02, sl_pct=0.01):
    """
    Create labels for supervised learning.
    Label = 1 if price hits TP before SL within lookahead bars.
    Label = 0 otherwise.
    """
    labels = []
    closes = df['close'].values
    highs = df['high'].values
    lows = df['low'].values
    
    for i in range(len(df) - lookahead):
        entry_price = closes[i]
        tp_price = entry_price * (1 + tp_pct)
        sl_price = entry_price * (1 - sl_pct)
        
        outcome = 0  # Default: No win
        
        for j in range(1, lookahead + 1):
            if i + j >= len(highs):
                break
            future_high = highs[i + j]
            future_low = lows[i + j]
            
            # Check SL first (conservative)
            if future_low <= sl_price:
                outcome = 0
                break
            # Check TP
            if future_high >= tp_price:
                outcome = 1
                break
        
        labels.append(outcome)
    
    return labels

def train_winner_hunter(timeframe='15m', lookahead=12, tp_pct=0.02, sl_pct=0.01):
    """Train a precision-optimized model for finding winners"""
    
    print(f"\n🏆 Training Winner Hunter on {timeframe} data...")
    print(f"   TP: +{tp_pct*100:.1f}% | SL: -{sl_pct*100:.1f}% | Lookahead: {lookahead} bars")
    
    # Load Feature Data
    filepath = os.path.join(DATA_DIR, f'BTC_{timeframe}_features.csv')
    if not os.path.exists(filepath):
        print(f"❌ Data not found: {filepath}")
        return None
    
    df = pd.read_csv(filepath)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Create Labels
    print("   🏷️ Labeling data...")
    labels = create_labels(df, lookahead, tp_pct, sl_pct)
    df = df.iloc[:-lookahead].copy()
    df['target'] = labels
    
    # Drop NaN rows
    df.dropna(inplace=True)
    
    # Feature Selection
    exclude_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'target']
    feature_cols = [c for c in df.columns if c not in exclude_cols]
    
    X = df[feature_cols]
    y = df['target']
    
    print(f"   📊 Dataset: {len(X)} samples | Win Rate: {y.mean():.2%}")
    
    # Time-Series Split
    tscv = TimeSeriesSplit(n_splits=5)
    
    # XGBoost with Precision Focus
    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=5,
        gamma=0.1,
        scale_pos_weight=1,  # Will adjust below
        eval_metric='logloss',
        use_label_encoder=False
    )
    
    # Calculate class weight to balance
    neg_count = (y == 0).sum()
    pos_count = (y == 1).sum()
    model.set_params(scale_pos_weight=neg_count/pos_count)
    
    # Cross-validation
    print("   🔄 Cross-validating...")
    scores = []
    precisions = []
    
    for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        
        model.fit(X_train, y_train, verbose=False)
        
        preds = model.predict(X_test)
        probs = model.predict_proba(X_test)[:, 1]
        
        # Calculate precision at different thresholds
        for thresh in [0.5, 0.7, 0.8, 0.9]:
            preds_thresh = (probs >= thresh).astype(int)
            if preds_thresh.sum() > 0:
                prec = precision_score(y_test, preds_thresh, zero_division=0)
                count = preds_thresh.sum()
                precisions.append({'fold': fold, 'thresh': thresh, 'precision': prec, 'count': count})
    
    # Show precision results
    prec_df = pd.DataFrame(precisions)
    print("\n   📈 Precision by Threshold:")
    for thresh in [0.5, 0.7, 0.8, 0.9]:
        subset = prec_df[prec_df['thresh'] == thresh]
        avg_prec = subset['precision'].mean()
        avg_count = subset['count'].mean()
        print(f"      Thresh {thresh:.0%}: Precision={avg_prec:.2%} | Trades={avg_count:.1f}")
    
    # Train final model on all data
    print("\n   🎓 Training final model...")
    model.fit(X, y, verbose=False)
    
    # Save model
    model_name = f'winner_hunter_{timeframe}'
    model_path = os.path.join(MODEL_DIR, f'{model_name}.json')
    model.save_model(model_path)
    print(f"   ✅ Model saved: {model_path}")
    
    # Feature importance
    importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("\n   🌟 Top 10 Features:")
    for i, row in importance.head(10).iterrows():
        print(f"      {row['feature']}: {row['importance']:.4f}")
    
    return model, feature_cols

def train_multi_timeframe():
    """Train models on multiple timeframes and find the best"""
    
    print("="*60)
    print("🚀 MULTI-TIMEFRAME WINNER HUNTING")
    print("="*60)
    
    timeframes = ['5m', '15m', '30m', '1h']
    results = {}
    
    for tf in timeframes:
        model, features = train_winner_hunter(
            timeframe=tf,
            lookahead=12,
            tp_pct=0.015,  # 1.5% target
            sl_pct=0.008   # 0.8% stop
        )
        if model:
            results[tf] = {'model': model, 'features': features}
    
    print("\n" + "="*60)
    print("🎉 TRAINING COMPLETE!")
    print("="*60)
    
    return results

if __name__ == '__main__':
    train_multi_timeframe()
