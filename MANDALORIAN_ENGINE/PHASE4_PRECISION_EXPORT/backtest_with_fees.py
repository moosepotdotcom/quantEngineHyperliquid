#!/usr/bin/env python3
"""
FEE-ADJUSTED BACKTEST
Tests configurations with realistic Hyperliquid trading fees
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
MAKER_FEE = 0.0002  # 0.02%
TAKER_FEE = 0.0005  # 0.05%
TAKER_RATIO = 0.9   # 90% taker orders
MAKER_RATIO = 0.1   # 10% maker orders
AVG_FEE = (TAKER_RATIO * TAKER_FEE) + (MAKER_RATIO * MAKER_FEE)  # 0.047%
SLIPPAGE = 0.0001   # 0.01%
TOTAL_COST_PER_SIDE = AVG_FEE + SLIPPAGE  # 0.057%
ROUND_TRIP_COST = TOTAL_COST_PER_SIDE * 2  # 0.114% per trade

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

def run_backtest_with_fees(params, df_full, probas):
    """Run backtest with realistic trading fees"""
    
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
                # Calculate gross profit
                gross_profit = p['size_usd'] * pnl
                
                # Calculate fees (entry + exit)
                entry_fee = p['size_usd'] * TOTAL_COST_PER_SIDE
                exit_fee = p['size_usd'] * TOTAL_COST_PER_SIDE
                total_trade_fee = entry_fee + exit_fee
                
                # Net profit after fees
                net_profit = gross_profit - total_trade_fee
                
                balance += net_profit
                total_fees_paid += total_trade_fee
                
                history.append({
                    'gross_pnl': gross_profit,
                    'fees': total_trade_fee,
                    'net_pnl': net_profit,
                    'reason': exit_type
                })
                
                if net_profit > 0: wins += 1
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
    gross_roi = ((final_balance + total_fees_paid - 10000.0) / 10000.0) * 100
    net_roi = ((final_balance - 10000.0) / 10000.0) * 100
    wr = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0
    
    history_df = pd.DataFrame(history)
    
    return {
        'gross_roi': gross_roi,
        'net_roi': net_roi,
        'final_balance': final_balance,
        'trades': len(history),
        'win_rate': wr,
        'total_fees': total_fees_paid,
        'fee_percentage': (total_fees_paid / 10000.0) * 100,
        'avg_gross_profit': history_df['gross_pnl'].mean(),
        'avg_fees': history_df['fees'].mean(),
        'avg_net_profit': history_df['net_pnl'].mean()
    }

print("="*80)
print("💰 FEE-ADJUSTED BACKTEST - DECEMBER 2025")
print("="*80)
print(f"Hyperliquid Fee Structure:")
print(f"  Maker: {MAKER_FEE*100:.3f}% | Taker: {TAKER_FEE*100:.3f}%")
print(f"  Average Fee: {AVG_FEE*100:.3f}% per side")
print(f"  Slippage: {SLIPPAGE*100:.3f}%")
print(f"  Total Round-Trip Cost: {ROUND_TRIP_COST*100:.3f}%")
print("="*80)

# Load December data
data_file = "dec2025_binance_data.csv"
print(f"\n📊 Loading {data_file}...")

df = pd.read_csv(data_file)
df['timestamp'] = pd.to_datetime(df['timestamp'])

print("🔧 Preparing features...")
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

print(f"✅ Data prepared: {len(df)} candles")

# Inference
print("🤖 Running model inference...")
trader = Phase3Trader(dry_run=True)
X_dict = {c: df[c].values for c in MTF_FEATURE_LIST}
X = np.column_stack([X_dict[c] for c in MTF_FEATURE_LIST])
X = np.nan_to_num(X, nan=0.0)
probas = trader.engine.get_ensemble_proba('MTF', X)
print("✅ Inference complete\n")

# Test all configurations
results = []

for name, params in CONFIGS.items():
    print(f"⚡ Testing {name}...")
    result = run_backtest_with_fees(params, df, probas)
    
    if result:
        result['config'] = name
        results.append(result)
        
        print(f"   Gross ROI: {result['gross_roi']:+.2f}%")
        print(f"   Fees Paid: ${result['total_fees']:,.2f} ({result['fee_percentage']:.2f}%)")
        print(f"   Net ROI: {result['net_roi']:+.2f}%")
        print(f"   Trades: {result['trades']}, WR: {result['win_rate']:.2f}%")
        print(f"   Avg Profit/Trade: ${result['avg_gross_profit']:.2f} → ${result['avg_net_profit']:.2f} (after fees)")
        print()

# Summary Table
print("="*80)
print("📊 COMPARISON TABLE")
print("="*80)
print(f"{'Config':<15} {'Trades':>7} {'Gross ROI':>10} {'Fees':>10} {'Net ROI':>10} {'Impact':>8}")
print("-"*80)

for r in results:
    impact = ((r['gross_roi'] - r['net_roi']) / r['gross_roi']) * 100 if r['gross_roi'] > 0 else 0
    print(f"{r['config']:<15} {r['trades']:>7} {r['gross_roi']:>9.2f}% {r['fee_percentage']:>9.2f}% {r['net_roi']:>9.2f}% {impact:>7.1f}%")

print("="*80)

# Key Insights
print("\n🎯 KEY INSIGHTS:")
print("="*80)

for r in results:
    if r['avg_net_profit'] > 0:
        status = "✅ PROFITABLE"
    else:
        status = "❌ UNPROFITABLE"
    
    print(f"{r['config']}: {status}")
    print(f"  Avg Net Profit/Trade: ${r['avg_net_profit']:.2f}")
    print(f"  Fee Efficiency: {(r['avg_net_profit'] / r['avg_gross_profit']) * 100:.1f}% of gross profit retained")
    print()

print("="*80)
print("✅ Fee-Adjusted Backtest Complete!")
print("="*80)
