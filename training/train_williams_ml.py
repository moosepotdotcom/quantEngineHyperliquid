#!/usr/bin/env python3
"""
Train Williams %R ML Model
--------------------------
1. Load 5m MTF Data (Huge File)
2. Extract Williams %R Signals
3. Label Outcomes (Win/Loss)
4. Train XGBoost/LGBM/CatBoost
"""

import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os
import sys

# --- CONFIG ---
DATA_FILE = 'training/data/BTC_5m_mtf_labeled.csv' # Huge training set
MODEL_DIR = 'models'
PERIOD = 14
TP_PCT = 0.010
SL_PCT = 0.005

# Features to use (Standard MTF list + specific ones)
FEATURE_COLS = [
    # Momentum
    'rsi_14', 'rsi_14_1h', 'rsi_14_4h',
    'macd', 'macd_hist', 'macd_1h',
    'adx', 'adx_1h',
    'williams_r', # The trigger itself is also a feature
    
    # Volatility
    'atr_14', 'bb_width',
    
    # Trend
    'ema_50', 'ema_200',
    
    # Volume
    'volume', 'obv'
]

def calculate_williams_r(df, period=140):
    high_roll = df['high'].rolling(period).max()
    low_roll = df['low'].rolling(period).min()
    denom = high_roll - low_roll
    denom = denom.replace(0, np.nan)
    return -100 * (high_roll - df['close']) / denom

def label_data(df):
    """
    Find signals and label them.
    Returns a new DataFrame with ONLY signal rows + 'target' column.
    """
    df = df.copy()
    
    # Ensure Williams %R is calculated with correct period
    # (The file might have wr_14, we need wr_140)
    print(f"🔧 Calculating Williams %R ({PERIOD})...")
    df['williams_r_140'] = calculate_williams_r(df, PERIOD)
    df['williams_r_140_prev'] = df['williams_r_140'].shift(1)
    
    signals = []
    
    # We need to look ahead to label
    # This is slow in pure python loop, but robust
    # Optimizing by detecting indices first
    
    long_condition = (df['williams_r_140_prev'] < -25) & (df['williams_r_140'] >= -25)
    short_condition = (df['williams_r_140_prev'] > -80) & (df['williams_r_140'] <= -80)
    
    signal_indices = df[long_condition | short_condition].index
    
    print(f"⚡ Processing {len(signal_indices)} signals...")
    
    for idx in signal_indices:
        if idx >= len(df) - 500: continue # Skip end
        
        row = df.loc[idx]
        is_long = long_condition[idx]
        
        entry_price = row['close']
        tp = entry_price * (1 + TP_PCT) if is_long else entry_price * (1 - TP_PCT)
        sl = entry_price * (1 - SL_PCT) if is_long else entry_price * (1 + SL_PCT)
        
        outcome = 0 # Loss
        
        # Look ahead up to 288 candles (24h)
        match = False
        future_window = df.loc[idx+1 : idx+288]
        
        for _, future in future_window.iterrows():
            if is_long:
                if future['high'] >= tp:
                    outcome = 1; match = True; break
                if future['low'] <= sl:
                    outcome = 0; match = True; break
            else:
                if future['low'] <= tp:
                    outcome = 1; match = True; break
                if future['high'] >= sl:
                    outcome = 0; match = True; break
        
        if match:
            # Add features for this row
            signal_data = row.to_dict()
            signal_data['target'] = outcome
            signal_data['signal_type'] = 1 if is_long else -1 # Metadata
            signals.append(signal_data)
            
    return pd.DataFrame(signals)

def train_models():
    if not os.path.exists(DATA_FILE):
        print(f"❌ Error: Data file {DATA_FILE} not found.")
        return

    print("📥 Loading Training Data (this might take a while)...")
    # Load limited columns to save RAM if needed, but for now specific cols
    # We need OHLCV for labeling + Feature columns
    df = pd.read_csv(DATA_FILE)
    df.columns = [c.lower() for c in df.columns] # normalize
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    print(f"✅ Loaded {len(df)} rows.")
    
    # 1. Label Data
    print("🏷️ Labeling Data...")
    labeled_df = label_data(df)
    
    print(f"📊 Training Set Size: {len(labeled_df)} samples")
    print(f"   Win Rate (Baseline): {labeled_df['target'].mean()*100:.2f}%")
    
    if len(labeled_df) < 100:
        print("❌ Not enough signals to train. Check thresholds.")
        return

    # 2. Prepare Features
    # Filter only available features
    use_cols = [c for c in FEATURE_COLS if c in labeled_df.columns]
    
    # Fill NAs
    X = labeled_df[use_cols].fillna(0)
    y = labeled_df['target']
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=False)
    
    # 3. Train XGBoost
    print("\n🧠 Training XGBoost...")
    model = xgb.XGBClassifier(
        n_estimators=500,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42
    )
    model.fit(X_train, y_train)
    
    # Evaluate
    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)[:, 1]
    
    acc = accuracy_score(y_test, preds)
    print(f"✅ Accuracy: {acc:.2f}")
    print(classification_report(y_test, preds))
    
    # High Confidence Check
    high_conf_indices = [i for i, p in enumerate(probs) if p > 0.80]
    if high_conf_indices:
        actual_wins = [y_test.iloc[i] for i in high_conf_indices]
        high_conf_acc = sum(actual_wins) / len(actual_wins)
        print(f"🚀 High Confidence (>80%) Accuracy: {high_conf_acc*100:.2f}% ({len(actual_wins)} trades)")
    else:
        print("⚠️ No predictions > 80% confidence found.")

    # Save
    if not os.path.exists(MODEL_DIR): os.makedirs(MODEL_DIR)
    model_path = os.path.join(MODEL_DIR, 'williams_xgb.json')
    model.save_model(model_path)
    print(f"💾 Model saved to {model_path}")

if __name__ == "__main__":
    train_models()
