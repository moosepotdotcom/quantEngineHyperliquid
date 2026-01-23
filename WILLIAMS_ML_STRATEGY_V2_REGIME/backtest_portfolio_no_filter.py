#!/usr/bin/env python3
"""
PORTFOLIO BACKTEST (Universal Model - No Filter)
Target: Jan 2 - Jan 23
Coins: BTC, ETH, SOL, AVAX, SUI
Model: MTF Scalper V2 (Universal)
Config: TP 0.7% | SL 1.5% | Conf > 0.65
Filter: NONE
"""

import pandas as pd
import numpy as np
from datetime import datetime
import requests
import warnings
import sys
import os
import pickle
import xgboost as xgb

# Add root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.feature_engineer import add_all_indicators

warnings.filterwarnings('ignore')

print("\n" + "="*70)
print("🚀 PORTFOLIO BACKTEST - UNIVERSAL MODEL (NO FILTER)")
print("Coins: BTC, ETH, SOL, AVAX, SUI")
print("Target: Jan 2 - Jan 23 | Conf > 0.65")
print("="*70)

# 1. LOAD MODEL
print("\n📦 Loading MTF Scalper V2 (Universal)...")
model_path = '/Users/alifiyaa/Downloads/quantEngineHyperliquid/EXPORT/models/mtf_scalper_5m_v2.json'

if not os.path.exists(model_path):
    print(f"❌ Model not found: {model_path}")
    exit(1)

xgb_model = xgb.XGBClassifier()
xgb_model.load_model(model_path)
print("✅ XGBoost Model Loaded")

# Load feature names
feat_path = '/Users/alifiyaa/Downloads/quantEngineHyperliquid/EXPORT/models/feature_names.pkl'
if not os.path.exists(feat_path):
    feat_path = '/Users/alifiyaa/Downloads/quantEngineHyperliquid/training/models/hybrid_v1/feature_names.pkl'

with open(feat_path, 'rb') as f:
    feature_names = pickle.load(f)
print(f"✅ Features Loaded: {len(feature_names)}")

# 2. DEFINITIONS
COINS = ['BTC', 'ETH', 'SOL', 'AVAX', 'SUI']
TP_PCT = 0.007
SL_PCT = 0.015
CONF_THRESH = 0.65

def fetch_binance_history(symbol, interval='5m', start_str='2026-01-02', end_str='2026-01-23'):
    """Fetch history from Binance"""
    symbol_pair = f"{symbol}USDT"
    base_url = 'https://api.binance.com/api/v3/klines'
    
    start_ts = int(pd.Timestamp(start_str).timestamp() * 1000)
    end_ts = int(pd.Timestamp(end_str).timestamp() * 1000)
    
    all_data = []
    current_start = start_ts
    
    while current_start < end_ts:
        params = {'symbol': symbol_pair, 'interval': interval, 'startTime': current_start, 'limit': 1000}
        try:
            resp = requests.get(base_url, params=params, timeout=10)
            data = resp.json()
            if not data or not isinstance(data, list): break
            
            for k in data:
                all_data.append({
                    'timestamp': pd.to_datetime(k[0], unit='ms'),
                    'open': float(k[1]), 'high': float(k[2]), 'low': float(k[3]), 'close': float(k[4]), 'volume': float(k[5])
                })
            
            current_start = data[-1][6] + 1
            # print(f"   {symbol}: {len(all_data)} candles...", end="\r")
            if current_start >= end_ts: break
        except Exception as e:
            print(f"❌ Error {symbol}: {e}")
            break
            
    return pd.DataFrame(all_data)

# 3. BACKTEST LOOP
portfolio_trades = []

for coin in COINS:
    print(f"\n🔄 Processing {coin}...")
    
    # A. Fetch Data
    df = fetch_binance_history(coin)
    if df.empty:
        print(f"   ⚠️ No data for {coin}")
        continue
        
    print(f"   ✅ Fetched {len(df)} candles ({df['timestamp'].min()} - {df['timestamp'].max()})")
    
    # B. Generate Features
    df = add_all_indicators(df)
    for feat in feature_names:
        if feat not in df.columns: df[feat] = 0
    df = df.dropna().reset_index(drop=True)
    
    # C. Predict
    X = df[feature_names].values
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    probas = xgb_model.predict_proba(X)
    
    # D. Simulate
    current_position = None
    trades = []
    
    for i, row in df.iterrows():
        timestamp = row['timestamp']
        
        # Position Management
        if current_position:
            h, l = row['high'], row['low']
            direction = current_position['dir']
            outcome = None
            
            if direction == 'LONG':
                if h >= current_position['tp']: outcome = 'WIN'
                elif l <= current_position['sl']: outcome = 'LOSS'
            else:
                if l <= current_position['tp']: outcome = 'WIN'
                elif h >= current_position['sl']: outcome = 'LOSS'
            
            if outcome:
                hold = (timestamp - current_position['time']).total_seconds()/3600
                trades.append({**current_position, 'outcome': outcome, 'hold': hold})
                current_position = None
            continue
            
        # Signal
        p_long = probas[i, 1]
        p_short = probas[i, 0]
        
        signal = None
        conf = 0.0
        
        if p_long > CONF_THRESH: signal = 'LONG'; conf = p_long
        elif p_short > CONF_THRESH: signal = 'SHORT'; conf = p_short
        
        if signal:
            # NO REGIME FILTER
            price = row['close']
            tp_p = price * (1+TP_PCT) if signal == 'LONG' else price * (1-TP_PCT)
            sl_p = price * (1-SL_PCT) if signal == 'LONG' else price * (1+SL_PCT)
            
            current_position = {
                'coin': coin, 'time': timestamp, 'dir': signal, 'price': price,
                'tp': tp_p, 'sl': sl_p, 'conf': conf
            }
            
    print(f"   📊 {coin}: {len(trades)} trades")
    portfolio_trades.extend(trades)

# 4. AGGREGATE RESULTS
print("\n" + "="*70)
print("🏆 PORTFOLIO RESULTS (5 Coins)")
print("="*70)

total = len(portfolio_trades)
wins = len([t for t in portfolio_trades if t['outcome'] == 'WIN'])
losses = len([t for t in portfolio_trades if t['outcome'] == 'LOSS'])

if total > 0:
    wr = wins/total*100
    print(f"Total Trades: {total}")
    print(f"Win Rate:     {wr:.2f}% ({wins} W / {losses} L)")
    
    capital = 53
    lev = 27
    bp = capital * lev
    
    pnl_usd = (wins * bp * TP_PCT) - (losses * bp * SL_PCT)
    roi = pnl_usd / capital * 100
    
    print(f"Total P&L:    ${pnl_usd:.2f}")
    print(f"ROI:          {roi:.2f}%")
    print(f"Final Bal:    ${capital+pnl_usd:.2f}")
    
    # Coin Breakdown
    print("\n   Breakdown by Coin:")
    df_res = pd.DataFrame(portfolio_trades)
    breakdown = df_res.groupby('coin')['outcome'].value_counts().unstack().fillna(0)
    print(breakdown)

else:
    print("No trades generated.")

print("\n✅ DONE")
