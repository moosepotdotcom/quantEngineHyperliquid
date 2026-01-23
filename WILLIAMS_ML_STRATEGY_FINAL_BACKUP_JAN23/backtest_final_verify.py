#!/usr/bin/env python3
"""
FINAL BACKTEST VERIFICATION
Target: Jan 2 - Jan 23
Ensures WILLIAMS_ML_STRATEGY_FINAL components (trend_filter, model) are accurate.
"""

import pandas as pd
import numpy as np
import requests
import warnings
import sys
import os
import xgboost as xgb

# Import Local Components
from trend_filter import get_market_regime, should_trade

warnings.filterwarnings('ignore')

print("\n" + "="*70)
print("🛡️ REGIME SHIELD PORTFOLIO BACKTEST - FINAL VERIFICATION")
print("Target: Jan 2 - Jan 23 | Conf > 0.65")
print("Coins: BTC, ETH, SOL, AVAX, SUI")
print("="*70)

# 1. LOAD MODEL (model_v1.json)
model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model_v1.json')
if not os.path.exists(model_path):
    print(f"❌ Model not found: {model_path}")
    exit(1)

xgb_model = xgb.XGBClassifier()
xgb_model.load_model(model_path)
print(f"✅ XGBoost Model Loaded ({model_path})")

FEATURES = ['williams_r', 'rsi_14', 'atr_14', 'vol_change', 'ema_200_dist']
PERIOD = 21

# 2. FEATURE ENGINEERING (Copied from live_trader.py logic)
def add_features(df):
    df = df.copy()
    high = df['high'].rolling(PERIOD).max()
    low = df['low'].rolling(PERIOD).min()
    denom = (high - low).replace(0, np.nan)
    df['williams_r'] = -100 * (high - df['close']) / denom
    df['williams_r_prev'] = df['williams_r'].shift(1)
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi_14'] = 100 - (100 / (1 + rs))
    
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift(1)).abs()
    tr3 = (df['low'] - df['close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr_14'] = tr.rolling(14).mean()
    
    df['vol_change'] = df['volume'].pct_change()
    
    ema = df['close'].ewm(span=200, adjust=False).mean()
    df['ema_200_dist'] = (df['close'] - ema) / ema
    
    return df.dropna()

def fetch_hyperliquid_history(coin='BTC', interval='5m', start_str='2026-01-02', end_str='2026-01-23'):
    """Fetch history from Hyperliquid API (Chunked)"""
    url = "https://api.hyperliquid.xyz/info"
    start_ts = int(pd.Timestamp(start_str).timestamp() * 1000)
    end_ts = int(pd.Timestamp(end_str).timestamp() * 1000)
    
    all_data = []
    current_end = end_ts
    chunk_dur_ms = 2000 * 5 * 60 * 1000 
    
    print(f"   Fetching ({coin})...", end="\r")
    
    while current_end > start_ts:
        current_start = max(start_ts, current_end - chunk_dur_ms)
        payload = {
            "type": "candleSnapshot",
            "req": {"coin": coin, "interval": interval, "startTime": current_start, "endTime": current_end}
        }
        try:
            resp = requests.post(url, json=payload, timeout=10)
            data = resp.json()
            if not data: break
            
            chunk = []
            for c in data:
                chunk.append({
                    'timestamp': pd.to_datetime(c['t'], unit='ms'),
                    'open': float(c['o']), 'high': float(c['h']), 'low': float(c['l']), 'close': float(c['c']), 'volume': float(c['v'])
                })
            all_data = chunk + all_data
            first_ts = data[0]['t']
            current_end = first_ts - 1
            if current_end <= start_ts: break
        except Exception as e:
            print(f"❌ Error: {e}")
            break
            
    return pd.DataFrame(all_data)

# 3. RUN BACKTEST
COINS = ['BTC', 'ETH', 'SOL', 'AVAX', 'SUI']
portfolio_trades = []

print(f"\n🔄 Running Validation (Jan 2 - Jan 23)...")

for coin in COINS:
    print(f"\n--- Processing {coin} ---")
    
    df = fetch_hyperliquid_history(coin=coin)
    if df.empty:
        print(f"   ⚠️ No data for {coin}")
        continue
        
    df = df.drop_duplicates('timestamp').sort_values('timestamp').reset_index(drop=True)
    print(f"   ✅ Data: {len(df)} candles")

    df = add_features(df)
    df = df.reset_index(drop=True)

    X = df[FEATURES].values
    X = np.nan_to_num(X, nan=0.0)
    probas = xgb_model.predict_proba(X)[:, 1]

    TP_PCT = 0.007
    SL_PCT = 0.015
    CONF_THRESH = 0.65

    trades = []
    current_position = None
    shield_stats = {'BULLISH': 0, 'BEARISH': 0, 'RANGING': 0}

    for i, row in df.iterrows():
        timestamp = row['timestamp']
        if current_position:
            h, l = row['high'], row['low']
            outcome = None
            if current_position['dir'] == 'LONG':
                if h >= current_position['tp']: outcome = 'WIN'
                elif l <= current_position['sl']: outcome = 'LOSS'
            else:
                if l <= current_position['tp']: outcome = 'WIN'
                elif h >= current_position['sl']: outcome = 'LOSS'
            if outcome:
                trades.append({**current_position, 'outcome': outcome})
                current_position = None
            continue
            
        wr = row['williams_r']
        wr_prev = row['williams_r_prev']
        prob = probas[i]
        
        signal = None
        if wr_prev < -20 and wr >= -20 and prob >= CONF_THRESH: signal = 'LONG'
        elif wr_prev > -80 and wr <= -80 and prob >= CONF_THRESH: signal = 'SHORT'
            
        if signal:
            regime = get_market_regime(df.iloc[:i+1]) # Calculate regime dynamically? Efficient approximation: use pre-calc
            # Efficient approximation to match live_trader:
            # Note: live_trader uses latest candle. Here we iterate.
            # To be strictly accurate we should slice, but for speed we can calculate rolling EMA columns
            # Recalculate regime logic inline for speed using columns:
            
            # Using simple inline logic matching trend_filter.py (0.1% buffer)
            # We need Emas in df
            pass

    # Efficient re-implementation of Regime Detection per row
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    trades = []
    current_position = None
    
    for i, row in df.iterrows():
        if i < 50: continue # Warmup
        
        if current_position:
            h, l = row['high'], row['low']
            outcome = None
            if current_position['dir'] == 'LONG':
                if h >= current_position['tp']: outcome = 'WIN'
                elif l <= current_position['sl']: outcome = 'LOSS'
            else:
                if l <= current_position['tp']: outcome = 'WIN'
                elif h >= current_position['sl']: outcome = 'LOSS'
            if outcome:
                trades.append({**current_position, 'outcome': outcome})
                current_position = None
            continue
            
        # Signal
        wr = row['williams_r']
        wr_prev = row['williams_r_prev']
        prob = probas[i]
        
        signal = None
        if wr_prev < -20 and wr >= -20 and prob >= CONF_THRESH: signal = 'LONG'
        elif wr_prev > -80 and wr <= -80 and prob >= CONF_THRESH: signal = 'SHORT'
            
        if signal:
            # Regime Check
            e20 = row['ema_20']
            e50 = row['ema_50']
            regime = 'RANGING'
            if e20 > e50 * 1.001: regime = 'BULLISH'
            elif e20 < e50 * 0.999: regime = 'BEARISH'
            
            is_valid, reason = should_trade(signal, regime)
            
            if is_valid:
                px = row['close']
                tp = px * (1+TP_PCT) if signal == 'LONG' else px * (1-TP_PCT)
                sl = px * (1-SL_PCT) if signal == 'LONG' else px * (1+SL_PCT)
                current_position = {'coin': coin, 'time': row['timestamp'], 'dir': signal, 'price': px, 'tp': tp, 'sl': sl, 'regime': regime}

    print(f"   📊 {coin}: {len(trades)} trades")
    portfolio_trades.extend(trades)

# Report
total = len(portfolio_trades)
wins = len([t for t in portfolio_trades if t['outcome']=='WIN'])
print(f"\n" + "="*70)
print(f"🏆 FINAL VERIFICATION RESULTS ({len(COINS)} Coins)")
print(f"Total Trades: {total}")

if total > 0:
    wr = wins/total*100
    pnl_usd = (wins * 27 * 53 * TP_PCT) - ((total-wins) * 27 * 53 * SL_PCT)
    roi_pct = pnl_usd / 53.0 * 100
    
    print(f"Win Rate: {wr:.2f}%")
    print(f"P&L: ${pnl_usd:.2f}")
    print(f"ROI: {roi_pct:.2f}%")
    
    df_trades = pd.DataFrame(portfolio_trades)
    print("\n📊 Breakdown by Coin:")
    print(df_trades.groupby('coin')['outcome'].value_counts().unstack().fillna(0))
else:
    print("No trades.")
