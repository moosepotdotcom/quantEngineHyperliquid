#!/usr/bin/env python3
"""
AUTOMATED COMPREHENSIVE TEST
Tests Balanced configuration on Full Year 2025
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from phase3_engine import Phase3Trader
from quant_engine import add_all_indicators, MTF_FEATURE_LIST
from utils.advanced_features import add_advanced_features

# BALANCED CONFIGURATION (RECOMMENDED)
CONFIG = {
    "name": "Balanced (RECOMMENDED)",
    "max_concurrent": 16,
    "max_duration_hours": 8,
    "position_size_pct": 0.30,
    "tp_pct": 0.012,
    "sl_pct": 0.006,
    "confidence_threshold": 0.42
}

# ALL 2025 MONTHS
TEST_MONTHS = [
    ("jan2025_binance_data.csv", "January 2025"),
    ("feb2025_binance_data.csv", "February 2025"),
    ("march2025_binance_data.csv", "March 2025"),
    ("april2025_binance_data.csv", "April 2025"),
    ("may2025_binance_data.csv", "May 2025"),
    ("june2025_binance_data.csv", "June 2025"),
    ("july2025_binance_data.csv", "July 2025"),
    ("aug2025_binance_data.csv", "August 2025"),
    ("sept2025_binance_data.csv", "September 2025"),
    ("oct2025_binance_data.csv", "October 2025"),
    ("nov2025_binance_data.csv", "November 2025"),
    ("dec2025_binance_data.csv", "December 2025")
]

def run_backtest(params, df_full, probas):
    """Run backtest with given parameters"""
    
    positions = []
    history = []
    balance = 10000.0
    wins = 0
    losses = 0
    peak_balance = 10000.0
    max_drawdown = 0.0
    
    for i in range(len(df_full)):
        row = df_full.iloc[i]
        price = row['close']
        
        # Track drawdown
        if balance > peak_balance:
            peak_balance = balance
        current_dd = ((peak_balance - balance) / peak_balance) * 100
        if current_dd > max_drawdown:
            max_drawdown = current_dd
        
        # Manage Positions
        remaining_pos = []
        for p in positions:
            p['duration'] += 1
            
            exit_type = None
            pnl = 0
            high = row['high']
            low = row['low']
            
            if p['type'] == 'LONG':
                if high >= p['tp']:
                    exit_type = 'TP'
                    pnl = (p['tp'] - p['entry']) / p['entry']
                elif low <= p['sl']:
                    exit_type = 'SL'
                    pnl = (p['sl'] - p['entry']) / p['entry']
            else:
                if low <= p['tp']:
                    exit_type = 'TP'
                    pnl = (p['entry'] - p['tp']) / p['entry']
                elif high >= p['sl']:
                    exit_type = 'SL'
                    pnl = (p['entry'] - p['sl']) / p['entry']
            
            if not exit_type and p['duration'] * 5 / 60 >= params['max_duration_hours']:
                exit_type = 'EXPIRED'
                if p['type'] == 'LONG':
                    pnl = (price - p['entry']) / p['entry']
                else:
                    pnl = (p['entry'] - price) / p['entry']
            
            if exit_type:
                profit_usd = p['size_usd'] * pnl
                balance += profit_usd
                history.append({'pnl_usd': profit_usd, 'reason': exit_type})
                if pnl > 0: wins += 1
                else: losses += 1
            else:
                remaining_pos.append(p)
        
        positions = remaining_pos
        
        # Open New?
        if len(positions) >= params['max_concurrent']:
            continue
        
        prob_long = probas[i][1]
        prob_short = probas[i][2]
        
        threshold = params['confidence_threshold']
        atr_ratio = row.get('atr_ratio', 0)
        
        if atr_ratio > 0.01:
            threshold += 0.05
        
        signal = None
        if prob_long >= threshold:
            signal = 'LONG'
        elif prob_short >= threshold:
            signal = 'SHORT'
        
        if signal:
            trade_size = balance * params['position_size_pct']
            entry = price
            tp = entry * (1 + params['tp_pct']) if signal == 'LONG' else entry * (1 - params['tp_pct'])
            sl = entry * (1 - params['sl_pct']) if signal == 'LONG' else entry * (1 + params['sl_pct'])
            
            positions.append({
                'type': signal,
                'entry': entry,
                'tp': tp,
                'sl': sl,
                'size_usd': trade_size,
                'duration': 0
            })
    
    if len(history) == 0:
        return None
    
    final_balance = balance
    roi = ((final_balance - 10000.0) / 10000.0) * 100
    wr = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0
    
    return {
        'roi': roi,
        'final_balance': final_balance,
        'trades': len(history),
        'win_rate': wr,
        'wins': wins,
        'losses': losses,
        'max_drawdown': max_drawdown
    }

print("="*70)
print("🚀 AUTOMATED COMPREHENSIVE TEST")
print("="*70)
print(f"Configuration: {CONFIG['name']}")
print(f"Test Period: Full Year 2025 (12 months)")
print(f"Expected ROI: +400-600% (per optimization)")
print("="*70)

all_results = []

for data_file, period_name in TEST_MONTHS:
    print(f"\n📊 Testing {period_name}...")
    
    if not os.path.exists(data_file):
        print(f"   ❌ Missing {data_file}, skipping...")
        continue
    
    # Load data
    df = pd.read_csv(data_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Prepare features
    df = add_all_indicators(df)
    df = add_advanced_features(df)
    
    df.set_index('timestamp', inplace=True)
    df15 = df.resample('15T').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
    df15 = add_all_indicators(df15)
    df15 = add_advanced_features(df15)
    
    df1h = df.resample('1H').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
    df1h = add_all_indicators(df1h)
    df1h = add_advanced_features(df1h)
    
    exclude = ['open', 'high', 'low', 'close', 'volume']
    ctx15 = [c for c in df15.columns if c not in exclude]
    df15_renamed = df15[ctx15].rename(columns={c: f"{c}_15m" for c in ctx15})
    df = pd.concat([df, df15_renamed.reindex(df.index, method='ffill')], axis=1)
    
    ctx1h = [c for c in df1h.columns if c not in exclude]
    df1h_renamed = df1h[ctx1h].rename(columns={c: f"{c}_1h" for c in ctx1h})
    df = pd.concat([df, df1h_renamed.reindex(df.index, method='ffill')], axis=1)
    
    df.dropna(inplace=True)
    df.reset_index(inplace=True)
    
    # Inference
    trader = Phase3Trader(dry_run=True)
    X_dict = {c: df[c].values for c in MTF_FEATURE_LIST}
    X = np.column_stack([X_dict[c] for c in MTF_FEATURE_LIST])
    X = np.nan_to_num(X, nan=0.0)
    probas = trader.engine.get_ensemble_proba('MTF', X)
    
    # Backtest
    result = run_backtest(CONFIG, df, probas)
    
    if result:
        result['period'] = period_name
        all_results.append(result)
        print(f"   ✅ ROI: {result['roi']:+.2f}%, Trades: {result['trades']}, WR: {result['win_rate']:.2f}%")
    else:
        print(f"   ❌ No trades generated")

# Aggregate Results
print("\n" + "="*70)
print("📊 FULL YEAR 2025 RESULTS")
print("="*70)

total_trades = sum(r['trades'] for r in all_results)
total_wins = sum(r['wins'] for r in all_results)
total_losses = sum(r['losses'] for r in all_results)
avg_roi = sum(r['roi'] for r in all_results) / len(all_results)
avg_wr = (total_wins / (total_wins + total_losses)) * 100
max_dd = max(r['max_drawdown'] for r in all_results)

print(f"Total Months Tested: {len(all_results)}")
print(f"Total Trades: {total_trades:,}")
print(f"Overall Win Rate: {avg_wr:.2f}%")
print(f"Average Monthly ROI: {avg_roi:+.2f}%")
print(f"Max Drawdown: {max_dd:.2f}%")

print(f"\n📈 Month-by-Month Breakdown:")
for r in all_results:
    print(f"  {r['period']:15s} → ROI: {r['roi']:+7.2f}%, Trades: {r['trades']:4d}, WR: {r['win_rate']:.2f}%")

print("\n" + "="*70)
print("🎯 CLAIM VERIFICATION")
print("="*70)
print(f"Expected ROI: +400-600%")
print(f"Actual Avg ROI: {avg_roi:+.2f}%")

if 400 <= avg_roi <= 600:
    print("✅ CLAIM VERIFIED: ROI within expected range!")
elif avg_roi > 600:
    print("🚀 EXCEEDED EXPECTATIONS: ROI higher than predicted!")
else:
    print(f"⚠️  ROI below expected range (difference: {400 - avg_roi:.1f}%)")

print("="*70)
print("✅ Test Complete!")
print("="*70)
