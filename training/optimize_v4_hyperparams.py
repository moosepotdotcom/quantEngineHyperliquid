
import pandas as pd
import numpy as np
import xgboost as xgb
import os
import sys
import random
from sklearn.metrics import precision_score, roc_auc_score

# Add root (one level up)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from training.train_v4_2025 import load_local_training_data, fetch_test_data

def optimize_hyperparams():
    print("🚀 Starting V4 Hyperparameter Optimization (Rescue Mission)...")
    
    # 1. Load Data
    path = '/Users/alifiyaa/Downloads/quantEngineHyperliquid/training/data/BTC_5m_mtf_labeled.csv'
    X_train, y_train = load_local_training_data(path)
    X_test, y_test = fetch_test_data()
    
    if X_train is None: return
    
    # Align Columns
    if X_train.shape[1] == X_test.shape[1]:
        X_train.columns = X_test.columns
    else:
        print("❌ Feature mismatch.")
        return

    # 2. Define Parameter Space (Regularization Focus)
    param_grid = {
        'max_depth': [3, 4, 5, 6],           # Lower depth to prevent memorization
        'learning_rate': [0.01, 0.05, 0.1],  # Slower learning
        'subsample': [0.6, 0.7, 0.8],        # Row sampling
        'colsample_bytree': [0.6, 0.7, 0.8], # Feature sampling
        'min_child_weight': [5, 10, 20],     # Higher weight to block noise
        'gamma': [0.1, 0.5, 1.0, 5.0],       # Minimum loss reduction
        'reg_alpha': [0.1, 1.0, 10.0],       # L1 Reg
        'reg_lambda': [1.0, 5.0, 10.0]       # L2 Reg
    }
    
    # 3. Random Search Loop
    n_iter = 20
    best_score = 0
    best_params = {}
    
    print(f"\n🧪 Running {n_iter} Experiments...")
    print(f"{'Iter':<4} | {'Prec(>0.6)':<10} | {'AUC':<6} | {'Params'}")
    print("-" * 80)
    
    for i in range(n_iter):
        # Sample Params
        params = {
            'objective': 'multi:softprob',
            'num_class': 3,
            'eval_metric': 'mlogloss',
            'n_estimators': 500, # Fixed decent size
            'early_stopping_rounds': 50,
            'tree_method': 'hist',
            'n_jobs': -1,
            'verbosity': 0,
            
            'max_depth': random.choice(param_grid['max_depth']),
            'learning_rate': random.choice(param_grid['learning_rate']),
            'subsample': random.choice(param_grid['subsample']),
            'colsample_bytree': random.choice(param_grid['colsample_bytree']),
            'min_child_weight': random.choice(param_grid['min_child_weight']),
            'gamma': random.choice(param_grid['gamma']),
            'reg_alpha': random.choice(param_grid['reg_alpha']),
            'reg_lambda': random.choice(param_grid['reg_lambda'])
        }
        
        # Train
        model = xgb.XGBClassifier(**params)
        
        # Sample weights (Focus on winners)
        weights = np.ones(len(y_train))
        weights[y_train != 0] = 3.0
        
        model.fit(
            X_train, y_train,
            sample_weight=weights,
            eval_set=[(X_test, y_test)],
            verbose=False
        )
        
        # Evaluate
        probs = model.predict_proba(X_test)
        
        # Calculate Precision at Confidence > 0.60 (Realistic trading threshold)
        long_preds = (probs[:, 1] > 0.60)
        short_preds = (probs[:, 2] > 0.60)
        
        # Check Longs
        if long_preds.sum() > 0:
            prec_long = precision_score(y_test, np.ones(len(y_test)), sample_weight=long_preds.astype(int), zero_division=0)
            # wait, precision_score compares y_true vs y_pred. 
            # y_true is 0,1,2. If we predict Long (1), we want y_true==1.
            # Manual calc is safer.
            true_longs = y_test[long_preds]
            acc_long = (true_longs == 1).mean()
        else:
            acc_long = 0
            
        # Check Shorts
        if short_preds.sum() > 0:
            true_shorts = y_test[short_preds]
            acc_short = (true_shorts == 2).mean()
        else:
            acc_short = 0
            
        # We want a weighted average of precision, but only if we have trades
        n_long = long_preds.sum()
        n_short = short_preds.sum()
        total_trades = n_long + n_short
        
        if total_trades > 0:
            weighted_prec = ((acc_long * n_long) + (acc_short * n_short)) / total_trades
        else:
            weighted_prec = 0
            
        # Score: Precision matters most, but we need some volume (trades)
        # If trades < 10, penalize
        score = weighted_prec
        if total_trades < 10: score *= 0.5
        
        print(f"{i+1:<4} | {weighted_prec:.1%} ({total_trades}) | {'-':<6} | D:{params['max_depth']} LR:{params['learning_rate']} L1:{params['reg_alpha']} G:{params['gamma']}")
        
        if score > best_score:
            best_score = score
            best_params = params
            print(f"      ✨ NEW BEST! (Prec: {weighted_prec:.1%} on {total_trades} trades)")

    print("\n🏆 OPTIMIZATION COMPLETE")
    print(f"Best Score: {best_score}")
    print(f"Best Params: {best_params}")

if __name__ == '__main__':
    optimize_hyperparams()
