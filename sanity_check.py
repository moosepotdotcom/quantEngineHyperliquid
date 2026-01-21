#!/usr/bin/env python3
"""
Statistical Sanity Check (Time-Series Split)
--------------------------------------------
Verify if performance holds on UNSEEN data.
Split: First 80% (Train) | Last 20% (Test)
"""

import pandas as pd
import numpy as np
import xgboost as xgb
import os
import glob
from sklearn.metrics import accuracy_score

# Reuse feature logic
from training.train_universal_portfolio import add_features

DATA_DIR = 'training/data/5m_3months'
PERIOD = 21
TP_PCT = 0.007
SL_PCT = 0.015
FEE_PCT = 0.00035
ML_THRESH = 0.60

def label_data(df):
    """
    Label data using LOCAL constants (TP_PCT, SL_PCT)
    """
    df = df.copy()
    df['target'] = 0
    
    # Vectorized labeling (approximate or precise?)
    # Precise iteration needed for TP/SL correctness
    
    # Or just use the logic matching backtest?
    # For training, we need to know if a signal resulted in a WIN or LOSS
    # Iterate through signals
    
    # Williams %R signals
    df['wr'] = df['williams_r']
    df['wr_prev'] = df['williams_r'].shift(1)
    
    long_signals = (df['wr_prev'] < -20) & (df['wr'] >= -20)
    short_signals = (df['wr_prev'] > -80) & (df['wr'] <= -80)
    
    signals_indices = df.index[long_signals | short_signals]
    
    for idx in signals_indices:
        row = df.loc[idx]
        entry = row['close']
        is_long = (row['wr_prev'] < -20)
        
        outcome = 0 # 0 = Loss/Neutral, 1 = Win
        
        # Look forward max 144 candles (12 hours)
        future = df.loc[idx+1 : idx+144]
        
        if future.empty: continue
            
        if is_long:
            tp_price = entry * (1 + TP_PCT)
            sl_price = entry * (1 - SL_PCT)
            
            hits_tp = future[future['high'] >= tp_price]
            hits_sl = future[future['low'] <= sl_price]
            
            first_tp = hits_tp.index[0] if not hits_tp.empty else 999999999
            first_sl = hits_sl.index[0] if not hits_sl.empty else 999999999
            
            if first_tp < first_sl:
                outcome = 1
                
        else: # SHORT
            tp_price = entry * (1 - TP_PCT)
            sl_price = entry * (1 + SL_PCT)
            
            hits_tp = future[future['low'] <= tp_price]
            hits_sl = future[future['high'] >= sl_price]
            
            first_tp = hits_tp.index[0] if not hits_tp.empty else 999999999
            first_sl = hits_sl.index[0] if not hits_sl.empty else 999999999
            
            if first_tp < first_sl:
                outcome = 1
                
        df.loc[idx, 'target'] = outcome
        
    return df[long_signals | short_signals].copy()

def run_sanity_check():
    print("🕵️ STARTING SANITY CHECK (Strict Train/Test Split)...")
    
    files = glob.glob(os.path.join(DATA_DIR, "*_5m_3mo.csv"))
    all_signals = []
    
    # 1. Prepare Data
    print("1️⃣  Loading & Splitting Data (5m)...")
    
    train_dfs = []
    test_dfs = []
    
    for f in files:
        coin = os.path.basename(f).split('_')[0]
        df = pd.read_csv(f)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.sort_values('timestamp', inplace=True)
        
        # Split Index
        split_idx = int(len(df) * 0.80)
        
        df_train = df.iloc[:split_idx].copy()
        df_test = df.iloc[split_idx:].copy() # The "Future"
        
        # Add Features & Labels to Train
        df_train = add_features(df_train)
        signals_train = label_data(df_train)
        
        if not signals_train.empty:
            train_dfs.append(signals_train)
            
        # Add Features to Test (Labels only for ground truth check, backtest logic is separate)
        df_test = add_features(df_test)
        df_test['coin'] = coin
        test_dfs.append(df_test)
        
    # 2. Train on PAST Data
    mega_train = pd.concat(train_dfs, ignore_index=True)
    print(f"2️⃣  Training on {len(mega_train)} samples (Past ~2.5 Months)...")
    print(f"    Baseline Train WR: {mega_train['target'].mean()*100:.2f}%")
    
    features = ['williams_r', 'rsi_14', 'atr_14', 'vol_change', 'ema_200_dist']
    X_train = mega_train[features].replace([np.inf, -np.inf], np.nan).fillna(0)
    y_train = mega_train['target']
    
    # Increased complexity for robust learning
    model = xgb.XGBClassifier(n_estimators=200, max_depth=6, learning_rate=0.03, objective='binary:logistic')
    model.fit(X_train, y_train)
    
    # 3. Test on FUTURE Data
    print(f"    Raw Signals in Test Set: {sum(len(df) for df in test_dfs)}")

    thresholds = [0.50, 0.55, 0.60, 0.65]
    
    for thresh in thresholds:
        print(f"\n🔹 Testing Threshold: {thresh}")
        all_trades = []
        
        for df_test in test_dfs:
            coin = df_test['coin'].iloc[0]
            
            # Predict
            X_test = df_test[features].replace([np.inf, -np.inf], np.nan).fillna(0)
            probs = model.predict_proba(X_test)[:, 1]
            df_test['conf'] = probs
            
            trades = []
            position = None
            
            # Sim Loop
            for i in range(200, len(df_test)):
                row = df_test.iloc[i]
                
                # Position
                if position:
                    outcome=None; exit_px=0
                    if position['type'] == 'LONG':
                        if row['high'] >= position['tp']: outcome='WIN'; exit_px=position['tp']
                        elif row['low'] <= position['sl']: outcome='LOSS'; exit_px=position['sl']
                    else:
                        if row['low'] <= position['tp']: outcome='WIN'; exit_px=position['tp']
                        elif row['high'] >= position['sl']: outcome='LOSS'; exit_px=position['sl']
                        
                    if outcome:
                        pnl = (exit_px - position['entry']) / position['entry']
                        if position['type'] == 'SHORT': pnl = -pnl
                        pnl -= (FEE_PCT*2)
                        trades.append({'outcome':outcome, 'pnl':pnl})
                        position = None
                    continue
                    
                # Signal
                curr_wr = row['williams_r']
                prev_wr = row['williams_r_prev']
                conf = row['conf']
                
                if conf < thresh: continue
                
                if (prev_wr < -20 and curr_wr >= -20): # Long
                    entry = row['close']
                    position={'type':'LONG', 'entry':entry, 'tp':entry*(1+TP_PCT), 'sl':entry*(1-SL_PCT)}
                    
                elif (prev_wr > -80 and curr_wr <= -80): # Short
                    entry = row['close']
                    position={'type':'SHORT', 'entry':entry, 'tp':entry*(1-TP_PCT), 'sl':entry*(1+SL_PCT)}
    
            if trades:
                wins = len([t for t in trades if t['outcome']=='WIN'])
                # print(f"   {coin:<6}: {len(trades)} trades, WR: {wins/len(trades)*100:.1f}%")
                all_trades.extend(trades)
                
        # Result per threshold
        if all_trades:
            total = len(all_trades)
            wins = len([t for t in all_trades if t['outcome']=='WIN'])
            wr = wins/total*100
            pnl = sum([t['pnl'] for t in all_trades])*100
            print(f"   👉 Total Trades: {total} | WR: {wr:.2f}% | PnL: {pnl:.2f}%")
        else:
            print("   ⚠️ No trades.")

if __name__ == "__main__":
    run_sanity_check()
