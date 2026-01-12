
import sys
import os
import pandas as pd
import numpy as np
import xgboost as xgb
import ta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
MODELS_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')

def load_data(timeframe):
    path = os.path.join(DATA_DIR, f'BTC_{timeframe}.csv')
    if not os.path.exists(path):
        print(f"❌ Missing {path}")
        return None
    df = pd.read_csv(path)
    if 'timestamp' in df.columns:
        df['datetime'] = pd.to_datetime(df['timestamp'])
        df.set_index('datetime', inplace=True)
    return df

def add_features_approx(df, suffix, multiplier):
    """
    Adds indicators using 'period * multiplier' on the BASE timeframe
    to strictly mimic the MTFScalperStrategy logic.
    """
    # RSI
    df[f'rsi_{suffix}'] = ta.momentum.rsi(df['close'], window=14*multiplier)
    
    # Bollinger Bands
    bb = ta.volatility.BollingerBands(df['close'], window=20*multiplier, window_dev=2)
    df[f'bb_high_{suffix}'] = bb.bollinger_hband()
    df[f'bb_low_{suffix}'] = bb.bollinger_lband()
    # Strategy Logic: (bb_top - bb_bot) / (bb_mid + 1e-9)
    # TA Lib: (h - l) / mavg
    df[f'bb_width_{suffix}'] = (bb.bollinger_hband() - bb.bollinger_lband()) / (bb.bollinger_mavg() + 1e-9)
    
    # MACD
    # Strategy: 12*m, 26*m, 9*m
    macd = ta.trend.MACD(df['close'], window_slow=26*multiplier, window_fast=12*multiplier, window_sign=9*multiplier)
    df[f'macd_{suffix}'] = macd.macd()
    
    # EMA Trend
    df[f'ema_50_{suffix}'] = ta.trend.ema_indicator(df['close'], window=50*multiplier)
    df[f'ema_200_{suffix}'] = ta.trend.ema_indicator(df['close'], window=200*multiplier)
    
    return df

def train_mtf_scalper_approx():
    print("🧠 Training MTF AI Scalper Model (Approximation Mode)...")
    
    # 1. Load Data (Only Base 15m needed!)
    df_15m = load_data('15m')
    
    if df_15m is None:
        print("❌ Data missing.")
        return

    # 2. Feature Engineering
    print("⚙️ Generating Approximated Features...")
    df = df_15m.copy()
    
    # Base Features (Multiplier 1) -> "5m" suffix in strategy terms (Context 0)
    # Strategy calls this 'get_ml_features' with Base, 1H, 4H.
    # We will name them consistent with strategy expectation:
    # 0: Base
    # 1: Context 1 (1H approx -> x4)
    # 2: Context 2 (4H approx -> x16)
    
    # Group 1: Base (15m)
    df = add_features_approx(df, 'base', 1)
    
    # Group 2: Context 1 (1H Approx)
    df = add_features_approx(df, '1h', 4)
    
    # Group 3: Context 2 (4H Approx)
    df = add_features_approx(df, '4h', 16)
    
    # Drop NaNs
    df.dropna(inplace=True)
    
    # 3. Create Targets (Labels)
    print("🏷️ Labeling Data...")
    lookahead = 12
    tp_pct = 0.015
    sl_pct = 0.010
    
    labels = []
    
    closes = df['close'].values
    highs = df['high'].values
    lows = df['low'].values
    
    for i in range(len(df) - lookahead):
        current_close = closes[i]
        target_price = current_close * (1 + tp_pct)
        stop_price = current_close * (1 - sl_pct)
        
        outcome = 0 
        
        for j in range(1, lookahead + 1):
            future_high = highs[i+j]
            future_low = lows[i+j]
            
            if future_low <= stop_price:
                outcome = 0
                break
            if future_high >= target_price:
                outcome = 1
                break
                
        labels.append(outcome)
        
    df_train = df.iloc[:-lookahead].copy()
    df_train['target'] = labels
    
    # 4. Correct Column Ordering to Match Strategy
    # Strategy: f_base + f_1h + f_4h
    # Each Block: [rsi, bb_high, bb_low, bb_w, macd, ema50, ema200]
    # Note: Strategy 'pack_features' returns: [rsi, top, bot, width, macd, ema50, ema200]
    # We must match this EXACTLY.
    
    feature_cols = []
    for suffix in ['base', '1h', '4h']:
        feature_cols.extend([
            f'rsi_{suffix}',
            f'bb_high_{suffix}',
            f'bb_low_{suffix}',
            f'bb_width_{suffix}',
            f'macd_{suffix}',
            f'ema_50_{suffix}',
            f'ema_200_{suffix}'
        ])
        
    X = df_train[feature_cols]
    y = df_train['target']
    
    print(f"📊 Dataset: {len(X)} rows. Win Rate: {y.mean():.2%}")
    
    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric='logloss'
    )
    
    split = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]
    
    model.fit(X_train, y_train)
    
    print(f"🎯 Train Acc: {model.score(X_train, y_train):.2%} | Test Acc: {model.score(X_test, y_test):.2%}")
    
    # Save Overwrite
    model_path = os.path.join(MODELS_DIR, 'scalp_mtf_v2_xgb.json')
    model.save_model(model_path)
    print(f"✅ Model restored (Approx Mode) to {model_path}")

if __name__ == '__main__':
    train_mtf_scalper_approx()
