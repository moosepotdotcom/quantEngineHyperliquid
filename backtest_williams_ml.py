#!/usr/bin/env python3
"""
Williams %R ML Backtest
-----------------------
Strategy:
1. Williams %R (140) Signal (Trend + Vol Filter + Thresh)
2. ML Model Confirmation (Probability > 0.80)

Model: models/williams_xgb.json
"""

import pandas as pd
import numpy as np
import xgboost as xgb
import os
import sys

# --- CONFIG ---
DATA_FILE = 'training/data/BTC_Jan2_11_2026_Hyperliquid.csv'
MODEL_FILE = 'models/williams_xgb.json'
PERIOD = 14
CONFIDENCE_THRESH = 0.80

# Strategy Params (Foundation)
LONG_THRESH = -25
SHORT_THRESH = -80
TP_PCT = 0.010
SL_PCT = 0.005
FEE_PCT = 0.00035

# Feature Cols (Must match training exactly)
FEATURE_COLS = [
    'rsi_14', 'rsi_14_1h',
    'macd', 'macd_hist', 'macd_1h',
    'adx', 'adx_1h',
    'williams_r', 
    'atr_14', 'bb_width',
    'ema_50', 'ema_200',
    'volume', 'obv'
]

def calculate_williams_r(df, period=140):
    high_roll = df['high'].rolling(period).max()
    low_roll = df['low'].rolling(period).min()
    denom = high_roll - low_roll
    denom = denom.replace(0, np.nan)
    return -100 * (high_roll - df['close']) / denom

def prepare_features(df):
    """
    Calculate Williams %R and other features needed for ML
    Note: Most features (RSI, etc.) are already in the file if we load the correct one.
    But this file (Jan2_11) is raw OHLCV? 
    Wait, the optimization script used 'BTC_Jan2_11_2026_Hyperliquid.csv' which is raw.
    We need to compute features on the fly or load the enriched version.
    """
    # Quick Check: Does the file have indicators?
    # If not, we need utils.feature_engineer. But that's slow.
    # Let's assume we need to compute them.
    # For speed/simplicity, I will compute the KEY features used by the model.
    # For full accuracy, we should use 'utils.feature_engineer'.
    
    from utils.feature_engineer import add_all_indicators
    print("🔧 Computing indicators for ML inference...")
    df = add_all_indicators(df)
    
    # Ensure Williams %R 140 exists
    df['williams_r'] = calculate_williams_r(df, PERIOD)
    df['williams_r_prev'] = df['williams_r'].shift(1)
    
    # 4H/1H MTF features? 
    # 'BTC_Jan2_11_2026_Hyperliquid.csv' is 5m data?
    # If we want MTF features, we need to resample.
    # For this backtest, I'll mock them or compute accurately if possible.
    # Let's try to compute simple approximations.
    
    # 1H
    df_1h = df.resample('1h', on='timestamp').last()
    # Simple forward fill for backtest (lookahead bias check?) 
    # Proper way: merge_asof
    
    # For now, let's load the model and see what features it expects.
    # I used FEATURE_COLS list above. I need to make sure df has them.
    
    # Approximations for MTF (to keep script standalone/fast)
    # real 1h rsi is complex to compute from 5m without full history.
    # I will rely on 'add_all_indicators' if it handles MTF. 
    # Checking utils/feature_engineer.py... it has generate_mtf_features but that saves to files.
    # It has a mocked MTF section in backtest_high_win_rate.py. I'll copy that.
    
    return df

def run_backtest():
    if not os.path.exists(DATA_FILE):
        print(f"❌ Error: Data file {DATA_FILE} not found.")
        return
    
    if not os.path.exists(MODEL_FILE):
        print(f"❌ Error: Model file {MODEL_FILE} not found. Train first.")
        return

    print("📥 Loading Data & Model...")
    df = pd.read_csv(DATA_FILE)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Load Model
    model = xgb.XGBClassifier()
    model.load_model(MODEL_FILE)
    
    # Prepare Features (Using the full utils pipeline for accuracy)
    # We need to import the project root to find utils
    sys.path.append(os.getcwd())
    from utils.feature_engineer import add_all_indicators
    
    print("🔧 Computing Technical Indicators...")
    df = add_all_indicators(df)
    
    # Add Williams %R 140 specifically
    df['williams_r'] = calculate_williams_r(df, PERIOD)
    df['williams_r_prev'] = df['williams_r'].shift(1)
    
    # Add Mock MTF (Necessary for model input)
    print("🔧 Approximating MTF Features...")
    # (Simplified MTF Logic similar to backtest_high_win_rate.py)
    # For accurate ML, we really need the actual MTF columns.
    # The training used 'BTC_5m_mtf_labeled.csv' which has them pre-calc.
    # Here we are generating them.
    
    # 1H Resample
    df_1h = df.set_index('timestamp').resample('1h').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    })
    df_1h = add_all_indicators(df_1h)
    df_1h = df_1h.add_suffix('_1h')
    
    # Merge back 1h features
    df = pd.merge_asof(df.sort_values('timestamp'), df_1h, left_on='timestamp', right_index=True)
    
    # 4H Resample
    df_4h = df.set_index('timestamp').resample('4h').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    })
    df_4h = add_all_indicators(df_4h)
    df_4h = df_4h.add_suffix('_4h')
    
    # Merge back 4h features
    df = pd.merge_asof(df, df_4h, left_on='timestamp', right_index=True)
    
    # Trend Filter (EMA 200)
    df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
    df['vol_sma_20'] = df['volume'].rolling(20).mean()

    # Fill NaNs
    df.fillna(0, inplace=True)

    print("🤖 Predicting with ML...")
    # Prepare X
    # Ensure all feature cols exist validation
    missing = [c for c in FEATURE_COLS if c not in df.columns]
    if missing:
        print(f"⚠️ Missing features: {missing}")
        # Add zeros
        for c in missing: df[c] = 0
            
    X = df[FEATURE_COLS]
    probs = model.predict_proba(X)[:, 1]
    df['ml_conf'] = probs
    
    # Create Loop for Thresholds
    thresholds = [0.60, 0.65, 0.70, 0.75, 0.80]
    results = []

    print("\n" + "="*60)
    print(f"{'Thresh':<8} {'Trades':<8} {'Win Rate':<10} {'PnL':<10} {'Avg Conf':<10}")
    print("="*60)

    for thresh in thresholds:
        trades = []
        position = None
        
        for i in range(200, len(df)):
            row = df.iloc[i]
            
            # Manage Position
            if position:
                outcome = None
                exit_px = 0
                if position['type'] == 'LONG':
                    if row['high'] >= position['tp']: outcome='WIN'; exit_px=position['tp']
                    elif row['low'] <= position['sl']: outcome='LOSS'; exit_px=position['sl']
                else:
                    if row['low'] <= position['tp']: outcome='WIN'; exit_px=position['tp']
                    elif row['high'] >= position['sl']: outcome='LOSS'; exit_px=position['sl']
                
                if outcome:
                    pnl = (exit_px - position['entry']) / position['entry']
                    if position['type'] == 'SHORT': pnl = -pnl
                    pnl -= (FEE_PCT*2)
                    trades.append({'outcome': outcome, 'pnl': pnl, 'conf': position['conf']})
                    position = None
                continue
                
            # Check Signals
            curr_wr = row['williams_r']
            prev_wr = row['williams_r_prev']
            conf = row['ml_conf']
            
            # Filters
            is_uptrend = row['close'] > row['ema_200']
            is_downtrend = row['close'] < row['ema_200']
            is_vol = row['volume'] > (1.5 * row['vol_sma_20'])
            
            if not is_vol: continue
            if conf < thresh: continue # ML Filter
            
            if is_uptrend and prev_wr < LONG_THRESH and curr_wr >= LONG_THRESH:
                entry = row['close']
                position = {
                    'type': 'LONG', 'entry': entry,
                    'tp': entry*(1+TP_PCT), 'sl': entry*(1-SL_PCT),
                    'time': row['timestamp'],
                    'conf': conf
                }
                
            elif is_downtrend and prev_wr > SHORT_THRESH and curr_wr <= SHORT_THRESH:
                entry = row['close']
                position = {
                    'type': 'SHORT', 'entry': entry,
                    'tp': entry*(1-TP_PCT), 'sl': entry*(1+SL_PCT),
                    'time': row['timestamp'],
                    'conf': conf
                }

        # Results for this thresh
        if not trades:
            print(f"{thresh:<8} {'0':<8} {'0.00%':<10} {'0.00%':<10} {'0.00':<10}")
            continue

        df_t = pd.DataFrame(trades)
        wins = len(df_t[df_t['outcome']=='WIN'])
        total = len(df_t)
        wr = wins / total * 100
        pnl = df_t['pnl'].sum() * 100
        avg_conf = df_t['conf'].mean()
        
        print(f"{thresh:<8} {total:<8} {wr:<10.2f} {pnl:<10.2f} {avg_conf:<10.2f}")
        results.append({'thresh': thresh, 'wr': wr, 'pnl': pnl})

if __name__ == "__main__":
    run_backtest()
