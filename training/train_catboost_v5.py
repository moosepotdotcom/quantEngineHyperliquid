
import pandas as pd
import numpy as np
from catboost import CatBoostClassifier, Pool
import joblib
import os
import sys

# Add root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from train_v4_2025 import load_local_training_data, fetch_test_data

def train_catboost_v5():
    print("🚀 Starting V5 (CatBoost) Training Pipeline...")
    
    # 1. LOAD LOCAL TRAINING DATA (Same as V4)
    # Re-use the optimized loader from V4 script
    path = '/Users/alifiyaa/Downloads/quantEngineHyperliquid/training/data/BTC_5m_mtf_labeled.csv'
    X_train, y_train = load_local_training_data(path)
    if X_train is None: return
    
    # 2. FETCH TEST (Jan 2026)
    X_test, y_test = fetch_test_data()
    
    # 3. ALIGN FEATURE NAMES
    print("   🔗 Aligning Feature Names...")
    if X_train.shape[1] == X_test.shape[1]:
        X_train.columns = X_test.columns
        print("      ✅ Applied feature names from Test Set to Train Set")
    else:
        print(f"      ❌ Feature count mismatch! Train: {X_train.shape[1]}, Test: {X_test.shape[1]}")
        return

    # 4. SAMPLE WEIGHTS (Focus on Winners)
    print("⚖️ Calculating Sample Weights...")
    sample_weights = np.ones(len(y_train))
    sample_weights[y_train == 0] = 1.0
    sample_weights[y_train == 1] = 3.0 # Boost Longs
    sample_weights[y_train == 2] = 3.0 # Boost Shorts
    
    # 5. TRAINING CATBOOST
    print("🐱 Training CatBoost Model...")
    
    model = CatBoostClassifier(
        iterations=1000,
        depth=6,
        learning_rate=0.03,
        loss_function='MultiClass',
        eval_metric='Accuracy',
        random_seed=42,
        verbose=100,
        task_type="CPU",
        early_stopping_rounds=50
    )
    
    train_pool = Pool(X_train, y_train, weight=sample_weights)
    test_pool = Pool(X_test, y_test)
    
    model.fit(train_pool, eval_set=test_pool)
    
    # 6. EVALUATION
    print("\n🔍 Evaluation (Jan 2026 Out-of-Sample):")
    y_pred_test = model.predict(X_test)
    
    from sklearn.metrics import classification_report
    print(classification_report(y_test, y_pred_test, zero_division=0))
    
    # Save the model
    # Ensure dir exists
    save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'model_engines/mtf_scalper_v3/weights')
    os.makedirs(save_dir, exist_ok=True)
    
    model_path = os.path.join(save_dir, 'mtf_scalper_v5_cat.cbm')
    print(f"💾 Saving CatBoost Model to: {model_path}")
    model.save_model(model_path)
    print("   ✅ V5 CatBoost Model Saved!")

if __name__ == '__main__':
    train_catboost_v5()
