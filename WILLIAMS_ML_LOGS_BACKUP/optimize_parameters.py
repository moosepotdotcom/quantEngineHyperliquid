#!/usr/bin/env python3
"""
PARAMETER OPTIMIZATION ENGINE
Target: Jan 2 - Jan 23
Method: Grid Search over TP/SL/Confidence
Goal: Maximize Total PnL while maintaining > 60% Win Rate.
"""

import pandas as pd
import numpy as np
import requests
import warnings
import sys
import os
import xgboost as xgb
import itertools

# Import Local Components
# Ensure we can import from current dir
sys.path.append(os.getcwd())
try:
    from trend_filter import get_market_regime, should_trade
except ImportError:
    print("❌ Run from WILLIAMS_ML_STRATEGY_FINAL directory")
    exit(1)

warnings.filterwarnings('ignore')

print("\n" + "="*70)
print("🧪 PARAMETER OPTIMIZATION LAB")
print("Target: High PnL + Safety")
print("="*70)

# 1. LOAD MODEL & DATA (Cached)
model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model_v1.json')
if not os.path.exists(model_path):
    print(f"❌ Model not found: {model_path}")
    exit(1)

xgb_model = xgb.XGBClassifier()
xgb_model.load_model(model_path)

FEATURES = ['williams_r', 'rsi_14', 'atr_14', 'vol_change', 'ema_200_dist']
PERIOD = 21

# Data Cache
DATA_CACHE = {}

def fetch_and_prep(coin):
    if coin in DATA_CACHE: return DATA_CACHE[coin]
    
    # Fetch Data Logic (Simplified for optimization speed - single chunk fetch if possible or reuse logic)
    # We will reuse the fetch logic from backtest_final_verify but cache it
    print(f"   📥 Loading Data for {coin}...")
    
    url = "https://api.hyperliquid.xyz/info"
    # Jan 2 to Jan 23
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
    
    # ML Features
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
    
    # Regime EMAs
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    df = df.dropna().reset_index(drop=True)
    
    # Pre-calculate Probas
    X = df[FEATURES].values
    df['proba'] = xgb_model.predict_proba(X)[:, 1]
    
    DATA_CACHE[coin] = df
    return df

# Initialize Data
COINS = ['BTC', 'ETH', 'SOL', 'AVAX', 'SUI']
for c in COINS: fetch_and_prep(c)

# 2. SIMULATION ENGINE
def run_simulation(tp_pct, sl_pct, conf_thresh, use_regime=True):
    total_wins = 0
    total_losses = 0
    
    for coin in COINS:
        df = DATA_CACHE[coin]
        
        # Vectorized Signal Logic attempt (too complex for regime state) 
        # using Fast Iteration
        
        # States
        in_trade = False
        trade_dir = None
        entry_price = 0
        tp_price = 0
        sl_price = 0
        
        # Iterate
        # Filter dataframe to potential entries first to speed up?
        # For simplicity and accuracy in grids, we iterate full df but optimized
        
        # Using numpy arrays for speed
        opens = df['open'].values
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        wrs = df['williams_r'].values
        wr_prevs = df['williams_r_prev'].values
        probas = df['proba'].values
        e20s = df['ema_20'].values
        e50s = df['ema_50'].values
        
        n = len(df)
        
        for i in range(n):
            if in_trade:
                # Check Exit
                curr_h = highs[i]
                curr_l = lows[i]
                
                win = False
                loss = False
                
                if trade_dir == 'LONG':
                    if curr_h >= tp_price: win = True
                    elif curr_l <= sl_price: loss = True
                else:
                    if curr_l <= tp_price: win = True
                    elif curr_h >= sl_price: loss = True
                    
                if win:
                    total_wins += 1
                    in_trade = False
                elif loss:
                    total_losses += 1
                    in_trade = False
                continue
            
            # Check Entry
            prob = probas[i]
            if prob < conf_thresh: continue
            
            wr = wrs[i]
            wr_p = wr_prevs[i]
            
            signal = None
            if wr_p < -20 and wr >= -20: signal = 'LONG'
            elif wr_p > -80 and wr <= -80: signal = 'SHORT'
            
            if signal:
                # Regime Check
                if use_regime:
                    e20 = e20s[i]
                    e50 = e50s[i]
                    regime = 'RANGING'
                    if e20 > e50 * 1.001: regime = 'BULLISH'
                    elif e20 < e50 * 0.999: regime = 'BEARISH'
                    
                    if signal == 'LONG' and regime != 'BULLISH': continue
                    if signal == 'SHORT' and regime != 'BEARISH': continue
                
                # Enter
                in_trade = True
                trade_dir = signal
                entry_price = closes[i]
                if signal == 'LONG':
                    tp_price = entry_price * (1 + tp_pct)
                    sl_price = entry_price * (1 - sl_pct)
                else:
                    tp_price = entry_price * (1 - tp_pct)
                    sl_price = entry_price * (1 + sl_pct)

    return total_wins, total_losses

# 3. GRID SEARCH
# Ranges to test
tp_ranges = [0.005, 0.007, 0.009, 0.012, 0.015, 0.020] # 0.5% to 2.0%
sl_ranges = [0.005, 0.010, 0.015, 0.020, 0.025, 0.030] # 0.5% to 3.0%
conf_ranges = [0.65, 0.70] # Keeping Confidence simple for now

results = []
print(f"\n🚀 Running Grid Search ({len(tp_ranges)*len(sl_ranges)*len(conf_ranges)} combinations)...")

for tp, sl, conf in itertools.product(tp_ranges, sl_ranges, conf_ranges):
    wins, losses = run_simulation(tp, sl, conf)
    total = wins + losses
    if total == 0: continue
    
    wr = wins / total * 100
    # Calc PnL (Base $53, 3x Lev -> $159 Size)
    # fees approx 0.07% total round trip
    # Profit = Wins * TP - Losses * SL
    # Normalized Risk/Reward Calc
    
    raw_pnl_pct = (wins * tp) - (losses * sl)
    # Estimate Fees
    fees_pct = total * 0.0007 
    net_pnl_pct = raw_pnl_pct - fees_pct
    
    # Sort Score: Net Profit * Win Rate (Penalty for low win rate)
    score = net_pnl_pct
    
    results.append({
        'tp': tp*100,
        'sl': sl*100,
        'conf': conf,
        'wins': wins,
        'losses': losses,
        'total': total,
        'wr': wr,
        'net_pnl_factor': net_pnl_pct
    })
    
    print(f"   TP: {tp*100:4.1f}% | SL: {sl*100:4.1f}% | Conf: {conf} -> WR: {wr:4.1f}% | Net PnL Factor: {net_pnl_pct:.4f}", end="\r")

print("\n" + "="*70)
print("🏆 TOP 5 CONFIGURATIONS")
print(f"{'TP (%)':<8} {'SL (%)':<8} {'Conf':<6} {'WR (%)':<8} {'Trades':<8} {'Score':<10}")
print("-" * 60)

# Sort by Net PnL Factor
sorted_res = sorted(results, key=lambda x: x['net_pnl_factor'], reverse=True)

for r in sorted_res[:10]:
    print(f"{r['tp']:<8.1f} {r['sl']:<8.1f} {r['conf']:<6} {r['wr']:<8.1f} {r['total']:<8} {r['net_pnl_factor']:<10.4f}")
    
# Recommendation
best = sorted_res[0]
print("\n💡 RECOMMENDATION:")
print(f"Set TP: {best['tp']}%")
print(f"Set SL: {best['sl']}%")
print(f"Set Conf: {best['conf']}")
