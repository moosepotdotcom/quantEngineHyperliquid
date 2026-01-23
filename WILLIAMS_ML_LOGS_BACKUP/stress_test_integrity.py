#!/usr/bin/env python3
"""
INTEGRITY STRESS TEST
Target: Jan 2 - Jan 23
Mode: PESSIMISTIC EXECUTION (Anti-Cheating)
Logic: If Low <= SL, it is a LOSS. period.
       (Even if High >= TP in the same candle).
       This assumes the worst-case scenario: Price crashed to SL before rallying to TP.
"""

import pandas as pd
import numpy as np
import requests
import xgboost as xgb
import os
import sys

# Import components
sys.path.append(os.getcwd())
try:
    from trend_filter import get_market_regime, should_trade
except ImportError:
    print("❌ Run from WILLIAMS_ML_STRATEGY_FINAL directory")
    exit(1)

# Load Model
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
DATA = {c: fetch_data(c) for c in COINS}

# Simulation
def simulate_pessimistic(run_name, tp_pct, sl_pct):
    trades = []
    
    for coin, df in DATA.items():
        in_trade = False
        trade_dir = None
        entry_price = 0
        tp_price = 0
        sl_price = 0
        
        for i, row in df.iterrows():
            if in_trade:
                curr_h, curr_l = row['high'], row['low']
                win = False
                loss = False
                
                # INTEGRITY CHECK: CHECK STOP LOSS FIRST
                # If SL is hit, GAME OVER. We do not check for TP subsequently.
                # This eliminates "Lucky Wicks" where price hits both levels in one candle.
                
                if trade_dir == 'LONG':
                    if curr_l <= sl_price: 
                        loss = True
                    elif curr_h >= tp_price: 
                        win = True
                else: # SHORT
                    if curr_h >= sl_price: 
                        loss = True
                    elif curr_l <= tp_price: 
                        win = True
                    
                if win or loss:
                    # Assumed 3x leverage ($159 Size) for PnL Calc
                    pos_size = 159 
                    pnl_pct = tp_pct if win else -sl_pct
                    raw_pnl = pos_size * pnl_pct
                    fees = pos_size * 0.0007
                    net_pnl = raw_pnl - fees
                    
                    trades.append(net_pnl)
                    in_trade = False
                continue
            
            # Entry
            prob = row['proba']
            if prob < 0.65: continue
            
            wr = row['williams_r']
            wr_p = row['williams_r_prev']
            
            signal = None
            if wr_p < -20 and wr >= -20: signal = 'LONG'
            elif wr_p > -80 and wr <= -80: signal = 'SHORT'
            
            if signal:
                e20 = row['ema_20']
                e50 = row['ema_50']
                regime = 'RANGING'
                if e20 > e50 * 1.001: regime = 'BULLISH'
                elif e20 < e50 * 0.999: regime = 'BEARISH'
                
                if signal == 'LONG' and regime != 'BULLISH': continue
                if signal == 'SHORT' and regime != 'BEARISH': continue
                
                in_trade = True
                trade_dir = signal
                entry_price = row['close']
                if signal == 'LONG':
                    tp_price = entry_price * (1 + tp_pct)
                    sl_price = entry_price * (1 - sl_pct)
                else:
                    tp_price = entry_price * (1 - tp_pct)
                    sl_price = entry_price * (1 + sl_pct)
                    
    # Metrics Calc
    if not trades: 
        print(f"📊 {run_name.upper()}: No Trades")
        return
    
    profits = np.array(trades)
    wins = profits[profits > 0]
    
    total_pnl = np.sum(profits)
    win_rate = len(wins) / len(profits) * 100
    
    print(f"\n📊 {run_name.upper()} REPORT (PESSIMISTIC MODE)")
    print(f"   Trades: {len(trades)}")
    print(f"   Win Rate: {win_rate:.2f}%")
    print(f"   Total Net PnL (Est): ${total_pnl:.2f}")

print("\nrunning Stress Test...")
simulate_pessimistic("Optimistic Bias Check (0.9/2.0)", 0.009, 0.020)
