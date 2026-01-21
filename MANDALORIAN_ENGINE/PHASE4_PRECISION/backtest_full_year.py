#!/usr/bin/env python3
"""
FULL YEAR 2025 FEE-ADJUSTED BACKTEST
Tests all configurations across 12 months with realistic fees
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from phase3_engine import Phase3Trader
from quant_engine import add_all_indicators, MTF_FEATURE_LIST
from utils.advanced_features import add_advanced_features

# HYPERLIQUID FEE STRUCTURE
ROUND_TRIP_COST = 0.00114  # 0.114%

# TEST CONFIGURATIONS
CONFIGS = {
    "Baseline": {
        "max_concurrent": 12,
        "max_duration_hours": 12,
        "position_size_pct": 0.25,
        "tp_pct": 0.015,
        "sl_pct": 0.008,
        "confidence_threshold": 0.45
    },
    "Conservative": {
        "max_concurrent": 15,
        "max_duration_hours": 10,
        "position_size_pct": 0.30,
        "tp_pct": 0.015,
        "sl_pct": 0.008,
        "confidence_threshold": 0.42
    },
    "Balanced": {
        "max_concurrent": 16,
        "max_duration_hours": 8,
        "position_size_pct": 0.30,
        "tp_pct": 0.012,
        "sl_pct": 0.006,
        "confidence_threshold": 0.42
    },
    "Aggressive": {
        "max_concurrent": 20,
        "max_duration_hours": 6,
        "position_size_pct": 0.40,
        "tp_pct": 0.012,
        "sl_pct": 0.005,
        "confidence_threshold": 0.42
    }
}

# ALL 2025 MONTHS
MONTHS = [
    ("jan2025_binance_data.csv", "Jan"),
    ("feb2025_binance_data.csv", "Feb"),
    ("march2025_binance_data.csv", "Mar"),
    ("april2025_binance_data.csv", "Apr"),
    ("may2025_binance_data.csv", "May"),
    ("june2025_binance_data.csv", "Jun"),
    ("july2025_binance_data.csv", "Jul"),
    ("aug2025_binance_data.csv", "Aug"),
    ("sept2025_binance_data.csv", "Sep"),
    ("oct2025_binance_data.csv", "Oct"),
    ("nov2025_binance_data.csv", "Nov"),
    ("dec2025_binance_data.csv", "Dec")
]

def run_backtest_with_fees(params, df_full, probas):
    positions = []
    history = []
    balance = 10000.0
    wins = 0
    losses = 0
    total_fees_paid = 0.0
    
    for i in range(len(df_full)):
        row = df_full.iloc[i]
        price = row['close']
        
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
                gross_profit = p['size_usd'] * pnl
                total_trade_fee = p['size_usd'] * ROUND_TRIP_COST
                net_profit = gross_profit - total_trade_fee
                
                balance += net_profit
                total_fees_paid += total_trade_fee
                
                history.append({'net_pnl': net_profit})
                if net_profit > 0: wins += 1
                else: losses += 1
            else:
                remaining_pos.append(p)
        
        positions = remaining_pos
        
        if len(positions) >= params['max_concurrent']:
            continue
        
        prob_long = probas[i][1]
        prob_short = probas[i][2]
        
        threshold = params['confidence_threshold']
        if row.get('atr_ratio', 0) > 0.01:
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
    
    net_roi = ((balance - 10000.0) / 10000.0) * 100
    wr = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0
    
    return {
        'net_roi': net_roi,
        'final_balance': balance,
        'trades': len(history),
        'win_rate': wr,
        'total_fees': total_fees_paid
    }

print("="*80)
print("📊 FULL YEAR 2025 FEE-ADJUSTED BACKTEST")
print("="*80)
print("Testing 4 configurations across 12 months with 0.114% round-trip fees\n")

# Store results for each config
all_config_results = {}

for config_name, params in CONFIGS.items():
    print(f"\n{'='*80}")
    print(f"⚡ Testing {config_name} Configuration")
    print(f"{'='*80}")
    
    monthly_results = []
    
    for data_file, month_name in MONTHS:
        if not os.path.exists(data_file):
            print(f"  ❌ {month_name}: Missing data file")
            continue
        
        # Load and prepare data
        df = pd.read_csv(data_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
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
        result = run_backtest_with_fees(params, df, probas)
        
        if result:
            result['month'] = month_name
            monthly_results.append(result)
            print(f"  ✅ {month_name}: Net ROI {result['net_roi']:+.2f}%, {result['trades']} trades, WR {result['win_rate']:.1f}%")
        else:
            print(f"  ❌ {month_name}: No trades")
    
    all_config_results[config_name] = monthly_results

# SUMMARY
print("\n" + "="*80)
print("📈 ANNUAL SUMMARY (2025)")
print("="*80)

summary_table = []

for config_name, monthly_results in all_config_results.items():
    if len(monthly_results) == 0:
        continue
    
    total_trades = sum(r['trades'] for r in monthly_results)
    total_fees = sum(r['total_fees'] for r in monthly_results)
    avg_monthly_roi = sum(r['net_roi'] for r in monthly_results) / len(monthly_results)
    avg_wr = sum(r['win_rate'] for r in monthly_results) / len(monthly_results)
    
    summary_table.append({
        'config': config_name,
        'months': len(monthly_results),
        'total_trades': total_trades,
        'avg_monthly_roi': avg_monthly_roi,
        'avg_wr': avg_wr,
        'total_fees': total_fees
    })

# Print summary table
print(f"\n{'Config':<15} {'Months':>6} {'Trades':>8} {'Avg ROI':>10} {'Avg WR':>8} {'Total Fees':>12}")
print("-"*80)
for s in summary_table:
    print(f"{s['config']:<15} {s['months']:>6} {s['total_trades']:>8} {s['avg_monthly_roi']:>9.2f}% {s['avg_wr']:>7.1f}% ${s['total_fees']:>10,.0f}")

print("\n" + "="*80)
print("🎯 RECOMMENDED CONFIGURATION")
print("="*80)

# Find best by avg ROI
best = max(summary_table, key=lambda x: x['avg_monthly_roi'])
print(f"\n⭐ {best['config']} delivers the best risk-adjusted returns:")
print(f"   Average Monthly ROI: {best['avg_monthly_roi']:.2f}%")
print(f"   Average Win Rate: {best['avg_wr']:.1f}%")
print(f"   Total Trades/Year: {best['total_trades']:,}")
print(f"   Total Fees Paid: ${best['total_fees']:,.0f}")

print("\n" + "="*80)
print("✅ Full Year Backtest Complete!")
print("="*80)
