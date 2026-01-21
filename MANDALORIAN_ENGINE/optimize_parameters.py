#!/usr/bin/env python3
"""
PARAMETER OPTIMIZATION EXPERIMENT
Tests all tunable parameters to maximize ROI
"""

import pandas as pd
import numpy as np
import sys
import os
from itertools import product

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from phase3_engine import Phase3Trader, CONFIG
from quant_engine import add_all_indicators, MTF_FEATURE_LIST
from utils.advanced_features import add_advanced_features

# PARAMETER GRID TO TEST
PARAM_GRID = {
    # Current: 12 positions
    'max_concurrent': [6, 8, 10, 12, 15, 18, 20],
    
    # Current: 12 hours
    'max_duration_hours': [6, 8, 10, 12, 16, 20, 24],
    
    # Current: 25%
    'position_size_pct': [0.15, 0.20, 0.25, 0.30, 0.35, 0.40],
    
    # Current: 1.5% TP / 0.8% SL
    'tp_pct': [0.010, 0.012, 0.015, 0.018, 0.020],
    'sl_pct': [0.005, 0.006, 0.008, 0.010, 0.012],
    
    # Current: 0.45 (45%)
    'confidence_threshold': [0.40, 0.42, 0.45, 0.48, 0.50]
}

def run_backtest(params, df_full, probas):
    """Run single backtest with given parameters"""
    
    positions = []
    history = []
    balance = 10000.0
    wins = 0
    losses = 0
    
    for i in range(len(df_full)):
        row = df_full.iloc[i]
        price = row['close']
        ts = row['timestamp']
        
        # 1. Manage Positions
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
            
            # Time Exit
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
        
        # 2. Open New?
        if len(positions) >= params['max_concurrent']:
            continue
        
        prob_long = probas[i][1]
        prob_short = probas[i][2]
        
        # Adaptive Filters
        threshold = params['confidence_threshold']
        atr_ratio = row.get('atr_ratio', 0)
        hurst = row.get('hurst', 0.5)
        rsi = row.get('rsi_14', 50)
        
        if atr_ratio > 0.01:
            threshold += 0.05
        
        signal = None
        if prob_long >= threshold:
            if not (rsi < 30 and hurst > 0.5):
                signal = 'LONG'
        elif prob_short >= threshold:
            if not (rsi > 70 and hurst > 0.5):
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
                'time': ts,
                'duration': 0
            })
    
    # Calculate metrics
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
        **params
    }

def optimize_parameters():
    print("="*60)
    print("🔬 PARAMETER OPTIMIZATION EXPERIMENT")
    print("="*60)
    
    # Load December data
    data_file = "dec2025_binance_data.csv"
    print(f"📊 Loading {data_file}...")
    df = pd.read_csv(data_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Prepare data
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
    
    # Batch inference
    print("🤖 Running model inference...")
    trader = Phase3Trader(dry_run=True)
    X_dict = {c: df[c].values for c in MTF_FEATURE_LIST}
    X = np.column_stack([X_dict[c] for c in MTF_FEATURE_LIST])
    X = np.nan_to_num(X, nan=0.0)
    probas = trader.engine.get_ensemble_proba('MTF', X)
    
    # STRATEGY 1: Test one parameter at a time (baseline comparison)
    print("\n" + "="*60)
    print("📈 STRATEGY 1: Single Parameter Optimization")
    print("="*60)
    
    baseline_params = {
        'max_concurrent': 12,
        'max_duration_hours': 12,
        'position_size_pct': 0.25,
        'tp_pct': 0.015,
        'sl_pct': 0.008,
        'confidence_threshold': 0.45
    }
    
    baseline_result = run_backtest(baseline_params, df, probas)
    print(f"\n✅ BASELINE: ROI={baseline_result['roi']:.2f}%, Trades={baseline_result['trades']}, WR={baseline_result['win_rate']:.2f}%")
    
    best_results = {}
    
    for param_name in PARAM_GRID.keys():
        print(f"\n🔍 Testing {param_name}...")
        param_results = []
        
        for value in PARAM_GRID[param_name]:
            test_params = baseline_params.copy()
            test_params[param_name] = value
            result = run_backtest(test_params, df, probas)
            if result:
                param_results.append(result)
                print(f"   {param_name}={value}: ROI={result['roi']:+.2f}%, Trades={result['trades']}, WR={result['win_rate']:.2f}%")
        
        # Find best for this parameter
        best = max(param_results, key=lambda x: x['roi'])
        best_results[param_name] = best
        improvement = best['roi'] - baseline_result['roi']
        print(f"   ⭐ BEST {param_name}={best[param_name]}: ROI={best['roi']:+.2f}% ({improvement:+.2f}% vs baseline)")
    
    # STRATEGY 2: Combine all best parameters
    print("\n" + "="*60)
    print("🚀 STRATEGY 2: Combined Optimization")
    print("="*60)
    
    optimal_params = {k: v[k] for k, v in best_results.items()}
    optimal_result = run_backtest(optimal_params, df, probas)
    
    print(f"\n🏆 OPTIMAL CONFIGURATION:")
    for k, v in optimal_params.items():
        print(f"   {k}: {v}")
    print(f"\n📊 RESULTS:")
    print(f"   ROI: {optimal_result['roi']:+.2f}%")
    print(f"   Final Balance: ${optimal_result['final_balance']:,.2f}")
    print(f"   Trades: {optimal_result['trades']}")
    print(f"   Win Rate: {optimal_result['win_rate']:.2f}%")
    print(f"   Improvement: {optimal_result['roi'] - baseline_result['roi']:+.2f}% vs baseline")
    
    # Save results
    results_df = pd.DataFrame([baseline_result, optimal_result])
    results_df.to_csv("optimization_results.csv", index=False)
    print(f"\n✅ Results saved to optimization_results.csv")
    
    return optimal_params, optimal_result

if __name__ == "__main__":
    optimal_params, optimal_result = optimize_parameters()
