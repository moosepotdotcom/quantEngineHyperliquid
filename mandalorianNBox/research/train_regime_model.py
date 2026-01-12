
"""
Regime Detection Model Training

Trains a classifier to detect market regimes:
- BULL: Uptrending market
- BEAR: Downtrending market  
- CHOP: Sideways/ranging market

Target: Regime over next 24 bars (2 hours)
"""

import os
import sys
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, classification_report
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from research.mtf_feature_engineer import MTFFeatureGenerator

try:
    import xgboost as xgb
    USE_XGB = True
except ImportError:
    from sklearn.ensemble import RandomForestClassifier
    USE_XGB = False

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def create_regime_labels(df, horizon=24, bull_threshold=0.01, bear_threshold=-0.01):
    """
    Create regime labels based on future price movement.
    
    0 = CHOP (between -1% and +1%)
    1 = BULL (> +1%)
    2 = BEAR (< -1%)
    """
    labels = []
    closes = df['close'].values
    
    for i in range(len(df) - horizon):
        current = closes[i]
        future = closes[i + horizon]
        
        pct_change = (future - current) / current
        
        if pct_change > bull_threshold:
            labels.append(1)  # BULL
        elif pct_change < bear_threshold:
            labels.append(2)  # BEAR
        else:
            labels.append(0)  # CHOP
    
    labels.extend([0] * horizon)  # Pad
    df['regime'] = labels
    return df


def train_regime_model():
    base_dir = os.path.join(os.path.dirname(__file__), '..', 'datasets')
    
    logger.info("=" * 60)
    logger.info("REGIME DETECTION MODEL TRAINING")
    logger.info("=" * 60)
    
    # Load Data
    logger.info("\n📂 Loading MTF Datasets...")
    df_5m = pd.read_csv(os.path.join(base_dir, "BTCUSD-5m-max-data.csv"))
    df_15m = pd.read_csv(os.path.join(base_dir, "BTCUSD-15m-max-data.csv"))
    df_30m = pd.read_csv(os.path.join(base_dir, "BTCUSD-30m-max-data.csv"))
    
    for df in [df_5m, df_15m, df_30m]:
        col = 'datetime' if 'datetime' in df.columns else 'timestamp'
        df[col] = pd.to_datetime(df[col])
    
    # Generate Features
    logger.info("⚙️  Fusing MTF Features...")
    gen = MTFFeatureGenerator(df_5m, df_15m, df_30m)
    df = gen.generate()
    
    # Create Labels
    logger.info("🏷️  Creating Regime Labels...")
    df = create_regime_labels(df)
    df.dropna(inplace=True)
    
    # Stats
    regime_counts = df['regime'].value_counts()
    logger.info(f"\n📊 REGIME DISTRIBUTION:")
    logger.info(f"   CHOP (0): {regime_counts.get(0, 0)} ({regime_counts.get(0, 0)/len(df)*100:.1f}%)")
    logger.info(f"   BULL (1): {regime_counts.get(1, 0)} ({regime_counts.get(1, 0)/len(df)*100:.1f}%)")
    logger.info(f"   BEAR (2): {regime_counts.get(2, 0)} ({regime_counts.get(2, 0)/len(df)*100:.1f}%)")
    
    # Prepare features
    cols_to_drop = ['open', 'high', 'low', 'close', 'volume', 'regime', 'dividends', 'stock splits']
    feature_cols = [c for c in df.columns if c not in cols_to_drop]
    X = df[feature_cols]
    y = df['regime']
    
    logger.info(f"   Feature Matrix: {X.shape}")
    
    # Train
    logger.info("\n" + "=" * 60)
    logger.info("🧠 TRAINING REGIME CLASSIFIER")
    logger.info("=" * 60)
    
    if USE_XGB:
        model = xgb.XGBClassifier(n_estimators=100, max_depth=6, learning_rate=0.05, n_jobs=-1, verbosity=0)
    else:
        model = RandomForestClassifier(n_estimators=100, max_depth=8, n_jobs=-1)
    
    tscv = TimeSeriesSplit(n_splits=5)
    accuracies = []
    
    for fold, (train_idx, test_idx) in enumerate(tscv.split(X), 1):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        acc = accuracy_score(y_test, preds)
        accuracies.append(acc)
        logger.info(f"   Fold {fold} Accuracy: {acc:.2%}")
    
    logger.info(f"\n   🏆 Avg Accuracy: {np.mean(accuracies):.2%}")
    
    # Final train
    model.fit(X, y)
    
    # Save
    models_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
    os.makedirs(models_dir, exist_ok=True)
    
    save_path = os.path.join(models_dir, 'regime_classifier.pkl')
    joblib.dump(model, save_path)
    
    logger.info(f"\n💾 Saved model to {save_path}")
    
    # Classification report
    logger.info("\n📋 Classification Report (Final):")
    preds = model.predict(X)
    print(classification_report(y, preds, target_names=['CHOP', 'BULL', 'BEAR']))
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ REGIME MODEL TRAINING COMPLETE!")
    logger.info("=" * 60)


if __name__ == "__main__":
    train_regime_model()
