#!/usr/bin/env python3
"""
Williams %R Optimization Script
-------------------------------
Grid Search for:
- Trend Filter (EMA 200)
- Volume Filter (Vol > 1.5 * Avg)
- TP/SL Combinations
- Thresholds
"""

import pandas as pd
import numpy as np
import os
import itertools
from concurrent.futures import ProcessPoolExecutor

# --- DATA LOADING ---
DATA_FILE = 'training/data/BTC_Jan2_11_2026_Hyperliquid.csv'

def load_data():
    if not os.path.exists(DATA_FILE):
        print(f"❌ Error: Data file not found at {DATA_FILE}")
        return None
    df = pd.read_csv(DATA_FILE)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

# --- INDICATORS ---
def prepare_features(df, period=140):
    df = df.copy()
    
    # Williams %R
    high_roll = df['high'].rolling(period).max()
    low_roll = df['low'].rolling(period).min()
    denom = high_roll - low_roll
    denom = denom.replace(0, np.nan)
    df['williams_r'] = -100 * (high_roll - df['close']) / denom
    df['williams_r_prev'] = df['williams_r'].shift(1)
    
    # EMA 200 (Trend)
    df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # Volume SMA 20
    df['vol_sma_20'] = df['volume'].rolling(20).mean()
    
    return df

# --- BACKTEST ENGINE ---
def run_backtest(df, params):
    """
    params: {
        'trend_filter': bool,
        'vol_filter': bool,
        'tp_pct': float,
        'sl_pct': float,
        'long_thresh': int,
        'short_thresh': int
    }
    """
    trades = []
    position = None
    fee_pct = 0.00035
    
    # Extract params for speed
    use_trend = params['trend_filter']
    use_vol = params['vol_filter']
    tp_pct = params['tp_pct']
    sl_pct = params['sl_pct']
    long_thresh = params['long_thresh']
    short_thresh = params['short_thresh']
    
    # Pre-calculate conditions to speed up loop? 
    # For now, simple loop is fine for 3000 candles * 100 combs
    
    for i in range(200, len(df)):
        row = df.iloc[i]
        curr_wr = row['williams_r']
        prev_wr = row['williams_r_prev']
        
        if pd.isna(curr_wr) or pd.isna(prev_wr):
            continue
            
        # Manage Position
        if position:
            outcome = None
            exit_px = 0
            
            if position['type'] == 'LONG':
                if row['high'] >= position['tp']:
                    outcome = 'WIN'; exit_px = position['tp']
                elif row['low'] <= position['sl']:
                    outcome = 'LOSS'; exit_px = position['sl']
            else:
                if row['low'] <= position['tp']:
                    outcome = 'WIN'; exit_px = position['tp']
                elif row['high'] >= position['sl']:
                    outcome = 'LOSS'; exit_px = position['sl']
                    
            if outcome:
                raw_pnl = (exit_px - position['entry']) / position['entry']
                if position['type'] == 'SHORT': raw_pnl = -raw_pnl
                net_pnl = raw_pnl - (fee_pct * 2)
                trades.append(net_pnl)
                position = None
            continue
            
        # Check Filters
        trend_ok_long = True
        trend_ok_short = True
        if use_trend:
            if row['close'] < row['ema_200']: trend_ok_long = False
            if row['close'] > row['ema_200']: trend_ok_short = False
            
        vol_ok = True
        if use_vol:
            if row['volume'] <= 1.5 * row['vol_sma_20']:
                vol_ok = False
        
        if not vol_ok: continue
        
        # Signals
        # Long
        if trend_ok_long and prev_wr < long_thresh and curr_wr >= long_thresh:
            entry = row['close']
            position = {
                'type': 'LONG',
                'entry': entry,
                'tp': entry * (1 + tp_pct),
                'sl': entry * (1 - sl_pct)
            }
            
        # Short
        elif trend_ok_short and prev_wr > short_thresh and curr_wr <= short_thresh:
            entry = row['close']
            position = {
                'type': 'SHORT',
                'entry': entry,
                'tp': entry * (1 - tp_pct),
                'sl': entry * (1 + sl_pct)
            }

    # Metrics
    if not trades:
        return {**params, 'trades': 0, 'win_rate': 0, 'pnl': 0}
        
    wins = len([t for t in trades if t > 0])
    win_rate = (wins / len(trades)) * 100
    total_pnl = sum(trades) * 100
    
    return {**params, 'trades': len(trades), 'win_rate': win_rate, 'pnl': total_pnl}

# --- MAIN ---
def main():
    print("📥 Loading Data...")
    df = load_data()
    if df is None: return
    
    print("🔧 Pre-calculating features...")
    df = prepare_features(df, period=140)
    
    print("🔄 Generating Grid...")
    
    # Grid Search Space
    grid = {
        'trend_filter': [True, False],
        'vol_filter': [True, False],
        'tp_sl': [
            (0.015, 0.008), # Baseline
            (0.010, 0.005), # Tight Scalp
            (0.020, 0.010), # Swing
            (0.030, 0.015)  # Aggressive
        ],
        'long_thresh': [-15, -18, -20, -25],
        'short_thresh': [-80, -85] # limited to keep combos low
    }
    
    combinations = []
    for t, v, (tp, sl), lt, st in itertools.product(
        grid['trend_filter'], grid['vol_filter'], grid['tp_sl'], 
        grid['long_thresh'], grid['short_thresh']
    ):
        combinations.append({
            'trend_filter': t,
            'vol_filter': v,
            'tp_pct': tp,
            'sl_pct': sl,
            'long_thresh': lt,
            'short_thresh': st
        })
        
    print(f"🧪 Testing {len(combinations)} combinations...")
    
    results = []
    for i, params in enumerate(combinations):
        res = run_backtest(df, params)
        results.append(res)
        if i % 50 == 0: print(f"   Processed {i}...")

    # Sort by PnL
    results.sort(key=lambda x: x['pnl'], reverse=True)
    
    print("\n" + "="*80)
    print(f"{'PnL %':<10} {'Win %':<8} {'Trades':<8} {'Trend':<6} {'Vol':<6} {'TP/SL':<12} {'Thresh':<10}")
    print("="*80)
    
    for r in results[:10]:
        tp_sl_str = f"{r['tp_pct']*100:.1f}/{r['sl_pct']*100:.1f}"
        thresh_str = f"{r['long_thresh']}/{r['short_thresh']}"
        print(f"{r['pnl']:<10.2f} {r['win_rate']:<8.1f} {r['trades']:<8} {str(r['trend_filter']):<6} {str(r['vol_filter']):<6} {tp_sl_str:<12} {thresh_str:<10}")

    # Best Result
    best = results[0]
    print("\n🏆 BEST CONFIGURATION:")
    print(best)

if __name__ == "__main__":
    main()
