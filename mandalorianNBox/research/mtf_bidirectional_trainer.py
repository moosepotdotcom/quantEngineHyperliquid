
"""
Bidirectional MTF Meta-Learner

Trains TWO XGBoost models:
1. LONG Model - Predicts profitable long entries (price up 0.5% before down 0.5%)
2. SHORT Model - Predicts profitable short entries (price down 0.5% before up 0.5%)

This enables the bot to trade in BOTH bull and bear markets!
"""

import os
import sys
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import precision_score
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


def create_bidirectional_labels(df, horizon=24, profit_target=0.005, stop_loss=0.005):
    """
    Create labels for both LONG and SHORT profitable entries.
    
    LONG Target: Price goes UP 0.5% before going DOWN 0.5% within horizon
    SHORT Target: Price goes DOWN 0.5% before going UP 0.5% within horizon
    """
    long_targets = []
    short_targets = []
    
    closes = df['close'].values
    highs = df['high'].values
    lows = df['low'].values
    
    for i in range(len(df) - horizon):
        entry = closes[i]
        
        # LONG thresholds
        long_tp = entry * (1 + profit_target)
        long_sl = entry * (1 - stop_loss)
        
        # SHORT thresholds (inverted)
        short_tp = entry * (1 - profit_target)
        short_sl = entry * (1 + stop_loss)
        
        window_high = highs[i+1 : i+1+horizon]
        window_low = lows[i+1 : i+1+horizon]
        
        # LONG analysis
        long_tp_idx = np.where(window_high >= long_tp)[0]
        long_sl_idx = np.where(window_low <= long_sl)[0]
        first_long_tp = long_tp_idx[0] if len(long_tp_idx) > 0 else 9999
        first_long_sl = long_sl_idx[0] if len(long_sl_idx) > 0 else 9999
        
        if first_long_tp < first_long_sl:
            long_targets.append(1)
        else:
            long_targets.append(0)
        
        # SHORT analysis
        short_tp_idx = np.where(window_low <= short_tp)[0]
        short_sl_idx = np.where(window_high >= short_sl)[0]
        first_short_tp = short_tp_idx[0] if len(short_tp_idx) > 0 else 9999
        first_short_sl = short_sl_idx[0] if len(short_sl_idx) > 0 else 9999
        
        if first_short_tp < first_short_sl:
            short_targets.append(1)
        else:
            short_targets.append(0)
    
    # Pad remaining
    long_targets.extend([0] * horizon)
    short_targets.extend([0] * horizon)
    
    df['target_long'] = long_targets
    df['target_short'] = short_targets
    
    return df


def train_bidirectional_models():
    base_dir = os.path.join(os.path.dirname(__file__), '..', 'datasets')
    
    logger.info("=" * 60)
    logger.info("BIDIRECTIONAL MTF MODEL TRAINING (LONG + SHORT)")
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
    logger.info("🏷️  Creating Bidirectional Labels (0.5% TP / 0.5% SL / 2H Horizon)...")
    df = create_bidirectional_labels(df)
    df.dropna(inplace=True)
    
    # Stats
    logger.info(f"\n📊 LABEL DISTRIBUTION:")
    logger.info(f"   LONG Profitable:  {df['target_long'].mean():.2%}")
    logger.info(f"   SHORT Profitable: {df['target_short'].mean():.2%}")
    
    # Prepare features
    cols_to_drop = ['open', 'high', 'low', 'close', 'volume', 'target_long', 'target_short', 
                    'dividends', 'stock splits']
    feature_cols = [c for c in df.columns if c not in cols_to_drop]
    X = df[feature_cols]
    
    logger.info(f"   Feature Matrix: {X.shape}")
    
    # Train LONG Model
    logger.info("\n" + "=" * 60)
    logger.info("🟢 TRAINING LONG MODEL")
    logger.info("=" * 60)
    
    y_long = df['target_long']
    
    if USE_XGB:
        model_long = xgb.XGBClassifier(n_estimators=100, max_depth=6, learning_rate=0.05, n_jobs=-1, verbosity=0)
    else:
        model_long = RandomForestClassifier(n_estimators=100, max_depth=8, n_jobs=-1)
    
    tscv = TimeSeriesSplit(n_splits=5)
    long_precisions = []
    
    for fold, (train_idx, test_idx) in enumerate(tscv.split(X), 1):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y_long.iloc[train_idx], y_long.iloc[test_idx]
        
        model_long.fit(X_train, y_train)
        preds = model_long.predict(X_test)
        prec = precision_score(y_test, preds, zero_division=0)
        long_precisions.append(prec)
        logger.info(f"   Fold {fold} Precision: {prec:.2%}")
    
    logger.info(f"   🏆 LONG Avg Precision: {np.mean(long_precisions):.2%}")
    
    # Final train LONG
    model_long.fit(X, y_long)
    
    # Train SHORT Model
    logger.info("\n" + "=" * 60)
    logger.info("🔴 TRAINING SHORT MODEL")
    logger.info("=" * 60)
    
    y_short = df['target_short']
    
    if USE_XGB:
        model_short = xgb.XGBClassifier(n_estimators=100, max_depth=6, learning_rate=0.05, n_jobs=-1, verbosity=0)
    else:
        model_short = RandomForestClassifier(n_estimators=100, max_depth=8, n_jobs=-1)
    
    short_precisions = []
    
    for fold, (train_idx, test_idx) in enumerate(tscv.split(X), 1):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y_short.iloc[train_idx], y_short.iloc[test_idx]
        
        model_short.fit(X_train, y_train)
        preds = model_short.predict(X_test)
        prec = precision_score(y_test, preds, zero_division=0)
        short_precisions.append(prec)
        logger.info(f"   Fold {fold} Precision: {prec:.2%}")
    
    logger.info(f"   🏆 SHORT Avg Precision: {np.mean(short_precisions):.2%}")
    
    # Final train SHORT
    model_short.fit(X, y_short)
    
    # Save Models
    models_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
    os.makedirs(models_dir, exist_ok=True)
    
    long_path = os.path.join(models_dir, 'scalp_mtf_long.pkl')
    short_path = os.path.join(models_dir, 'scalp_mtf_short.pkl')
    
    joblib.dump(model_long, long_path)
    joblib.dump(model_short, short_path)
    
    logger.info(f"\n💾 Saved LONG model to {long_path}")
    logger.info(f"💾 Saved SHORT model to {short_path}")
    
    # Analyze thresholds
    logger.info("\n" + "=" * 60)
    logger.info("📈 THRESHOLD ANALYSIS")
    logger.info("=" * 60)
    
    long_probs = model_long.predict_proba(X)[:, 1]
    short_probs = model_short.predict_proba(X)[:, 1]
    
    logger.info("\n🟢 LONG Model:")
    for t in [0.5, 0.6, 0.7, 0.75, 0.8]:
        preds = (long_probs >= t).astype(int)
        if preds.sum() > 0:
            prec = precision_score(y_long, preds, zero_division=0)
            trades = preds.sum()
            logger.info(f"   Threshold {t}: {prec:.2%} precision, {trades} trades")
    
    logger.info("\n🔴 SHORT Model:")
    for t in [0.5, 0.6, 0.7, 0.75, 0.8]:
        preds = (short_probs >= t).astype(int)
        if preds.sum() > 0:
            prec = precision_score(y_short, preds, zero_division=0)
            trades = preds.sum()
            logger.info(f"   Threshold {t}: {prec:.2%} precision, {trades} trades")
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ BIDIRECTIONAL TRAINING COMPLETE!")
    logger.info("=" * 60)


if __name__ == "__main__":
    train_bidirectional_models()
