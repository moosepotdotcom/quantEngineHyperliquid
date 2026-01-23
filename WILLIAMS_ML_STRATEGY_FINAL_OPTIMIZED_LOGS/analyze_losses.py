#!/usr/bin/env python3
"""
DEEP DIVE: Small Cap Loss Analysis (SOL, AVAX, SUI)
Target: Uncover why Win Rate is lower than BTC/ETH.
Hypothesis:
1. Increased Volatility (Wicks) hitting tight SL.
2. Regime Lag (EMA 20/50 too slow for explosive moves).
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
    exit()

# Load Data Reuse Function
def fetch_data(coin):
    # Reuse valid fetch logic or just quick fetch for the specific coin
    url = "https://api.hyperliquid.xyz/info"
    # Fetch last 20 days roughly
    end_ts = int(pd.Timestamp("2026-01-23").timestamp() * 1000)
    start_ts = int(pd.Timestamp("2026-01-02").timestamp() * 1000)
    
    all_data = []
    curr = end_ts
    while curr > start_ts:
        start = int(max(start_ts, curr - (2000 * 5 * 60 * 1000)))
        curr_int = int(curr)
        req = {"type": "candleSnapshot", "req": {"coin": coin, "interval": "5m", "startTime": start, "endTime": curr_int}}
        resp = requests.post(url, json=req).json()
        if not resp: break
        chunk = pd.DataFrame(resp)
        all_data.append(chunk)
        curr = chunk.iloc[0]['t'] - 1
        
    df = pd.concat(all_data).sort_values('t').drop_duplicates('t').reset_index(drop=True)
    df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
    df['open'] = df['o'].astype(float)
    df['high'] = df['h'].astype(float)
    df['low'] = df['l'].astype(float)
    df['close'] = df['c'].astype(float)
    df['volume'] = df['v'].astype(float)
    return df

# Feature Eng
PERIOD = 21
def prepare_data(df):
    df = df.copy()
    # Williams %R
    high = df['high'].rolling(PERIOD).max()
    low = df['low'].rolling(PERIOD).min()
    denom = (high - low).replace(0, np.nan)
    df['williams_r'] = -100 * (high - df['close']) / denom
    df['williams_r_prev'] = df['williams_r'].shift(1)
    
    # ATR for Volatility Analysis
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift(1)).abs()
    tr3 = (df['low'] - df['close'].shift(1)).abs()
    df['atr'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1).rolling(14).mean()
    df['atr_pct'] = df['atr'] / df['close'] * 100 # ATR as % of Price (Volatility Metric)
    
    # Regime EMAs
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    # ML Features (Simple subset for prediction)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi_14'] = 100 - (100 / (1 + rs))
    df['vol_change'] = df['volume'].pct_change()
    ema200 = df['close'].ewm(span=200, adjust=False).mean()
    df['ema_200_dist'] = (df['close'] - ema200) / ema200
    
    # ATR 14 (duplicate for model name match)
    df['atr_14'] = df['atr'] 

    return df.dropna()

# Analyze
def analyze_coin(coin, model):
    print(f"\n🔍 INVESTIGATING {coin}...")
    df = fetch_data(coin)
    df = prepare_data(df)
    
    features = ['williams_r', 'rsi_14', 'atr_14', 'vol_change', 'ema_200_dist']
    X = df[features].values
    probs = model.predict_proba(X)[:, 1]
    
    trades = []
    active_trade = None
    
    TP_PCT = 0.007
    SL_PCT = 0.015
    CONF = 0.65
    
    for i in range(len(df)):
        row = df.iloc[i]
        
        # Check Exit
        if active_trade:
            # Check if stopped out by Volatility (High/Low wick)
            win = False
            loss = False
            
            if active_trade['dir'] == 'LONG':
                if row['high'] >= active_trade['tp']: win = True
                elif row['low'] <= active_trade['sl']: loss = True
            else:
                if row['low'] <= active_trade['tp']: win = True
                elif row['high'] >= active_trade['sl']: loss = True
                
            if win or loss:
                active_trade['outcome'] = 'WIN' if win else 'LOSS'
                active_trade['exit_time'] = row['timestamp']
                active_trade['exit_atr_pct'] = row['atr_pct'] # Volatility at exit
                trades.append(active_trade)
                active_trade = None
            continue
            
        # Check Entry
        wr = row['williams_r']
        wr_prev = row['williams_r_prev']
        prob = probs[i]
        
        signal = None
        if wr_prev < -20 and wr >= -20 and prob >= CONF: signal = 'LONG'
        elif wr_prev > -80 and wr <= -80 and prob >= CONF: signal = 'SHORT'
        
        if signal:
            # Regime Shield
            e20, e50 = row['ema_20'], row['ema_50']
            regime = 'RANGING'
            if e20 > e50 * 1.001: regime = 'BULLISH'
            elif e20 < e50 * 0.999: regime = 'BEARISH'
            
            allowed, reason = should_trade(signal, regime)
            if allowed:
                px = row['close']
                tp = px * (1+TP_PCT) if signal == 'LONG' else px * (1-TP_PCT)
                sl = px * (1-SL_PCT) if signal == 'LONG' else px * (1+SL_PCT)
                
                active_trade = {
                    'coin': coin,
                    'entry_time': row['timestamp'],
                    'dir': signal,
                    'entry_price': px,
                    'tp': tp, 
                    'sl': sl,
                    'entry_atr_pct': row['atr_pct'], # VOLATILITY AT ENTRY
                    'regime': regime
                }

    # Deep Dive on Losses
    losses = [t for t in trades if t['outcome'] == 'LOSS']
    wins = [t for t in trades if t['outcome'] == 'WIN']
    
    print(f"   Trades: {len(trades)} | Win Rate: {len(wins)/len(trades)*100:.1f}%" if trades else "   No Trades")
    
    if losses:
        avg_loss_atr = np.mean([t['entry_atr_pct'] for t in losses])
        avg_win_atr = np.mean([t['entry_atr_pct'] for t in wins]) if wins else 0
        
        print(f"   📉 Avg Volatility (ATR %) during LOSSES: {avg_loss_atr:.3f}%")
        print(f"   📈 Avg Volatility (ATR %) during WINS:   {avg_win_atr:.3f}%")
        
        if avg_loss_atr > avg_win_atr:
            print("   ⚠️ DIAGNOSIS: Losses occur in higher volatility conditions (Wicks stop you out).")
        
        print("\n   Detailed Loss Log:")
        for l in losses[-5:]: # Show last 5
            print(f"     {l['entry_time']} {l['dir']} | Regime: {l['regime']} | Volatility: {l['entry_atr_pct']:.3f}%")
            
# Run
model = xgb.XGBClassifier()
model.load_model('model_v1.json')

for coin in ['SOL', 'AVAX', 'SUI']:
    analyze_coin(coin, model)
