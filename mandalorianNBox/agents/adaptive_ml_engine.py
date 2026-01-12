
"""
Adaptive ML Engine

A self-retraining ML engine that continuously adapts to market conditions
by retraining on rolling 5-10 day windows of recent data.

Features:
- Runs in parallel to main trading loop
- Retrains every 6 hours (configurable)
- Uses last 5-10 days of 5m data
- Automatically saves new model for hot-swap
- Tracks probability distribution drift
"""

import os
import sys
import time
import threading
import pandas as pd
import numpy as np
import joblib
from datetime import datetime, timedelta
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.loader import DataLoader
from research.mtf_feature_engineer import MTFFeatureGenerator

# XGBoost import
try:
    import xgboost as xgb
    USE_XGB = True
except ImportError:
    from sklearn.ensemble import RandomForestClassifier
    USE_XGB = False

from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import precision_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)


class AdaptiveMLEngine:
    """
    Self-adapting ML engine that retrains on rolling windows.
    """
    
    def __init__(self, retrain_interval_hours=6, lookback_days=5):
        self.retrain_interval = retrain_interval_hours * 3600  # seconds
        self.lookback_days = lookback_days
        self.model_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'scalp_adaptive.pkl')
        self.metrics_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'adaptive_metrics.json')
        self.running = False
        self.thread = None
        self.last_train_time = None
        self.last_precision = 0.0
        self.probability_history = []
        
    def create_labels(self, df, horizon=24, profit_target=0.005, stop_loss=0.005):
        """Create binary labels for profitable entries."""
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
            
            tp_hit_idx = np.where(window_high >= tp)[0]
            sl_hit_idx = np.where(window_low <= sl)[0]
            
            first_tp = tp_hit_idx[0] if len(tp_hit_idx) > 0 else 9999
            first_sl = sl_hit_idx[0] if len(sl_hit_idx) > 0 else 9999
            
            if first_tp < first_sl:
                targets.append(1)
            else:
                targets.append(0)
                
        targets.extend([0] * horizon)
        df['target'] = targets
        return df
    
    def retrain(self):
        """Fetch latest data and retrain the model."""
        logger.info("🔄 ADAPTIVE ENGINE: Starting retrain cycle...")
        
        try:
            # 1. Fetch fresh data
            logger.info(f"   📥 Fetching last {self.lookback_days} days of MTF data...")
            
            df_5m = DataLoader.fetch_yfinance("BTC-USD", period=f"{self.lookback_days}d", interval="5m", quiet=True)
            df_15m = DataLoader.fetch_yfinance("BTC-USD", period=f"{self.lookback_days * 3}d", interval="15m", quiet=True)
            df_30m = DataLoader.fetch_yfinance("BTC-USD", period=f"{self.lookback_days * 6}d", interval="30m", quiet=True)
            
            if df_5m.empty or df_15m.empty or df_30m.empty:
                logger.warning("   ⚠️ Empty data, skipping retrain")
                return
            
            logger.info(f"   📊 Data: 5m={len(df_5m)}, 15m={len(df_15m)}, 30m={len(df_30m)}")
            
            # 2. Generate MTF Features
            gen = MTFFeatureGenerator(df_5m, df_15m, df_30m)
            df = gen.generate()
            
            # 3. Create Labels
            df = self.create_labels(df)
            df.dropna(inplace=True)
            
            # 4. Prepare training data
            cols_to_drop = ['open', 'high', 'low', 'close', 'volume', 'target', 'dividends', 'stock splits']
            feature_cols = [c for c in df.columns if c not in cols_to_drop]
            X = df[feature_cols]
            y = df['target']
            
            logger.info(f"   📈 Matrix: {X.shape}, Class Balance: {y.mean():.2%}")
            
            # 5. Train with Time Series CV
            if USE_XGB:
                model = xgb.XGBClassifier(n_estimators=100, max_depth=6, learning_rate=0.05, n_jobs=-1, verbosity=0)
            else:
                model = RandomForestClassifier(n_estimators=100, max_depth=8, n_jobs=-1)
            
            tscv = TimeSeriesSplit(n_splits=3)
            precisions = []
            
            for train_idx, test_idx in tscv.split(X):
                X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
                y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
                
                model.fit(X_train, y_train)
                preds = model.predict(X_test)
                prec = precision_score(y_test, preds, zero_division=0)
                precisions.append(prec)
            
            avg_precision = np.mean(precisions)
            logger.info(f"   🎯 Avg Precision: {avg_precision:.2%}")
            
            # 6. Final train on all data
            model.fit(X, y)
            
            # 7. Save model
            joblib.dump(model, self.model_path)
            self.last_train_time = datetime.now()
            self.last_precision = avg_precision
            
            # 8. Analyze current probability distribution
            probs = model.predict_proba(X.iloc[-100:])[:, 1]
            self.probability_history.append({
                'time': datetime.now().isoformat(),
                'min': float(probs.min()),
                'max': float(probs.max()),
                'mean': float(probs.mean()),
                'precision': float(avg_precision)
            })
            
            # Keep only last 24 entries
            self.probability_history = self.probability_history[-24:]
            
            # Save metrics
            import json
            with open(self.metrics_path, 'w') as f:
                json.dump({
                    'last_train': self.last_train_time.isoformat(),
                    'precision': avg_precision,
                    'lookback_days': self.lookback_days,
                    'history': self.probability_history
                }, f, indent=2)
            
            logger.info(f"   💾 Model saved to {self.model_path}")
            logger.info(f"   📊 Prob Range: {probs.min():.3f} - {probs.max():.3f}")
            logger.info("   ✅ Retrain complete!")
            
        except Exception as e:
            logger.error(f"   ❌ Retrain error: {e}")
            import traceback
            traceback.print_exc()
    
    def _run_loop(self):
        """Background thread loop."""
        while self.running:
            self.retrain()
            logger.info(f"💤 Sleeping {self.retrain_interval/3600:.1f}h until next retrain...")
            time.sleep(self.retrain_interval)
    
    def start(self):
        """Start the adaptive engine in background."""
        if self.running:
            logger.warning("Adaptive engine already running")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("🚀 ADAPTIVE ML ENGINE STARTED (Background Thread)")
    
    def stop(self):
        """Stop the adaptive engine."""
        self.running = False
        logger.info("🛑 ADAPTIVE ML ENGINE STOPPED")
    
    def get_status(self):
        """Get current status."""
        return {
            'running': self.running,
            'last_train': self.last_train_time.isoformat() if self.last_train_time else None,
            'last_precision': self.last_precision,
            'lookback_days': self.lookback_days,
            'retrain_interval_hours': self.retrain_interval / 3600
        }


# For standalone testing
if __name__ == "__main__":
    engine = AdaptiveMLEngine(retrain_interval_hours=0.1, lookback_days=5)  # 6 min for testing
    engine.retrain()  # Run once immediately
    print("\n" + "=" * 50)
    print("Status:", engine.get_status())
