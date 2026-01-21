#!/usr/bin/env python3
"""
Universal Portfolio Backtest
----------------------------
Coins: BTC, ETH, SOL, AVAX, SUI
Timeframe: 1m
Model: models/universal_portfolio_v1.json
"""

import pandas as pd
import numpy as np
import xgboost as xgb
import os
import glob
from training.train_universal_portfolio import add_features 

# --- CONFIG ---
DATA_DIR = 'training/data/1m_portfolio'
MODEL_FILE = 'models/universal_portfolio_v1.json'
TP_PCT = 0.010
SL_PCT = 0.005
FEE_PCT = 0.00035

# Thresholds
ML_THRESH = 0.60 # Lower threshold to get volume, relying on ML
LONG_THRESH = -20
SHORT_THRESH = -80

def run_backtest():
    if not os.path.exists(MODEL_FILE):
        print("❌ Model not found.")
        return
        
    print("🧠 Loading Model...")
    model = xgb.XGBClassifier()
    model.load_model(MODEL_FILE)
    
    files = glob.glob(os.path.join(DATA_DIR, "*_1m_7days.csv"))
    all_trades = []
    
    print("\n🚀 Starting Portfolio Simulation...")
    print(f"{'Coin':<6} {'Trades':<8} {'Win Rate':<10} {'PnL':<10}")
    print("-" * 40)
    
    for f in files:
        coin = os.path.basename(f).split('_')[0]
        df = pd.read_csv(f)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Features
        df = add_features(df)
        
        # ML Preds
        features = ['williams_r', 'rsi_14', 'atr_14', 'vol_change', 'ema_200_dist']
        X = df[features].replace([np.inf, -np.inf], np.nan).fillna(0)
        X = X.astype(float)
        
        probs = model.predict_proba(X)[:, 1]
        df['conf'] = probs
        
        # Sim Loop
        trades = []
        position = None
        
        for i in range(200, len(df)):
            row = df.iloc[i]
            
            # Manage Position
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
                    trades.append({
                        'coin':coin, 
                        'outcome':outcome, 
                        'pnl':pnl, 
                        'ts':row['timestamp'],
                        'entry':position['entry'],
                        'exit':exit_px,
                        'type':position['type']
                    })
                    position = None
                continue
                
            # Entry
            curr_wr = row['williams_r']
            prev_wr = row['williams_r_prev']
            conf = row['conf']
            
            if conf < ML_THRESH: continue
            
            if (prev_wr < LONG_THRESH and curr_wr >= LONG_THRESH):
                entry = row['close']
                position={'type':'LONG', 'entry':entry, 'tp':entry*(1+TP_PCT), 'sl':entry*(1-SL_PCT)}
                
            elif (prev_wr > SHORT_THRESH and curr_wr <= SHORT_THRESH):
                entry = row['close']
                position={'type':'SHORT', 'entry':entry, 'tp':entry*(1-TP_PCT), 'sl':entry*(1+SL_PCT)}

        # Coin Results
        if trades:
            wins = len([t for t in trades if t['outcome']=='WIN'])
            wr = wins/len(trades)*100
            pnl = sum([t['pnl'] for t in trades])*100
            print(f"{coin:<6} {len(trades):<8} {wr:<10.1f} {pnl:<10.2f}")
            all_trades.extend(trades)
        else:
            print(f"{coin:<6} 0        0.0        0.00")
            
    # Portfolio Results
    print("\n" + "="*50)
    print("🌍 PORTFOLIO SUMMARY (7 Days)")
    print("="*50)
    
    if all_trades:
        # Save to CSV for Simulation
        df_trades = pd.DataFrame(all_trades)
        df_trades.sort_values('ts', inplace=True)
        df_trades.to_csv('portfolio_trades.csv', index=False)
        print("💾 Saved trades to portfolio_trades.csv")

        total_trades = len(all_trades)
        total_wins = len([t for t in all_trades if t['outcome']=='WIN'])
        total_wr = total_wins / total_trades * 100
        total_pnl = sum([t['pnl'] for t in all_trades]) * 100
        trades_per_day = total_trades / 7
        
        print(f"Total Trades:   {total_trades}")
        print(f"Trades/Day:     {trades_per_day:.1f} (Target: 4-5)")
        print(f"Win Rate:       {total_wr:.2f}%")
        print(f"Total PnL:      {total_pnl:.2f}%")
    else:
        print("No trades generated.")

if __name__ == "__main__":
    run_backtest()
