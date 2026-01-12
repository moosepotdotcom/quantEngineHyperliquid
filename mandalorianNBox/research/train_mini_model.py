
import pandas as pd
import numpy as np
import ta
import xgboost as xgb
import pickle
import json
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

def train_mini_scalper():
    print("🧠 Training 'Mini Scalper V3' Model...")
    
    # 1. Load Data
    path = os.path.join(os.path.dirname(__file__), '..', 'data', 'BTC_15m.csv')
    df = pd.read_csv(path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    # 2. Indicators (Features)
    # We need a robust feature set for the AI to filter effectively
    df['rsi'] = ta.momentum.rsi(df['close'], window=9) # Candidate uses 9
    df['atr'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
    df['bb_w'] = ta.volatility.bollinger_wband(df['close'], window=20, window_dev=2)
    df['vol_ma'] = df['volume'].rolling(20).mean()
    df['vol_ratio'] = df['volume'] / (df['vol_ma'] + 1)
    df['ema50'] = ta.trend.ema_indicator(df['close'], window=50)
    df['dist_ema'] = (df['close'] - df['ema50']) / df['ema50']
    
    # Drop NaNs
    df.dropna(inplace=True)
    
    # 3. Labeling (The Candidate Strategy Logic)
    # Candidate: RSI 9 < 35 | TP 300 | SL 50
    # Logic: If RSI < 35, BUY. Target +300, Stop -50.
    
    labels = []
    valid_indices = []
    
    closes = df['close'].values
    highs = df['high'].values
    lows = df['low'].values
    rsi_vals = df['rsi'].values
    
    tp_dist = 300.0
    sl_dist = 50.0
    entry_thresh = 35.0
    
    for i in range(len(closes) - 100): # Ensure space for trade to resolve
        if rsi_vals[i] < entry_thresh:
            entry_price = closes[i]
            target = entry_price + tp_dist
            stop = entry_price - sl_dist
            
            # Check forward
            outcome = 0 # Loss default
            for j in range(i+1, i+100): # Max hold 100 bars?
                if lows[j] <= stop:
                    outcome = 0 # Loss
                    break
                if highs[j] >= target:
                    outcome = 1 # Win
                    break
            
            labels.append(outcome)
            valid_indices.append(i)
            
    # 4. Create ML Dataset
    # We only train on the bars where a signal generated (RSI < 35)
    feature_cols = ['rsi', 'atr', 'bb_w', 'vol_ratio', 'dist_ema']
    X = df.iloc[valid_indices][feature_cols].values
    y = np.array(labels)
    
    print(f"   Dataset Size: {len(X)} potential trades")
    print(f"   Base Win Rate: {np.mean(y)*100:.2f}% (Without AI)")
    
    if len(X) < 50:
        print("⚠️ Not enough samples to train.")
        return

    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
    
    # Train XGBoost
    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        objective='binary:logistic',
        eval_metric='logloss'
    )
    
    model.fit(X_train, y_train)
    
    # Evaluate
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"🎯 Test Accuracy: {acc*100:.2f}%")
    
    # Save
    model_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'scalp_mini_v3_xgb.json')
    model.save_model(model_path)
    print(f"✅ Model saved to {model_path}")

if __name__ == "__main__":
    train_mini_scalper()
