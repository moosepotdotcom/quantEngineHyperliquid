#!/usr/bin/env python3
"""
Online Learner - Incremental model updates with live trading data
"""
import os
import json
import pickle
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.calibration import CalibratedClassifierCV

class OnlineLearner:
    """
    Implements online learning with incremental XGBoost updates
    """
    
    def __init__(self, model_name: str, window_days: int = 30):
        """
        Initialize online learner
        
        Args:
            model_name: Name of model (winner_hunter_1h or mtf_scalper_5m)
            window_days: Number of days to keep in sliding window
        """
        self.model_name = model_name
        self.window_days = window_days
        self.model_dir = 'models'
        self.training_dir = 'training/online_learning'
        os.makedirs(self.training_dir, exist_ok=True)
        
        # Load current model
        self.current_model = None
        self.load_current_model()
        
        # Training history
        self.training_history = []
    
    def load_current_model(self):
        """Load the current production model"""
        model_path = os.path.join(self.model_dir, f'{self.model_name}_v2.json')
        if os.path.exists(model_path):
            self.current_model = xgb.XGBClassifier()
            self.current_model.load_model(model_path)
            print(f"✅ Loaded current model: {model_path}")
        else:
            print(f"⚠️ No current model found at {model_path}")
    
    def get_training_data(self, logger, min_samples: int = 100) -> Optional[pd.DataFrame]:
        """
        Get training data from logged trades
        
        Args:
            logger: TradeLogger instance
            min_samples: Minimum samples required
            
        Returns:
            DataFrame with features and labels, or None
        """
        # Get training data from logger
        df = logger.get_training_data(min_trades=min_samples)
        
        if df is None or len(df) < min_samples:
            print(f"⚠️ Insufficient data: {len(df) if df is not None else 0} samples (need {min_samples})")
            return None
        
        # Apply sliding window (last N days)
        cutoff_date = datetime.now() - timedelta(days=self.window_days)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df[df['timestamp'] >= cutoff_date]
        
        print(f"📊 Training data: {len(df)} samples from last {self.window_days} days")
        
        return df
    
    def train_incremental(self, df: pd.DataFrame) -> Tuple[xgb.XGBClassifier, Dict]:
        """
        Train model incrementally on new data
        
        Args:
            df: Training DataFrame with features and labels
            
        Returns:
            (new_model, metrics)
        """
        print(f"\n🤖 Training incremental model...")
        
        # Prepare data
        feature_cols = [c for c in df.columns if c not in ['label', 'pnl', 'timestamp', 'confidence']]
        X = df[feature_cols].values
        y = df['label'].values
        
        # Clean data
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        
        # Split for validation
        split_idx = int(len(X) * 0.8)
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        print(f"   Train: {len(X_train)} samples")
        print(f"   Val:   {len(X_val)} samples")
        
        # Calculate class weights
        scale_pos_weight = len(y_train[y_train == 0]) / len(y_train[y_train == 1])
        
        # Train new model
        model = xgb.XGBClassifier(
            n_estimators=100,  # Fewer trees for faster training
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_pos_weight,
            random_state=42,
            n_jobs=-1,
            early_stopping_rounds=10
        )
        
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False
        )
        
        # Evaluate
        y_val_pred = model.predict(X_val)
        y_val_proba = model.predict_proba(X_val)[:, 1]
        
        val_accuracy = np.mean(y_val_pred == y_val)
        val_win_rate = np.mean(y_val)
        
        # Calibrate
        print(f"\n🎯 Calibrating probabilities...")
        calibrated_model = CalibratedClassifierCV(model, method='sigmoid', cv='prefit')
        calibrated_model.fit(X_val, y_val)
        
        # Metrics
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'train_samples': len(X_train),
            'val_samples': len(X_val),
            'val_accuracy': float(val_accuracy),
            'val_win_rate': float(val_win_rate),
            'best_iteration': model.best_iteration
        }
        
        print(f"\n📊 Training Results:")
        print(f"   Accuracy: {val_accuracy:.2%}")
        print(f"   Win Rate: {val_win_rate:.2%}")
        print(f"   Best Iteration: {model.best_iteration}")
        
        return calibrated_model, metrics
    
    def should_update_model(self, new_metrics: Dict, threshold: float = 0.05) -> bool:
        """
        Determine if new model should replace current model
        
        Args:
            new_metrics: Metrics from new model
            threshold: Minimum improvement required (5%)
            
        Returns:
            True if should update
        """
        # If no training history, accept first model
        if not self.training_history:
            print("✅ First incremental model - accepting")
            return True
        
        # Compare with last model
        last_metrics = self.training_history[-1]
        last_accuracy = last_metrics.get('val_accuracy', 0)
        new_accuracy = new_metrics.get('val_accuracy', 0)
        
        improvement = new_accuracy - last_accuracy
        
        if improvement >= threshold:
            print(f"✅ Model improved by {improvement:.2%} - accepting")
            return True
        else:
            print(f"⚠️ Model improvement {improvement:.2%} below threshold {threshold:.2%} - rejecting")
            return False
    
    def save_model(self, model, metrics: Dict, version: str = None):
        """
        Save model with versioning
        
        Args:
            model: Trained model
            metrics: Training metrics
            version: Version string (auto-generated if None)
        """
        if version is None:
            version = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save model
        model_path = os.path.join(self.training_dir, f'{self.model_name}_v{version}.pkl')
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        print(f"💾 Saved model: {model_path}")
        
        # Save metrics
        metrics_path = os.path.join(self.training_dir, f'{self.model_name}_v{version}_metrics.json')
        with open(metrics_path, 'w') as f:
            json.dump(metrics, f, indent=2)
        print(f"💾 Saved metrics: {metrics_path}")
        
        # Update training history
        self.training_history.append({
            'version': version,
            'timestamp': metrics['timestamp'],
            'metrics': metrics
        })
        
        # Save history
        history_path = os.path.join(self.training_dir, f'{self.model_name}_history.json')
        with open(history_path, 'w') as f:
            json.dump(self.training_history, f, indent=2)
    
    def update_production_model(self, model, version: str):
        """
        Update production model (hot-swap)
        
        Args:
            model: New model to deploy
            version: Model version
        """
        # Extract base XGBoost model from calibrated wrapper
        if hasattr(model, 'estimator'):
            base_model = model.estimator
        else:
            base_model = model
        
        # Save to production path
        prod_path = os.path.join(self.model_dir, f'{self.model_name}_v2.json')
        base_model.save_model(prod_path)
        print(f"🚀 Updated production model: {prod_path}")
        
        # Save calibrated version
        calibrated_path = os.path.join(self.model_dir, f'{self.model_name}_v2_calibrated.pkl')
        with open(calibrated_path, 'wb') as f:
            pickle.dump(model, f)
        print(f"🚀 Updated calibrated model: {calibrated_path}")
    
    def run_incremental_update(self, logger, force: bool = False) -> bool:
        """
        Run full incremental update pipeline
        
        Args:
            logger: TradeLogger instance
            force: Force update even if improvement is small
            
        Returns:
            True if model was updated
        """
        print("\n" + "="*70)
        print(f"🔄 INCREMENTAL UPDATE: {self.model_name}")
        print("="*70)
        
        # Get training data
        df = self.get_training_data(logger, min_samples=100)
        if df is None:
            return False
        
        # Train new model
        new_model, metrics = self.train_incremental(df)
        
        # Decide if should update
        should_update = force or self.should_update_model(metrics)
        
        if should_update:
            # Save new model
            version = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.save_model(new_model, metrics, version)
            
            # Update production
            self.update_production_model(new_model, version)
            
            print("\n✅ Incremental update COMPLETE!")
            print("="*70)
            return True
        else:
            print("\n⚠️ Model not updated (insufficient improvement)")
            print("="*70)
            return False

# Singleton instances
_learners = {}

def get_learner(model_name: str) -> OnlineLearner:
    """Get online learner instance for a model"""
    global _learners
    if model_name not in _learners:
        _learners[model_name] = OnlineLearner(model_name)
    return _learners[model_name]
