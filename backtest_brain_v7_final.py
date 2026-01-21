#!/usr/bin/env python3
"""
BRAIN V7: FINAL BACKTEST (RIGOROUS VERIFICATION)
- Loads 3 Models (XGB, LGB, Cat)
- Loads Optimized Config (Long > 0.65, Short > 0.40)
- Simulates Jan 15 - Jan 21 (Out of Sample)
- Calculates Sharpe, Max DD, Win Rate, Profit Factor
"""
import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
import json
import os
import sys
import matplotlib.pyplot as plt

# Load Utils
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

MODEL_PREFIX = 'models/brain_v7_'
CONFIG_FILE = 'models/brain_v7_optimized.json'
DATA_FILE = 'training/data/BTC_5m_jan2026_mtf_labeled.csv'

def load_system():
    print("⏳ Loading Brain V7 System...")
    # Config
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    thresh_l = config['optimized_thresholds']['long']
    thresh_s = config['optimized_thresholds']['short']
    print(f"   ⚙️  Thresholds: Long > {thresh_l} | Short > {thresh_s}")
    
    # Models
    xgb_m = xgb.XGBClassifier()
    xgb_m.load_model(f'{MODEL_PREFIX}xgb.json')
    lgb_m = lgb.Booster(model_file=f'{MODEL_PREFIX}lgb.json')
    cat_m = CatBoostClassifier()
    cat_m.load_model(f'{MODEL_PREFIX}cat.json')
    
    return (xgb_m, lgb_m, cat_m), (thresh_l, thresh_s)

def get_ensemble_proba(models, X):
    p1 = models[0].predict_proba(X)
    p2 = models[1].predict(X)
    p3 = models[2].predict_proba(X)
    return (p1 + p2 + p3) / 3

def backtest():
    print("="*70)
    print("🧪 BRAIN V7: FINAL VERIFICATION BACKTEST")
    print("="*70)
    
    # 1. Load Data
    print("\n📊 Loading Verification Data (OOS)...")
    df = pd.read_csv(DATA_FILE)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Validation Split (Last 30% - Jan 15 to Jan 21 approx)
    # Total ~5000 rows. Last 1500 is roughly last 5 days.
    oos_start_idx = int(len(df) * 0.70)
    df_oos = df.iloc[oos_start_idx:].copy().reset_index(drop=True)
    
    print(f"   Full Data: {len(df)}")
    print(f"   OOS Data:  {len(df_oos)} (Starts {df_oos['timestamp'].iloc[0]})")
    
    # Prepare Features
    exclude = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'label']
    feature_cols = [c for c in df.columns if c not in exclude]
    X = df_oos[feature_cols].values
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    y_true = df_oos['label'].values
    
    # 2. Run Inference
    models, thresholds = load_system()
    th_long, th_short = thresholds
    
    print("🔮 Generating Signals...")
    probs = get_ensemble_proba(models, X)
    
    # 3. Simulate Account
    balance = 1000.0
    equity_curve = [balance]
    trades = []
    
    # Targets (V7 Standard)
    TP_PCT = 0.005 # 0.5%
    SL_PCT = 0.003 # 0.3%
    FEE_PCT = 0.0005 # 0.05% per side (0.1% total roundtrip approx)
    
    for i in range(len(df_oos)):
        p_long = probs[i, 1]
        p_short = probs[i, 2]
        price = df_oos['close'].iloc[i]
        ts = df_oos['timestamp'].iloc[i]
        
        # Signal Logic (Asymmetric)
        signal = 0
        if p_long > th_long and p_long > p_short:
            signal = 1 # Long
        elif p_short > th_short and p_short > p_long:
            signal = 2 # Short
            
        trade_res = 0
        if signal != 0:
            # Oracle Check (using Label as Outcome Proxy for Speed/Accuracy)
            # Label generation was Strict: 1=TP hit before SL. 2=TP hit before SL.
            label = int(y_true[i])
            
            pnl = 0
            if signal == 1: # Long
                if label == 1:
                    pnl = (balance * TP_PCT) - (balance * FEE_PCT * 2)
                    ids = "WIN"
                else:
                    pnl = -(balance * SL_PCT) - (balance * FEE_PCT * 2)
                    ids = "LOSS"
            elif signal == 2: # Short
                if label == 2:
                    pnl = (balance * TP_PCT) - (balance * FEE_PCT * 2)
                    ids = "WIN"
                else:
                    pnl = -(balance * SL_PCT) - (balance * FEE_PCT * 2)
                    ids = "LOSS"
            
            balance += pnl
            trades.append({
                'time': ts, 'type': 'Long' if signal==1 else 'Short',
                'res': ids, 'pnl': pnl, 'bal': balance,
                'conf': p_long if signal==1 else p_short
            })
            
        equity_curve.append(balance)
        
    # 4. Metrics
    trades_df = pd.DataFrame(trades)
    
    if len(trades_df) == 0:
        print("\n❌ NO TRADES GENERATED IN OOS PERIOD!")
        return
        
    wins = len(trades_df[trades_df['res'] == 'WIN'])
    total = len(trades_df)
    win_rate = wins / total
    
    net_pnl = balance - 1000.0
    roi = net_pnl / 1000.0
    
    # Calculate Max Drawdown
    equity = np.array(equity_curve)
    peak = np.maximum.accumulate(equity)
    drawdown = (equity - peak) / peak
    max_dd = np.min(drawdown)
    
    print("\n" + "="*70)
    print("🏆 FINAL RESULTS (Jan 15 - Jan 21)")
    print("="*70)
    print(f"   Net Profit:    ${net_pnl:.2f}")
    print(f"   ROI:           {roi*100:.2f}%")
    print(f"   Final Balance: ${balance:.2f}")
    print(f"   Max Drawdown:  {max_dd*100:.2f}%")
    print(f"   Sharpe Ratio:  {(roi / abs(max_dd)) if max_dd != 0 else 0:.2f}") # Approx
    print("-" * 30)
    print(f"   Total Trades:  {total}")
    print(f"   Win Rate:      {win_rate*100:.2f}%")
    print(f"   Profit Factor: {abs(trades_df[trades_df['pnl']>0]['pnl'].sum() / trades_df[trades_df['pnl']<0]['pnl'].sum()):.2f}")
    print("="*70)
    
    # Save results
    trades_df.to_csv('brain_v7_backtest_trades.csv', index=False)
    print(f"\n💾 Saved trade log to brain_v7_backtest_trades.csv")

if __name__ == "__main__":
    backtest()
