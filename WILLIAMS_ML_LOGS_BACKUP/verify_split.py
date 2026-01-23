#!/usr/bin/env python3
"""
STATISTICAL INTEGRITY PROOF: SPLIT-SAMPLE VALIDATION
Phase 1 (Training): Jan 2 - Jan 14 -> Find Best Params
Phase 2 (Testing):  Jan 15 - Jan 23 -> Verify Performance (Out of Sample)
"""

import pandas as pd
import numpy as np
import requests
import xgboost as xgb
import itertools
import os
import sys

# Import components
sys.path.append(os.getcwd())
try:
    from trend_filter import get_market_regime, should_trade
except ImportError:
    print("❌ Run from WILLIAMS_ML_STRATEGY_FINAL directory")
    exit(1)

# Load Model (Trained pre-Jan 1, so fully valid for both sets)
model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model_v1.json')
xgb_model = xgb.XGBClassifier()
xgb_model.load_model(model_path)

FEATURES = ['williams_r', 'rsi_14', 'atr_14', 'vol_change', 'ema_200_dist']
PERIOD = 21

# Data Fetch
def fetch_data(coin):
    url = "https://api.hyperliquid.xyz/info"
    start_ts = int(pd.Timestamp("2026-01-02").timestamp() * 1000)
    end_ts = int(pd.Timestamp("2026-01-23").timestamp() * 1000)
    
    all_data = []
    curr = end_ts
    while curr > start_ts:
        start = int(max(start_ts, curr - (2000 * 5 * 60 * 1000)))
        curr_int = int(curr)
        req = {"type": "candleSnapshot", "req": {"coin": coin, "interval": "5m", "startTime": start, "endTime": curr_int}}
        try:
            resp = requests.post(url, json=req, timeout=10).json()
            if not resp: break
            chunk = pd.DataFrame(resp)
            all_data.append(chunk)
            curr = chunk.iloc[0]['t'] - 1
        except: break
            
    df = pd.concat(all_data).sort_values('t').drop_duplicates('t').reset_index(drop=True)
    df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
    cols = ['o', 'h', 'l', 'c', 'v']
    new_cols = ['open', 'high', 'low', 'close', 'volume']
    for c, n in zip(cols, new_cols):
        df[n] = df[c].astype(float)
        
    # Features
    df['high_roll'] = df['high'].rolling(PERIOD).max()
    df['low_roll'] = df['low'].rolling(PERIOD).min()
    denom = (df['high_roll'] - df['low_roll']).replace(0, np.nan)
    df['williams_r'] = -100 * (df['high_roll'] - df['close']) / denom
    df['williams_r_prev'] = df['williams_r'].shift(1)
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi_14'] = 100 - (100 / (1 + rs))
    
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift(1)).abs()
    tr3 = (df['low'] - df['close'].shift(1)).abs()
    df['atr_14'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1).rolling(14).mean()
    
    df['vol_change'] = df['volume'].pct_change()
    ema = df['close'].ewm(span=200, adjust=False).mean()
    df['ema_200_dist'] = (df['close'] - ema) / ema
    
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    df = df.dropna().reset_index(drop=True)
    X = df[FEATURES].values
    df['proba'] = xgb_model.predict_proba(X)[:, 1]
    
    return df

COINS = ['BTC', 'ETH', 'SOL', 'AVAX', 'SUI']
print("📥 Fetching Data...")
RAW_DATA = {c: fetch_data(c) for c in COINS}

# Split Data
SPLIT_DATE = pd.Timestamp("2026-01-14")
TRAIN_DATA = {}
TEST_DATA = {}

for c, df in RAW_DATA.items():
    TRAIN_DATA[c] = df[df['timestamp'] < SPLIT_DATE]
    TEST_DATA[c] = df[df['timestamp'] >= SPLIT_DATE]

print(f"✂️ Split Date: {SPLIT_DATE}")
print(f"   Training Set: Jan 2 - Jan 14")
print(f"   Testing Set:  Jan 14 - Jan 23")

# Logic
def simulate(data_dict, tp_pct, sl_pct, conf_thresh=0.65):
    wins = 0
    losses = 0
    
    for coin, df in data_dict.items():
        in_trade = False
        trade_dir = None
        tp_price = 0
        sl_price = 0
        
        for i, row in df.iterrows():
            if in_trade:
                h, l = row['high'], row['low']
                win, loss = False, False
                
                # Pessimistic Check just to be safe
                if trade_dir == 'LONG':
                    if l <= sl_price: loss = True
                    elif h >= tp_price: win = True
                else: 
                    if h >= sl_price: loss = True
                    elif l <= tp_price: win = True
                    
                if win: wins += 1; in_trade = False
                elif loss: losses += 1; in_trade = False
                continue
                
            # Entry
            if row['proba'] < conf_thresh: continue
            wr = row['williams_r']
            wr_p = row['williams_r_prev']
            
            signal = None
            if wr_p < -20 and wr >= -20: signal = 'LONG'
            elif wr_p > -80 and wr <= -80: signal = 'SHORT'
            
            if signal:
                e20, e50 = row['ema_20'], row['ema_50']
                regime = 'RANGING'
                if e20 > e50 * 1.001: regime = 'BULLISH'
                elif e20 < e50 * 0.999: regime = 'BEARISH'
                
                if signal == 'LONG' and regime != 'BULLISH': continue
                if signal == 'SHORT' and regime != 'BEARISH': continue
                
                in_trade = True
                trade_dir = signal
                if signal == 'LONG':
                    tp_price = row['close'] * (1 + tp_pct)
                    sl_price = row['close'] * (1 - sl_pct)
                else:
                    tp_price = row['close'] * (1 - tp_pct)
                    sl_price = row['close'] * (1 + sl_pct)

    return wins, losses

# 1. OPTIMIZE ON TRAINING SET
print("\n🔍 PHASE 1: Optimizing on Training Set...")
best_score = -999
best_params = (0, 0)
base_params = (0.7, 1.5)

# Small Grid
tp_ranges = [0.5, 0.7, 0.9, 1.2, 1.5]
sl_ranges = [1.0, 1.5, 2.0, 2.5]

for tp, sl in itertools.product(tp_ranges, sl_ranges):
    w, l = simulate(TRAIN_DATA, tp/100, sl/100)
    total = w + l
    if total == 0: continue
    
    # Simple Score: Net PnL Factor
    score = (w * tp) - (l * sl)
    
    if score > best_score:
        best_score = score
        best_params = (tp, sl)
        
print(f"   🏆 Best Training Params: TP {best_params[0]}% | SL {best_params[1]}%")

# 2. VALIDATE ON TEST SET
print("\n⚖️ PHASE 2: Validating on Test Set (Out of Sample)...")

# Run Baseline
bw, bl = simulate(TEST_DATA, 0.7/100, 1.5/100)
base_pnl = (bw * 0.7) - (bl * 1.5)

# Run Optimized
ow, ol = simulate(TEST_DATA, best_params[0]/100, best_params[1]/100)
opt_pnl = (ow * best_params[0]) - (ol * best_params[1])

print(f"\nRESULTS ON UNSEEN DATA (Jan 14 - Jan 23):")
print(f"1. Baseline (0.7/1.5):  {bw}W / {bl}L | PnL Factor: {base_pnl:.2f}")
print(f"2. Optimized ({best_params[0]}/{best_params[1]}): {ow}W / {ol}L | PnL Factor: {opt_pnl:.2f}")

if opt_pnl > base_pnl:
    print("\n✅ VALIDATED: The optimized parameters outperformed baseline on unseen data.")
else:
    print("\n❌ FAILED: The optimized parameters overfitted the training set.")
