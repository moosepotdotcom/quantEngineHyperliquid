
import os
import sys
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import precision_score, recall_score, roc_auc_score
import logging

# Setup Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from research.mtf_feature_engineer import MTFFeatureGenerator

# Check for XGBoost
try:
    import xgboost as xgb
    USE_XGB = True
except ImportError:
    from sklearn.ensemble import RandomForestClassifier
    USE_XGB = False

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

def create_labels(df):
    """
    Target: 0.5% profit in next 24 bars (2 hours) with 0.5% stop.
    """
    horizon = 24
    profit_target = 0.005
    stop_loss = 0.005
    
    targets = []
    closes = df['close'].values
    highs = df['high'].values
    lows = df['low'].values
    
    for i in range(len(df) - horizon):
        entry = closes[i]
        tp = entry * (1 + profit_target)
        sl = entry * (1 - stop_loss)
        
        window_high = highs[i+1 : i+1+horizon]
        window_low = lows[i+1 : i+1+horizon]
        
        tp_hit = np.any(window_high >= tp)
        sl_hit = np.any(window_low <= sl)
        
        if tp_hit and not sl_hit:
            targets.append(1)
        elif tp_hit and sl_hit:
            if np.where(window_high >= tp)[0][0] < np.where(window_low <= sl)[0][0]:
                targets.append(1)
            else:
                targets.append(0)
        else:
            targets.append(0)
            
    targets.extend([0] * horizon)
    df['target'] = targets
    return df

def train_mtf_model():
    base_dir = os.path.join(os.path.dirname(__file__), '..', 'datasets')
    
    # Load Datas
    logger.info("📂 Loading MTF Datasets...")
    df_5m = pd.read_csv(os.path.join(base_dir, "BTCUSD-5m-max-data.csv"))
    df_15m = pd.read_csv(os.path.join(base_dir, "BTCUSD-15m-max-data.csv"))
    df_30m = pd.read_csv(os.path.join(base_dir, "BTCUSD-30m-max-data.csv"))
    
    # Standardize Datetime
    for df in [df_5m, df_15m, df_30m]:
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
        elif 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Generate Features
    logger.info("⚙️  fusing MTF Features...")
    gen = MTFFeatureGenerator(df_5m, df_15m, df_30m)
    df = gen.generate()
    
    # Create Labels
    logger.info("🏷️  Creating Labels (0.5% Target / 2H Horizon)...")
    df = create_labels(df)
    df.dropna(inplace=True)
    
    # Train Split
    features = [c for c in df.columns if c not in ['open', 'high', 'low', 'close', 'volume', 'target', 'dividends', 'stock splits', 'open_15m', 'close_15m', 'high_15m', 'low_15m', 'volume_15m', 'open_30m', 'close_30m']]
    X = df[features]
    y = df['target']
    
    logger.info(f"📊 Matrix Shape: {X.shape}")
    logger.info(f"🎯 Class Balance: {y.mean():.2%}")
    
    tscv = TimeSeriesSplit(n_splits=5)
    
    if USE_XGB:
        model = xgb.XGBClassifier(n_estimators=100, max_depth=6, learning_rate=0.05, n_jobs=-1)
    else:
        model = RandomForestClassifier(n_estimators=100, max_depth=8, n_jobs=-1)
        
    fold = 1
    scores = []
    
    for train_idx, test_idx in tscv.split(X):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        prec = precision_score(y_test, preds, zero_division=0)
        
        logger.info(f"Fold {fold} Precision: {prec:.2%}")
        scores.append(prec)
        fold += 1
        
    logger.info(f"🏆 Average Precision: {np.mean(scores):.2%}")
    
    # Final Train
    model.fit(X, y)
    save_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'scalp_mtf_xgb.pkl')
    joblib.dump(model, save_path)
    logger.info(f"💾 Saved Model to {save_path}")

if __name__ == "__main__":
    train_mtf_model()
