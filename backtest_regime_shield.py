#!/usr/bin/env python3
"""
REGIME SHIELD BACKTEST - CORRECTED MODEL (MTF Scalper V2)
Target: Jan 2 - Jan 23
Model: MTF Scalper V2 (XGBoost Binary)
Config: TP 0.7% | SL 1.5% | Conf > 0.65
Data: CSV History (Jan 2-11) + API (Jan 12-23)
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
sys.path.append(os.getcwd())
from utils.feature_engineer import add_all_indicators
from utils.trend_filter import get_market_regime, should_trade

warnings.filterwarnings('ignore')

print("\n" + "="*70)
print("🛡️ REGIME SHIELD BACKTEST - MTF SCALPER V2")
print("Target: Jan 2 - Jan 23 | Conf > 0.65")
print("="*70)

# 1. LOAD MODEL
print("\n📦 Loading MTF Scalper V2...")
model_path = '/Users/alifiyaa/Downloads/quantEngineHyperliquid/EXPORT/models/mtf_scalper_5m_v2.json'
meta_path = '/Users/alifiyaa/Downloads/quantEngineHyperliquid/EXPORT/models/mtf_scalper_5m_v2_metadata.json'

if not os.path.exists(model_path):
    print(f"❌ Model not found: {model_path}")
    exit(1)

xgb_model = xgb.XGBClassifier()
xgb_model.load_model(model_path)
print("✅ XGBoost Model Loaded")

# Load feature names (Need to find where they are stored, usually pickle or metadata)
# Try EXPORT/models/feature_names.pkl or assume standard list
# mtf_scalper_5m_trio uses 231 features. V2 likely same.
feat_path = '/Users/alifiyaa/Downloads/quantEngineHyperliquid/EXPORT/models/feature_names.pkl'
if not os.path.exists(feat_path):
    # Fallback to hybrid features
    feat_path = '/Users/alifiyaa/Downloads/quantEngineHyperliquid/training/models/hybrid_v1/feature_names.pkl'

with open(feat_path, 'rb') as f:
    feature_names = pickle.load(f)
print(f"✅ Features Loaded: {len(feature_names)}")

# 2. LOAD DATA (Binance History as Proxy for Backtest Stability)
print("\nDATASOURCE: Fetching Binance History (Robust)...")

def fetch_binance_history(symbol='BTCUSDT', interval='5m', start_str='2026-01-02', end_str='2026-01-23'):
    base_url = 'https://api.binance.com/api/v3/klines'
    
    start_ts = int(pd.Timestamp(start_str).timestamp() * 1000)
    end_ts = int(pd.Timestamp(end_str).timestamp() * 1000)
    
    all_data = []
    current_start = start_ts
    
    while current_start < end_ts:
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': current_start,
            'limit': 1000
        }
        
        try:
            resp = requests.get(base_url, params=params, timeout=10)
            data = resp.json()
            
            if not data or not isinstance(data, list):
                break
                
            for k in data:
                all_data.append({
                    'timestamp': pd.to_datetime(k[0], unit='ms'),
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5])
                })
            
            # Update start time to last candle + 1ms
            last_close_time = data[-1][6]
            current_start = last_close_time + 1
            
            print(f"   Fetched {len(all_data)} candles...", end="\r")
            
            if current_start >= end_ts:
                break
                
        except Exception as e:
            print(f"❌ Error: {e}")
            break
            
    return pd.DataFrame(all_data)

df = fetch_binance_history()
print(f"\n✅ Fetched {len(df)} candles")

if len(df) > 0:
    print(f"   Period: {df['timestamp'].min()} to {df['timestamp'].max()}")

# 3. FEATURES & REGIME
print("\n🔧 Generating Features & Regimes...")
# ... (Rest of logic is same)

# 3. FEATURES & REGIME
print("\n🔧 Generating Features & Regimes...")
df = add_all_indicators(df)

# Regime Calculation
regimes = []
ema20s = df['ema_20']
ema50s = df['ema_50']
for i in range(len(df)):
    if i < 50: 
        regimes.append('UNKNOWN')
        continue
    e20 = ema20s.iloc[i]
    e50 = ema50s.iloc[i]
    if e20 > e50 * 1.005: r = 'BULLISH'
    elif e20 < e50 * 0.995: r = 'BEARISH'
    else: r = 'RANGING'
    regimes.append(r)
df['regime'] = regimes

# Fill Features
for feat in feature_names:
    if feat not in df.columns: df[feat] = 0

df = df.dropna().reset_index(drop=True)

# 4. INFERENCE
print("\n🤖 Generating Predictions...")
X = df[feature_names].values
X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

# Binary Model: predict_proba returns [prob_0, prob_1]
# Mapping: 0=SHORT, 1=LONG
probas = xgb_model.predict_proba(X)
prob_short = probas[:, 0]
prob_long = probas[:, 1]

# 5. SIMULATION
print("\n🔄 Running Simulation...")
tp_pct = 0.007
sl_pct = 0.015
conf_thresh = 0.65

trades = []
current_position = None
shield_stats = {'BULLISH': 0, 'BEARISH': 0, 'RANGING': 0}

for i, row in df.iterrows():
    timestamp = row['timestamp']
    
    # Manage Open Position
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

    # Signal Logic
    p_long = prob_long[i]
    p_short = prob_short[i]
    regime = row['regime']
    
    signal = None
    conf = 0.0
    
    if p_long > conf_thresh:
        signal = 'LONG'; conf = p_long
    elif p_short > conf_thresh:
        signal = 'SHORT'; conf = p_short
        
    if signal:
        # Regime Shield
        is_valid, reason = should_trade(signal, regime)
        
        if is_valid:
            price = row['close']
            tp_p = price * (1+tp_pct) if signal == 'LONG' else price * (1-tp_pct)
            sl_p = price * (1-sl_pct) if signal == 'LONG' else price * (1+sl_pct)
            
            current_position = {
                'time': timestamp, 'dir': signal, 'price': price,
                'tp': tp_p, 'sl': sl_p, 'conf': conf, 'regime': regime
            }
        else:
            shield_stats[regime] += 1

# 6. RESULTS
print("\n" + "="*70)
print(f"📊 FINAL RESULTS (MTF Scalper V2 + Regime Shield)")
print(f"Target: Jan 2 - Jan 23")
print("="*70)

wins = len([t for t in trades if t['outcome'] == 'WIN'])
losses = len([t for t in trades if t['outcome'] == 'LOSS'])
total = wins + losses

print(f"Total Trades: {total}")
print(f"🛡️ Shield Blocked: {sum(shield_stats.values())} trades")
print(f"   Detailed: {shield_stats}")

if total > 0:
    wr = wins/total*100
    print(f"\nWin Rate: {wr:.2f}%")
    
    capital = 53
    lev = 27
    bp = capital * lev
    pnl = (wins * bp * tp_pct) - (losses * bp * sl_pct)
    roi = pnl/capital*100
    
    print(f"P&L: ${pnl:.2f}")
    print(f"ROI: {roi:.2f}%")
else:
    print("No trades.")
    
print("\n✅ DONE")
