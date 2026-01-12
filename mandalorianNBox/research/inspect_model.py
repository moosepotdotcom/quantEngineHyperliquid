#!/usr/bin/env python3
"""
Inspect ML Model
===============
Loads the trained XGBoost model and finds the optimal probability threshold.
Goal: Find a threshold where Precision > 60% even if Recall is low.
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
import joblib
import json
try:
    import xgboost as xgb
except ImportError:
    pass # Might be using RF
from sklearn.metrics import precision_recall_curve, precision_score

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(PROJECT_ROOT)

try:
    from research.meta_learner import create_labels
    from research.feature_generator import AdvancedFeatureGenerator
except ImportError:
    # Quick hack to run standalone
    from feature_generator import AdvancedFeatureGenerator

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

def inspect(data_path, model_path):
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
    
    # 2. Features & Labels
    gen = AdvancedFeatureGenerator(df)
    df = gen.generate_all()
    df = create_labels(df)
    df.dropna(inplace=True)
    
    features = [c for c in df.columns if c not in ['open', 'high', 'low', 'close', 'volume', 'target', 'dividends', 'stock splits']]
    X = df[features]
    y = df['target']
    
    # 3. Load Model
    model = joblib.load(model_path)
    
    # 4. Predict Probabilities
    # Class 1 is profitable
    probs = model.predict_proba(X)[:, 1]
    
    # 5. Threshold Analysis
    thresholds = np.arange(0.1, 0.95, 0.05)
    best_thresh = 0.5
    best_prec = 0
    results = []
    
    print(f"{'Threshold':<10} | {'Precision':<10} | {'Recall':<10} | {'Trades/Day':<10}")
    print("-" * 50)
    
    for t in thresholds:
        preds = (probs >= t).astype(int)
        prec = precision_score(y, preds, zero_division=0)
        rec = len(y[y==1][preds[y==1]==1]) / len(y[y==1])
        
        # Estimate trades per day (15m bars = 96 per day)
        n_trades = np.sum(preds)
        days = len(df) / 96
        trades_per_day = n_trades / days
        
        if n_trades > 5: # Ignore empty filters
            print(f"{t:.2f}       | {prec:.2%}     | {rec:.2%}     | {trades_per_day:.1f}")
            results.append({"threshold": float(t), "precision": float(prec), "trades": int(n_trades)})
            
            if prec > best_prec and n_trades > 20:
                best_prec = prec
                best_thresh = t
                
    # 6. Save Optimal Threshold
    config_path = os.path.join(PROJECT_ROOT, "models", "ml_config.json")
    with open(config_path, "w") as f:
        json.dump({"min_probability": float(best_thresh), "expected_precision": float(best_prec)}, f, indent=4)
        
    logger.info(f"\n✅ Optimal Threshold Saved: {best_thresh:.2f} (Precision: {best_prec:.2%})")

if __name__ == "__main__":
    data_file = os.path.abspath(os.path.join(PROJECT_ROOT, "datasets", "BTCUSD-15m-max-data.csv"))
    model_file = os.path.abspath(os.path.join(PROJECT_ROOT, "models", "scalp_xgb.pkl"))
    inspect(data_file, model_file)
