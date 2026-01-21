#!/usr/bin/env python3
"""
Train Universal Portfolio Model (5 Coins)
-----------------------------------------
1. Load 1m Data for BTC, ETH, SOL, AVAX, SUI
2. Normalize features (using % change, not raw price)
3. Combine into one mega-dataset
4. Train XGBoost Model
"""

import pandas as pd
import numpy as np
import xgboost as xgb
import os
import glob
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# --- CONFIG ---
DATA_DIR = 'training/data/1m_portfolio'
MODEL_DIR = 'models'
PERIOD = 14
TP_PCT = 0.010
SL_PCT = 0.005

def add_features(df):
    df = df.copy()
    
    # Williams %R
    high_roll = df['high'].rolling(PERIOD).max()
    low_roll = df['low'].rolling(PERIOD).min()
    denom = high_roll - low_roll
    denom = denom.replace(0, np.nan)
    df['williams_r'] = -100 * (high_roll - df['close']) / denom
    df['williams_r_prev'] = df['williams_r'].shift(1)
    
    # RSI 14
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan) # avoid div0
    df['rsi_14'] = 100 - (100 / (1 + rs))
    
    # Volatility
    df['atr_14'] = (df['high'] - df['low']).rolling(14).mean() / df['close'] # Normalized ATR
    
    # Volume Change
    df['vol_change'] = df['volume'].pct_change()
    
    # Trend
    df['ema_200_dist'] = (df['close'] - df['close'].ewm(span=200).mean()) / df['close']
    
    return df

def label_data(df):
    """
    Label Win/Loss based on TP/SL
    """
    df = df.copy()
    signals = []
    
    # Detect Crosses (> -20, < -80) - Optimized Thresholds from before were -20/-80
    long_mask = (df['williams_r_prev'] < -20) & (df['williams_r'] >= -20)
    short_mask = (df['williams_r_prev'] > -80) & (df['williams_r'] <= -80)
    
    indices = df[long_mask | short_mask].index
    
    for idx in indices:
        if idx >= len(df) - 300: continue # Skip end
        
        row = df.loc[idx]
        is_long = long_mask[idx]
        
        entry = row['close']
        tp = entry * (1 + TP_PCT) if is_long else entry * (1 - TP_PCT)
        sl = entry * (1 - SL_PCT) if is_long else entry * (1 + SL_PCT)
        
        outcome = 0
        match = False
        
        # Look ahead 60m (60 candles)
        future = df.loc[idx+1 : idx+60]
        
        for _, f in future.iterrows():
            if is_long:
                if f['high'] >= tp: outcome=1; match=True; break
                if f['low'] <= sl: outcome=0; match=True; break
            else:
                if f['low'] <= tp: outcome=1; match=True; break
                if f['high'] >= sl: outcome=0; match=True; break
        
        if match:
            s = row.to_dict()
            s['target'] = outcome
            signals.append(s)
            
    return pd.DataFrame(signals)

def main():
    print("📥 Loading Portfolio Data...")
    files = glob.glob(os.path.join(DATA_DIR, "*_1m_7days.csv"))
    
    all_signals = []
    
    for f in files:
        coin = os.path.basename(f).split('_')[0]
        print(f"   Processing {coin}...", end=" ")
        df = pd.read_csv(f)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        if len(df) < 300: continue
        
        df = add_features(df)
        signals = label_data(df)
        signals['coin'] = coin # Track source
        
        all_signals.append(signals)
        print(f"✅ {len(signals)} signals")
        
    if not all_signals:
        print("❌ No signals found across all coins.")
        return

    mega_df = pd.concat(all_signals, ignore_index=True)
    print(f"\n📊 Total Training Samples: {len(mega_df)}")
    
    if len(mega_df) < 50:
        print("❌ Too few samples to train (<50).")
        return

    print(f"   Win Rate (Baseline): {mega_df['target'].mean()*100:.2f}%")
    
    # Train
    features = ['williams_r', 'rsi_14', 'atr_14', 'vol_change', 'ema_200_dist']
    
    # Clean Data
    X = mega_df[features].replace([np.inf, -np.inf], np.nan).fillna(0)
    y = mega_df['target']
    
    # Ensure X types are valid
    X = X.astype(float)
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("\n🧠 Training Universal Model...")
    # Reduce n_estimators if small data
    model = xgb.XGBClassifier(n_estimators=100, max_depth=5, learning_rate=0.05, objective='binary:logistic')
    model.fit(X_train, y_train)
    
    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)[:, 1]
    
    print(f"✅ Accuracy: {accuracy_score(y_test, preds):.2f}")
    
    # High Confidence Check
    high_conf = [y_test.iloc[i] for i, p in enumerate(probs) if p > 0.70]
    if high_conf:
        acc = sum(high_conf)/len(high_conf)
        print(f"🚀 High Confidence (>70%) Accuracy: {acc*100:.2f}% ({len(high_conf)} trades)")
        
    # Save
    if not os.path.exists(MODEL_DIR): os.makedirs(MODEL_DIR)
    model.save_model(os.path.join(MODEL_DIR, 'universal_portfolio_v1.json'))
    print("💾 Model Saved.")

if __name__ == "__main__":
    main()
