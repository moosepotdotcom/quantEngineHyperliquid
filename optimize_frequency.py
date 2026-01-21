#!/usr/bin/env python3
"""
Williams %R High Frequency Optimizer
------------------------------------
Goal: 50+ trades (5/day) with high win rate.
Grid:
- Timeframes: 5m, 15m, 30m, 1h (Resampled)
- Periods: 14, 21, 50, 140
- Filters: True/False (Trend, Vol)
"""

import pandas as pd
import numpy as np
import os
import itertools

DATA_FILE = 'training/data/BTC_Jan2_11_2026_Hyperliquid.csv'

def load_data():
    if not os.path.exists(DATA_FILE):
        print(f"❌ Error: {DATA_FILE} not found")
        return None
    df = pd.read_csv(DATA_FILE)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

def resample_data(df, timeframe):
    """
    Resample 5m data to target timeframe
    """
    if timeframe == '5m': return df.copy()
    
    mapping = {'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}
    resampled = df.set_index('timestamp').resample(timeframe).agg(mapping).dropna()
    resampled.reset_index(inplace=True)
    return resampled

def calculate_williams_r(df, period):
    high_roll = df['high'].rolling(period).max()
    low_roll = df['low'].rolling(period).min()
    denom = high_roll - low_roll
    denom = denom.replace(0, np.nan)
    return -100 * (high_roll - df['close']) / denom

def run_backtest(df, params):
    # Params
    period = params['period']
    use_trend = params['trend']
    use_vol = params['vol']
    tf = params['tf']
    
    # Constants
    tp_pct = 0.010
    sl_pct = 0.005
    fee_pct = 0.00035
    long_thresh = -20
    short_thresh = -80
    
    # Feature Engineering
    df = df.copy()
    df['wr'] = calculate_williams_r(df, period)
    df['wr_prev'] = df['wr'].shift(1)
    
    if use_trend:
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
        
    if use_vol:
        df['vol_sma'] = df['volume'].rolling(20).mean()
        
    # Simulation
    trades = []
    position = None
    
    for i in range(200, len(df)):
        row = df.iloc[i]
        curr_wr = row['wr']
        prev_wr = row['wr_prev']
        
        if pd.isna(curr_wr) or pd.isna(prev_wr): continue
        
        # Position Management
        if position:
            outcome=None
            exit_px=0
            if position['type'] == 'LONG':
                if row['high'] >= position['tp']: outcome='WIN'; exit_px=position['tp']
                elif row['low'] <= position['sl']: outcome='LOSS'; exit_px=position['sl']
            else:
                if row['low'] <= position['tp']: outcome='WIN'; exit_px=position['tp']
                elif row['high'] >= position['sl']: outcome='LOSS'; exit_px=position['sl']
                
            if outcome:
                # PnL
                pnl = (exit_px - position['entry']) / position['entry']
                if position['type'] == 'SHORT': pnl = -pnl
                pnl -= (fee_pct * 2)
                trades.append(pnl)
                position = None
            continue
            
        # Entry Logic
        # Trend
        trend_ok_long = True
        trend_ok_short = True
        if use_trend:
            if row['close'] < row['ema_200']: trend_ok_long=False
            if row['close'] > row['ema_200']: trend_ok_short=False
            
        # Vol
        vol_ok = True
        if use_vol:
            if row['volume'] <= 1.5 * row['vol_sma']: vol_ok=False
            
        if not vol_ok: continue
        
        # Signals
        if trend_ok_long and prev_wr < long_thresh and curr_wr >= long_thresh:
            position={'type':'LONG', 'entry':row['close'], 'tp':row['close']*(1+tp_pct), 'sl':row['close']*(1-sl_pct)}
            
        elif trend_ok_short and prev_wr > short_thresh and curr_wr <= short_thresh:
            position={'type':'SHORT', 'entry':row['close'], 'tp':row['close']*(1-tp_pct), 'sl':row['close']*(1+sl_pct)}

    # Metrics
    if not trades: return {'trades':0, 'pnl':0, 'wr':0, **params}
    
    wins = len([t for t in trades if t > 0])
    wr = wins/len(trades)*100
    pnl = sum(trades)*100
    
    return {'trades':len(trades), 'pnl':pnl, 'wr':wr, **params}

def main():
    print("📥 Loading Data...")
    df_raw = load_data()
    if df_raw is None: return
    
    # Grid
    timeframes = ['5m', '15m', '30m', '1h']
    periods = [14, 21, 50, 140]
    trends = [True, False]
    vols = [True, False]
    
    results = []
    
    print("🔄 Running Grid Search (Frequency Optimization)...")
    
    for tf in timeframes:
        print(f"   Processing {tf}...")
        df_tf = resample_data(df_raw, tf)
        
        for p, t, v in itertools.product(periods, trends, vols):
            params = {'tf':tf, 'period':p, 'trend':t, 'vol':v}
            res = run_backtest(df_tf, params)
            results.append(res)
            
    # Sort by PnL but filter for trades >= 40 (4/day)
    # The dataset is 10 days.
    
    print("\n" + "="*80)
    print(f"{'TF':<6} {'Period':<6} {'Trend':<6} {'Vol':<6} {'Trades':<8} {'Win Rate':<10} {'PnL':<10}")
    print("="*80)
    
    # Filter: At least 30 trades (3/day) for high freq
    candidates = [r for r in results if r['trades'] >= 30]
    candidates.sort(key=lambda x: x['pnl'], reverse=True)
    
    if not candidates:
        print("⚠️ No configurations found with >30 trades.")
        print("Showing top PnL regardless of freq:")
        candidates = sorted(results, key=lambda x: x['pnl'], reverse=True)[:5]
        
    for r in candidates[:10]:
        print(f"{r['tf']:<6} {r['period']:<6} {str(r['trend']):<6} {str(r['vol']):<6} {r['trades']:<8} {r['wr']:<10.1f} {r['pnl']:<10.2f}")
        
    if candidates:
        print("\n🏆 BEST HIGH FREQ CONFIG:")
        print(candidates[0])

if __name__ == "__main__":
    main()
