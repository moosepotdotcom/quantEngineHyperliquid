import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, classification_report
import joblib
import sys
import os

# Add path to access existing utils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quant_engine import add_all_indicators, MTF_FEATURE_LIST

def generate_advanced_features(df):
    """
    Generates 'Alpha' features beyond the standard set.
    """
    print("   🧠 Generating Alpha Features (Lags, Volatility, Time)...")
    
    # 1. Volatility Regime (Normalized ATR)
    # Rolling 100-period ATR normalized by price
    df['atr_100'] = df['high'].rolling(100).max() - df['low'].rolling(100).min() # Approximation
    df['vol_regime'] = (df['close'].rolling(20).std() / df['close']) * 100
    
    # 2. Lagged Features (The "Memory")
    # We want the model to know what happened 1, 3, and 5 candles ago
    lags = [1, 2, 3, 5]
    cols_to_lag = ['rsi_14', 'roc_5', 'return_1', 'vol_regime']
    
    for col in cols_to_lag:
        if col not in df.columns: continue
        for lag in lags:
            df[f'{col}_lag{lag}'] = df[col].shift(lag)
            
    # 3. Cyclical Time Features
    df['hour_sin'] = np.sin(2 * np.pi * df.index.hour / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df.index.hour / 24)
    df['day_sin'] = np.sin(2 * np.pi * df.index.dayofweek / 7)
    df['day_cos'] = np.cos(2 * np.pi * df.index.dayofweek / 7)
    
    return df

def train_meta_model():
    print("="*60)
    print("🚀 TRAINING AI META-MODEL OPTIMIZER")
    print("="*60)
    
    # 1. Load Data
    print("🔄 Loading MASTER_TRAINING_DATA.csv...")
    df = pd.read_csv("MASTER_TRAINING_DATA.csv")
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    # 2. Add Standard Indicators
    print("🔧 Adding Standard Indicators...")
    df = add_all_indicators(df)
    
    # 3. Add Advanced Features
    df = generate_advanced_features(df)
    df.dropna(inplace=True)
    
    print(f"✅ Feature Engineering Complete. Rows: {len(df)}")
    
    # 4. Label Generation (The "Target")
    # We want to predict if a trade would be a WIN or LOSS
    # Rule: If Long, Win if Price hits +1.5% before -0.8%
    # Rule: If Short, Win if Price hits -1.5% before +0.8%
    # But for a simpler Meta-Model, let's predict simpler Look-Ahead Return
    
    print("🎯 Generating Labels (Look-Ahead)...")
    
    # Look ahead 12 hours (144 5m candles)
    LOOKAHEAD = 144
    TP = 0.015
    SL = 0.008
    
    # Vectorized labeling is hard for TP/SL, using simpler approximation for now
    # Label: Did price go up 1.5% in next 12h? (For Long Potential)
    # Ideally we retrain the DIRECTION model first with new features.
    
    # Let's train a new DIRECTIONAL PREDICTOR with the new Alpha Features
    # Target: 1 = Big Pump ( > 1.5% in 12h), 0 = Neutral/Dump
    
    df['future_high'] = df['high'].rolling(LOOKAHEAD).max().shift(-LOOKAHEAD)
    df['future_low'] = df['low'].rolling(LOOKAHEAD).min().shift(-LOOKAHEAD)
    
    df['target_long'] = ((df['future_high'] - df['close']) / df['close'] > TP).astype(int)
    # Improve label: Must not hit SL first. This is complex vectorized.
    # For now, let's rely on the robust classification:
    # Target: Price is higher in 4 hours?
    
    df['future_close_4h'] = df['close'].shift(-48) # 4 hours
    df['target_direction'] = 0 # Neutral
    df.loc[df['future_close_4h'] > df['close'] * 1.005, 'target_direction'] = 1 # Long
    df.loc[df['future_close_4h'] < df['close'] * 0.995, 'target_direction'] = 2 # Short
    
    # Drop rows without target
    df.dropna(inplace=True)
    
    # 5. Prepare Train/Test Split
    # Use Time-Series Split (Train on first 80%, Test on last 20%)
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]
    
    # Features to use (Standard + Alpha)
    # Filter numeric only
    feature_cols = [c for c in df.columns if c not in ['target_long', 'target_direction', 'future_high', 'future_low', 'future_close_4h', 'open','high','low','close','volume']]
    # Remove NaNs
    
    X_train = train_df[feature_cols]
    y_train = train_df['target_direction']
    X_test = test_df[feature_cols]
    y_test = test_df['target_direction']
    
    print(f"📊 Training Set: {len(X_train)} rows | Test Set: {len(X_test)} rows")
    
    # 6. Train XGBoost
    print("🤖 Training XGBoost Model...")
    model = xgb.XGBClassifier(
        n_estimators=500,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        n_jobs=-1,
        random_state=42
    )
    
    model.fit(X_train, y_train)
    
    # 7. Evaluate
    print("🔍 Evaluating...")
    preds = model.predict(X_test)
    report = classification_report(y_test, preds)
    print(report)
    
    # 8. Feature Importance
    print("\n🌟 Top 10 Alpha Features:")
    importance = pd.DataFrame({'feature': feature_cols, 'importance': model.feature_importances_})
    importance = importance.sort_values('importance', ascending=False)
    print(importance.head(10))
    
    # Save Model
    joblib.dump(model, "models/phase3_xgboost.pkl")
    print("\n💾 Model Saved to models/phase3_xgboost.pkl")

if __name__ == "__main__":
    train_meta_model()
