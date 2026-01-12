
import pandas as pd
import numpy as np
import ta
import xgboost as xgb
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

def train_mini_v4():
    print("🧠 Training 'Mini Scalper V4' (High Freq)...")
    
    # 1. Load Data
    path = os.path.join(os.path.dirname(__file__), '..', 'data', 'BTC_15m.csv')
    df = pd.read_csv(path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    # 2. Indicators (Features)
    df['rsi'] = ta.momentum.rsi(df['close'], window=9)
    df['atr'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
    df['bb_w'] = ta.volatility.bollinger_wband(df['close'], window=20, window_dev=2)
    df['vol_ma'] = df['volume'].rolling(20).mean()
    df['vol_ratio'] = df['volume'] / (df['vol_ma'] + 1e-9)
    df['ema50'] = ta.trend.ema_indicator(df['close'], window=50)
    df['dist_ema'] = (df['close'] - df['ema50']) / df['ema50']
    
    # Drop NaNs
    df.dropna(inplace=True)
    
    # 3. Labeling (Candidate: RSI 9 < 40 | TP 150 | SL 100)
    labels = []
    valid_indices = []
    
    closes = df['close'].values
    highs = df['high'].values
    lows = df['low'].values
    rsi_vals = df['rsi'].values
    
    tp_dist = 150.0
    sl_dist = 100.0
    entry_thresh = 40.0 # Aggressive entry
    
    print(f"   Labeling trades (RSI < 40, TP {tp_dist}, SL {sl_dist})...")
    
    for i in range(len(closes) - 100):
        if rsi_vals[i] < entry_thresh:
            entry_price = closes[i]
            target = entry_price + tp_dist
            stop = entry_price - sl_dist
            
            outcome = 0 
            for j in range(i+1, i+100):
                if lows[j] <= stop:
                    outcome = 0
                    break
                if highs[j] >= target:
                    outcome = 1
                    break
            
            labels.append(outcome)
            valid_indices.append(i)
            
    # 4. Create ML Dataset
    feature_cols = ['rsi', 'atr', 'bb_w', 'vol_ratio', 'dist_ema']
    X = df.iloc[valid_indices][feature_cols].values
    y = np.array(labels)
    
    print(f"   Dataset Size: {len(X)} trades")
    print(f"   Raw Win Rate: {np.mean(y)*100:.2f}%")
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
    
    # Train XGBoost
    # We use scale_pos_weight because class imbalance (32% win rate)
    ratio = float(np.sum(y == 0)) / np.sum(y == 1)
    
    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.03,
        scale_pos_weight=ratio, # Focus on finding the rare wins? Or balance?
        # Actually we want high precision.
        objective='binary:logistic',
        eval_metric='logloss'
    )
    
    model.fit(X_train, y_train)
    
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"🎯 Test Accuracy: {acc*100:.2f}%")
    
    # Save
    model_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'scalp_mini_v4_xgb.json')
    model.save_model(model_path)
    print(f"✅ Model saved to {model_path}")

if __name__ == "__main__":
    train_mini_v4()
