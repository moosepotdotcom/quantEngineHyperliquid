
import pandas as pd
import numpy as np
import glob
import os
from itertools import product

# Data Config
DATA_DIR = 'training/data/5m_3months'
TRAIN_END_DATE = '2026-01-15'

def backtest_vectorized(df, period, tp, sl):
    # Calculate Williams %R
    high = df['high'].rolling(period).max()
    low = df['low'].rolling(period).min()
    close = df['close']
    
    denom = high - low
    denom = denom.replace(0, np.nan)
    
    wr = -100 * (high - close) / denom
    wr_prev = wr.shift(1)
    
    # Momentum Signals (Breakout > -20)
    long_signals = (wr_prev < -20) & (wr >= -20)
    short_signals = (wr_prev > -80) & (wr <= -80)
    
    long_indices = df.index[long_signals].tolist()
    short_indices = df.index[short_signals].tolist()
    
    trades = []
    MAX_HOLD = 144
    
    all_indices = [(i, 'LONG') for i in long_indices] + [(i, 'SHORT') for i in short_indices]
    all_indices.sort()
    
    last_trade_idx = -999
    
    for idx, side in all_indices:
        if idx - last_trade_idx < 5: continue
        
        row = df.iloc[idx]
        entry = row['close']
        
        outcome = None
        
        if idx + 1 >= len(df): continue
            
        future = df.iloc[idx+1 : idx+1+MAX_HOLD]
        if future.empty: continue
            
        if side == 'LONG':
            tp_price = entry * (1 + tp)
            sl_price = entry * (1 - sl)
            
            hits_tp = future[future['high'] >= tp_price]
            hits_sl = future[future['low'] <= sl_price]
            
            first_tp = hits_tp.index[0] if not hits_tp.empty else 999999999
            first_sl = hits_sl.index[0] if not hits_sl.empty else 999999999
            
            if first_tp < first_sl:
                outcome = 'WIN'
            elif first_sl < first_tp:
                outcome = 'LOSS'
                
        else: # SHORT
            tp_price = entry * (1 - tp)
            sl_price = entry * (1 + sl)
            
            hits_tp = future[future['low'] <= tp_price]
            hits_sl = future[future['high'] >= sl_price]
            
            first_tp = hits_tp.index[0] if not hits_tp.empty else 999999999
            first_sl = hits_sl.index[0] if not hits_sl.empty else 999999999
            
            if first_tp < first_sl:
                outcome = 'WIN'
            elif first_sl < first_tp:
                outcome = 'LOSS'
        
        if outcome == 'WIN':
            trades.append(tp - 0.0007)
        elif outcome == 'LOSS':
            trades.append(-sl - 0.0007)
        
        if outcome:
             # Simplified stepping
             last_trade_idx = idx + 1

    return trades

def run_grid_search():
    files = glob.glob(os.path.join(DATA_DIR, "*_5m_3mo.csv"))
    dfs = []
    print(f"📂 Loading data from {DATA_DIR}...")
    for f in files:
        df = pd.read_csv(f)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.sort_values('timestamp', inplace=True)
        df = df[df['timestamp'] < TRAIN_END_DATE].copy()
        
        df = df.reset_index(drop=True)
        if not df.empty:
            dfs.append(df)
            
    print(f"✅ Loaded {len(dfs)} coins with training data.")

    # High Win Rate Grid
    periods = [7, 14, 21]
    tps = [0.004, 0.005, 0.006, 0.007] # 0.4% - 0.7% (Tight Take Profit)
    sls = [0.008, 0.010, 0.012, 0.015] # 0.8% - 1.5% (Wide Stop Loss)
    
    results = []
    
    print(f"⚡ Starting Grid Search...")
    print(f"{'Period':<6} | {'TP':<6} | {'SL':<6} | {'Trades':<6} | {'WinRate':<8} | {'TotPnL':<8}")
    print("-" * 60)
    
    for p, tp, sl in product(periods, tps, sls):
        all_trades = []
        for df in dfs:
            trades = backtest_vectorized(df, p, tp, sl)
            all_trades.extend(trades)
            
        if len(all_trades) > 10:
            count = len(all_trades)
            wins = len([t for t in all_trades if t > 0])
            wr = wins / count * 100
            tot_pnl = sum(all_trades) * 100
            
            results.append({'period':p, 'tp':tp, 'sl':sl, 'wr':wr, 'pnl':tot_pnl, 'trades':count})
            
    if results:
        # Sort by Win Rate this time, to see potential for ML
        sorted_res = sorted(results, key=lambda x: x['pnl'], reverse=True) # Sort by PnL still safest, but inspect WR
        
        print("\n📊 TOP 10 CONFIGURATIONS (Training Set):")
        print(f"{'Period':<6} | {'TP':<6} | {'SL':<6} | {'Trades':<6} | {'WinRate':<8} | {'TotPnL':<8}")
        print("-" * 60)
        for res in sorted_res[:10]:
             print(f"{res['period']:<6} | {res['tp']:.1%}  | {res['sl']:.1%}  | {res['trades']:<6} | {res['wr']:.1f}%   | {res['pnl']:.1f}%")
    else:
        print("❌ No trades generated at all.")

if __name__ == '__main__':
    run_grid_search()
