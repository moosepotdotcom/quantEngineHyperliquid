#!/usr/bin/env python3
"""
ML Meta-Learner (XGBoost)
=========================
Trains an XGBoost model to filter trade signals for the Scalper.
Goal: Predict profitable entries (1% gain before 0.5% loss in 12 bars).

Workflow:
1. Load 15m data.
2. Generate base features (RSI, BB, etc.).
3. Label targets (Y).
4. Train XGBoost.
5. Save model.
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
try:
    import xgboost as xgb
    USE_XGB = True
except ImportError as e:
    logging.warning(f"⚠️ XGBoost import failed: {e}. Falling back to RandomForest.")
    USE_XGB = False
except Exception as e:
    logging.warning(f"⚠️ XGBoost init failed: {e}. Falling back to RandomForest.")
    USE_XGB = False

from sklearn.ensemble import RandomForestClassifier
import joblib
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import precision_score, recall_score, roc_auc_score

# Ensure project root is on sys.path for imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(PROJECT_ROOT)

try:
    from research.feature_generator import AdvancedFeatureGenerator
except Exception as e:
    logging.error(f"Failed to import AdvancedFeatureGenerator: {e}")
    raise

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def create_labels(df, forecast_horizon=12, profit_target=0.005, stop_loss=0.005):
    """
    Creates target labels for ML:
    1 = Profitable (Hit TP before SL within horizon)
    0 = Not Profitable (Hit SL first, or timed out)
    """
    logger.info("🏷️  Creating Labels (Horizon: %s bars, TP: %s, SL: %s)", forecast_horizon, profit_target, stop_loss)
    targets = []
    closes = df['close'].values
    highs = df['high'].values
    lows = df['low'].values
    
    for i in range(len(df) - forecast_horizon):
        entry_price = closes[i]
        tp_price = entry_price * (1 + profit_target)
        sl_price = entry_price * (1 - stop_loss)
        
        # Look forward
        window_highs = highs[i+1 : i+1+forecast_horizon]
        window_lows = lows[i+1 : i+1+forecast_horizon]
        
        # Check if TP hit
        tp_hit = np.any(window_highs >= tp_price)
        # Check if SL hit
        sl_hit = np.any(window_lows <= sl_price)
        
        if tp_hit and not sl_hit:
            targets.append(1)  # Clean win
        elif tp_hit and sl_hit:
            # Check which happened first
            tp_idx = np.where(window_highs >= tp_price)[0][0]
            sl_idx = np.where(window_lows <= sl_price)[0][0]
            if tp_idx < sl_idx:
                targets.append(1)
            else:
                targets.append(0)
        else:
            targets.append(0)
            
    # Pad the end
    targets.extend([0] * forecast_horizon)
    df['target'] = targets
    return df

def train_model(data_path):
    logger.info("🚀 Starting ML Training Pipeline")
    
    # 1. Load Data
    df = pd.read_csv(data_path)
    # Determine the correct datetime column name
    if "datetime" in df.columns:
        time_col = "datetime"
    elif "timestamp" in df.columns:
        time_col = "timestamp"
    else:
        time_col = "time"
    df[time_col] = pd.to_datetime(df[time_col])
    df.set_index(time_col, inplace=True)
    
    # 2. Feature Generation
    gen = AdvancedFeatureGenerator(df)
    df = gen.generate_all()
    
    # 3. Labeling
    df = create_labels(df)
    
    # 4. Prepare for Training
    # Drop rows with NaN (from indicators) and trailing rows without labels
    df.dropna(inplace=True)
    
    # Select Features (Exclude target and raw OHLCV from X)
    features = [c for c in df.columns if c not in ['open', 'high', 'low', 'close', 'volume', 'target', 'dividends', 'stock splits']]
    X = df[features]
    y = df['target']
    
    logger.info(f"📊 Training Data: {len(df)} samples, {len(features)} features")
    logger.info(f"🎯 Class Balance: {y.mean():.2%} profitable trades")
    
    # 5. Time Series Split Training
    tscv = TimeSeriesSplit(n_splits=5)
    
    if USE_XGB:
        logger.info("🌲 Training with XGBoost...")
        model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            objective='binary:logistic',
            eval_metric='logloss',
            n_jobs=-1
        )
    else:
        logger.info("🌳 Training with RandomForest...")
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10, # Limit depth to prevent overfit
            n_jobs=-1,
            random_state=42
        )
    
    fold = 1
    scores = []
    
    for train_index, test_index in tscv.split(X):
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y.iloc[train_index], y.iloc[test_index]
        
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        
        prec = precision_score(y_test, preds, zero_division=0)
        rec = recall_score(y_test, preds, zero_division=0)
        auc = roc_auc_score(y_test, preds)
        
        logger.info(f"Fold {fold}: Precision={prec:.2f}, Recall={rec:.2f}, AUC={auc:.2f}")
        scores.append(prec)
        fold += 1
        
    logger.info(f"🏆 Average Precision: {np.mean(scores):.2f}")
    
    # 6. Train on Full Data and Save
    model.fit(X, y)
    model_path = os.path.join(PROJECT_ROOT, "models", "scalp_xgb.pkl")
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(model, model_path)
    logger.info(f"💾 Model saved to {model_path}")
    
    # Feature Importance
    importance = pd.DataFrame({
        'feature': features,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("\n🔝 Top 10 Features:")
    print(importance.head(10))

if __name__ == "__main__":
    data_file = os.path.abspath(os.path.join(PROJECT_ROOT, "datasets", "BTCUSD-15m-max-data.csv"))
    if not os.path.exists(data_file):
        logger.error(f"Data file not found: {data_file}")
        sys.exit(1)
    train_model(data_file)
