#!/usr/bin/env python3
"""
V9 Backtest - Liquidation-Enhanced Strategy
Test on Jan 2026 data with Hyperliquid fees
"""

import pandas as pd
import numpy as np
import joblib
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.v5_feature_engineer import generate_v5_features

# Import liquidation proxy creator
from create_liquidation_proxy import create_liquidation_proxy

# Hyperliquid fees
TAKER_FEE = 0.0005  # 0.05%

def backtest_v9_jan2026():
    print("🚀 V9 Liquidation Strategy Backtest - Jan 2026")
    print("="*70)
    
    # Load 2026 data
    data_path = '../training/data/BTC_5m_2025_enriched.csv'
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Filter to Jan 2026
    df_test = df[df['timestamp'] >= '2026-01-01'].copy().reset_index(drop=True)
    print(f"📅 Test Period: {df_test['timestamp'].min()} to {df_test['timestamp'].max()}")
    
    # Generate features
    print("🧠 Generating Features...")
    df_enriched = generate_v5_features(df_test)
    
    # Add liquidation proxy
    print("💥 Adding Liquidation Proxy...")
    df_enriched = create_liquidation_proxy(df_enriched)
    
    # Load V9 model
    model_path = 'v9_liquidation_model.pkl'
    feature_path = 'v9_feature_names.txt'
    
    model = joblib.load(model_path)
    with open(feature_path, 'r') as f:
        feature_cols = [line.strip() for line in f.readlines()]
    
    print(f"✅ Loaded V9 model with {len(feature_cols)} features")
    
    # Predict
    X = df_enriched[feature_cols].fillna(0)
    predictions = model.predict(X)
    probs = model.predict_proba(X)
    
    df_enriched['v9_pred'] = predictions
    df_enriched['prob_long'] = probs[:, 0]  # Class 0 = Long
    df_enriched['prob_short'] = probs[:, 1]  # Class 1 = Short
    df_enriched['prob_neutral'] = probs[:, 2]  # Class 2 = Neutral
    
    # Backtest with V8 optimal settings
    print("\n🔄 Backtesting with Optimal Settings:")
    print("   Confidence: 0.40")
    print("   Max Concurrent: 6")
    print("   TP: 1.5%, SL: 0.8%")
    
    base_conf = 0.40
    max_concurrent = 6
    tp = 0.015
    sl = 0.008
    
    active_trades = []
    completed_trades = []
    max_concurrent_reached = 0
    
    for i in range(200, len(df_enriched) - 1):
        row = df_enriched.iloc[i]
        
        # Manage active trades
        for trade in active_trades[:]:
            h, l = row['high'], row['low']
            if trade['direction'] == 'LONG':
                if h >= trade['tp']:
                    completed_trades.append({
                        'entry_time': trade['time'],
                        'exit_time': row['timestamp'],
                        'direction': 'LONG',
                        'outcome': 'WIN',
                        'gross_pnl_pct': tp,
                        'fee_pct': TAKER_FEE * 2,
                        'net_pnl_pct': tp - (TAKER_FEE * 2)
                    })
                    active_trades.remove(trade)
                elif l <= trade['sl']:
                    completed_trades.append({
                        'entry_time': trade['time'],
                        'exit_time': row['timestamp'],
                        'direction': 'LONG',
                        'outcome': 'LOSS',
                        'gross_pnl_pct': -sl,
                        'fee_pct': TAKER_FEE * 2,
                        'net_pnl_pct': -sl - (TAKER_FEE * 2)
                    })
                    active_trades.remove(trade)
            else:  # SHORT
                if l <= trade['tp']:
                    completed_trades.append({
                        'entry_time': trade['time'],
                        'exit_time': row['timestamp'],
                        'direction': 'SHORT',
                        'outcome': 'WIN',
                        'gross_pnl_pct': tp,
                        'fee_pct': TAKER_FEE * 2,
                        'net_pnl_pct': tp - (TAKER_FEE * 2)
                    })
                    active_trades.remove(trade)
                elif h >= trade['sl']:
                    completed_trades.append({
                        'entry_time': trade['time'],
                        'exit_time': row['timestamp'],
                        'direction': 'SHORT',
                        'outcome': 'LOSS',
                        'gross_pnl_pct': -sl,
                        'fee_pct': TAKER_FEE * 2,
                        'net_pnl_pct': -sl - (TAKER_FEE * 2)
                    })
                    active_trades.remove(trade)
        
        # Check for new signal
        if len(active_trades) >= max_concurrent:
            continue
        
        prob_long = row['prob_long']
        prob_short = row['prob_short']
        
        direction = None
        if prob_long >= base_conf:
            direction = 'LONG'
        elif prob_short >= base_conf:
            direction = 'SHORT'
        
        if direction:
            entry = row['close']
            if direction == 'LONG':
                tp_price = entry * (1 + tp)
                sl_price = entry * (1 - sl)
            else:
                tp_price = entry * (1 - tp)
                sl_price = entry * (1 + sl)
            
            active_trades.append({
                'direction': direction,
                'entry': entry,
                'tp': tp_price,
                'sl': sl_price,
                'time': row['timestamp']
            })
            
            if len(active_trades) > max_concurrent_reached:
                max_concurrent_reached = len(active_trades)
    
    # Results
    df_trades = pd.DataFrame(completed_trades)
    
    if len(df_trades) > 0:
        wins = len(df_trades[df_trades['outcome'] == 'WIN'])
        losses = len(df_trades[df_trades['outcome'] == 'LOSS'])
        total = len(df_trades)
        
        gross_pnl_pct = df_trades['gross_pnl_pct'].sum()
        total_fees_pct = df_trades['fee_pct'].sum()
        net_pnl_pct = df_trades['net_pnl_pct'].sum()
        
        print(f"\n📊 V9 LIQUIDATION STRATEGY RESULTS:")
        print(f"   Total Trades: {total}")
        print(f"   Wins: {wins}, Losses: {losses}")
        print(f"   Win Rate: {wins/total:.1%}")
        print(f"   Max Concurrent: {max_concurrent_reached} positions")
        print(f"   Trades/Day: {total/14:.1f}")
        print()
        print(f"   Gross PnL (no fees):     {gross_pnl_pct*100:+.2f}%")
        print(f"   Total Fees:              -{total_fees_pct*100:.2f}%")
        print(f"   Net PnL (after fees):    {net_pnl_pct*100:+.2f}%")
        
        # Compare to V8 baseline
        print(f"\n📈 COMPARISON VS V8 BASELINE:")
        print(f"   V8: 68 trades, 83.82% WR, +70.80% PnL")
        print(f"   V9: {total} trades, {wins/total:.2%} WR, {net_pnl_pct*100:+.2f}% PnL")
        
        improvement = net_pnl_pct * 100 - 70.80
        print(f"\n   Improvement: {improvement:+.2f}%")
        
        if net_pnl_pct > 0:
            print(f"\n   ✅ PROFITABLE after fees!")
            print(f"   Final Balance: ${10000 * (1 + net_pnl_pct):.2f}")
            print(f"   At 27x leverage: {net_pnl_pct * 27 * 100:+.2f}%")
        else:
            print(f"\n   ❌ NOT PROFITABLE after fees")
        
        # Save trade log
        df_trades.to_csv('V9_TRADE_LOG_JAN2026.csv', index=False)
        print(f"\n   📝 Trade log saved to V9_TRADE_LOG_JAN2026.csv")
    else:
        print("\n❌ No trades executed")

if __name__ == "__main__":
    backtest_v9_jan2026()
