
import os
import sys
import pandas as pd
import numpy as np
import joblib
import json
from sklearn.metrics import precision_score

# Setup Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from research.mtf_feature_engineer import MTFFeatureGenerator
from research.mtf_meta_learner_xgb import create_labels

def inspect_mtf_model():
    base_dir = os.path.join(os.path.dirname(__file__), '..', 'datasets')
    model_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'scalp_mtf_xgb.pkl')
    
    # Load Datas
    df_5m = pd.read_csv(os.path.join(base_dir, "BTCUSD-5m-max-data.csv"))
    df_15m = pd.read_csv(os.path.join(base_dir, "BTCUSD-15m-max-data.csv"))
    df_30m = pd.read_csv(os.path.join(base_dir, "BTCUSD-30m-max-data.csv"))
    
    # Standardize Datetime
    for df in [df_5m, df_15m, df_30m]:
        if 'datetime' in df.columns: df['datetime'] = pd.to_datetime(df['datetime'])
        elif 'timestamp' in df.columns: df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Generate Features & Labels
    gen = MTFFeatureGenerator(df_5m, df_15m, df_30m)
    df = gen.generate()
    df = create_labels(df)
    df.dropna(inplace=True)
    
    features = [c for c in df.columns if c not in ['open', 'high', 'low', 'close', 'volume', 'target', 'dividends', 'stock splits', 'open_15m', 'close_15m', 'high_15m', 'low_15m', 'volume_15m', 'open_30m', 'close_30m']]
    X = df[features]
    y = df['target']
    
    model = joblib.load(model_path)
    probs = model.predict_proba(X)[:, 1]
    
    print(f"{'Threshold':<10} | {'Precision':<10} | {'Recall':<10} | {'Trades/Day':<10}")
    print("-" * 50)
    
    thresholds = np.arange(0.5, 0.95, 0.05)
    
    days = len(df) / 288 # 5m bars = 288/day
    
    for t in thresholds:
        preds = (probs >= t).astype(int)
        
        if np.sum(preds) < 5: continue
        
        prec = precision_score(y, preds, zero_division=0)
        rec = len(y[y==1][preds[y==1]==1]) / len(y[y==1])
        n_trades = np.sum(preds)
        
        print(f"{t:.2f}       | {prec:.2%}     | {rec:.2%}     | {n_trades/days:.1f}")

if __name__ == "__main__":
    inspect_mtf_model()
