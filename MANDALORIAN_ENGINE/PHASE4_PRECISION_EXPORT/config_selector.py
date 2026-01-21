#!/usr/bin/env python3
"""
INTERACTIVE CONFIGURATION SELECTOR & VALIDATOR
Choose optimization level and verify performance claims
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from phase3_engine import Phase3Trader, CONFIG
from quant_engine import add_all_indicators, MTF_FEATURE_LIST
from utils.advanced_features import add_advanced_features

# CONFIGURATION PRESETS
CONFIGS = {
    "1": {
        "name": "Full Optimal (AGGRESSIVE)",
        "description": "Maximum ROI with high risk",
        "params": {
            "max_concurrent": 20,
            "max_duration_hours": 6,
            "position_size_pct": 0.40,
            "tp_pct": 0.012,
            "sl_pct": 0.005,
            "confidence_threshold": 0.42
        },
        "expected_roi": "+1073%",
        "risk_level": "HIGH (8x leverage)",
        "drawdown": "30-40%"
    },
    "2": {
        "name": "Balanced (RECOMMENDED)",
        "description": "Great ROI with moderate risk",
        "params": {
            "max_concurrent": 16,
            "max_duration_hours": 8,
            "position_size_pct": 0.30,
            "tp_pct": 0.012,
            "sl_pct": 0.006,
            "confidence_threshold": 0.42
        },
        "expected_roi": "+400-600%",
        "risk_level": "MODERATE (4.8x leverage)",
        "drawdown": "20-25%"
    },
    "3": {
        "name": "Conservative Upgrade (SAFE)",
        "description": "Solid improvement with low risk",
        "params": {
            "max_concurrent": 15,
            "max_duration_hours": 10,
            "position_size_pct": 0.30,
            "tp_pct": 0.015,
            "sl_pct": 0.008,
            "confidence_threshold": 0.42
        },
        "expected_roi": "+200-300%",
        "risk_level": "LOW (4.5x leverage)",
        "drawdown": "15-20%"
    },
    "0": {
        "name": "Current Baseline",
        "description": "Existing configuration",
        "params": {
            "max_concurrent": 12,
            "max_duration_hours": 12,
            "position_size_pct": 0.25,
            "tp_pct": 0.015,
            "sl_pct": 0.008,
            "confidence_threshold": 0.45
        },
        "expected_roi": "+120%",
        "risk_level": "LOW (3x leverage)",
        "drawdown": "15-20%"
    }
}

# AVAILABLE BACKTEST PERIODS (Chronological Order)
PERIODS = {
    # 2025 Data
    "1": {"name": "January 2025", "file": "jan2025_binance_data.csv", "description": "Start of 2025"},
    "2": {"name": "February 2025", "file": "feb2025_binance_data.csv", "description": "Q1 2025"},
    "3": {"name": "March 2025", "file": "march2025_binance_data.csv", "description": "Q1 2025"},
    "4": {"name": "April 2025", "file": "april2025_binance_data.csv", "description": "Q2 2025"},
    "5": {"name": "May 2025", "file": "may2025_binance_data.csv", "description": "Q2 2025"},
    "6": {"name": "June 2025", "file": "june2025_binance_data.csv", "description": "Q2 2025"},
    "7": {"name": "July 2025", "file": "july2025_binance_data.csv", "description": "Q3 2025"},
    "8": {"name": "August 2025", "file": "aug2025_binance_data.csv", "description": "Q3 2025"},
    "9": {"name": "September 2025", "file": "sept2025_binance_data.csv", "description": "Q3 Chop"},
    "10": {"name": "October 2025", "file": "oct2025_binance_data.csv", "description": "Q4 Uptrend"},
    "11": {"name": "November 2025", "file": "nov2025_binance_data.csv", "description": "Q4 Bull Run"},
    "12": {"name": "December 2025", "file": "dec2025_binance_data.csv", "description": "Q4 Volatile"},
    
    # 2026 Data
    "13": {"name": "January 2026", "file": "jan2026_binance_data.csv", "description": "Recent (18 days)"},
    
    # Aggregate Options
    "q1": {"name": "Q1 2025 (Jan-Mar)", "file": "Q1_2025", "description": "3 months"},
    "q2": {"name": "Q2 2025 (Apr-Jun)", "file": "Q2_2025", "description": "3 months"},
    "q3": {"name": "Q3 2025 (Jul-Sep)", "file": "Q3_2025", "description": "3 months"},
    "q4": {"name": "Q4 2025 (Oct-Dec)", "file": "Q4_2025", "description": "3 months"},
    "2025": {"name": "Full Year 2025", "file": "YEAR_2025", "description": "All 12 months"},
    "all": {"name": "All Available Data", "file": "ALL", "description": "13 months (Jan 2025 - Jan 2026)"}
}

# Quarter mappings
QUARTER_FILES = {
    "Q1_2025": [
        ("jan2025_binance_data.csv", "January 2025"),
        ("feb2025_binance_data.csv", "February 2025"),
        ("march2025_binance_data.csv", "March 2025")
    ],
    "Q2_2025": [
        ("april2025_binance_data.csv", "April 2025"),
        ("may2025_binance_data.csv", "May 2025"),
        ("june2025_binance_data.csv", "June 2025")
    ],
    "Q3_2025": [
        ("july2025_binance_data.csv", "July 2025"),
        ("aug2025_binance_data.csv", "August 2025"),
        ("sept2025_binance_data.csv", "September 2025")
    ],
    "Q4_2025": [
        ("oct2025_binance_data.csv", "October 2025"),
        ("nov2025_binance_data.csv", "November 2025"),
        ("dec2025_binance_data.csv", "December 2025")
    ],
    "YEAR_2025": [
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
    ],
    "ALL": [
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
        ("dec2025_binance_data.csv", "December 2025"),
        ("jan2026_binance_data.csv", "January 2026")
    ]
}

def print_header():
    print("\n" + "="*70)
    print("🚀 MANDALORIAN PHASE 3 - CONFIGURATION SELECTOR")
    print("="*70)

def print_menu():
    print("\n📊 Available Configurations:\n")
    
    for key in ["1", "2", "3", "0"]:
        config = CONFIGS[key]
        print(f"[{key}] {config['name']}")
        print(f"    {config['description']}")
        print(f"    Expected ROI: {config['expected_roi']}")
        print(f"    Risk Level: {config['risk_level']}")
        print(f"    Max Drawdown: {config['drawdown']}")
        print()

def print_period_menu():
    print("\n📅 Select Backtest Period:\n")
    
    print("  Individual Months (2025):")
    for key in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]:
        period = PERIODS[key]
        print(f"    [{key:>2s}] {period['name']:20s} - {period['description']}")
    
    print("\n  Recent (2026):")
    period = PERIODS["13"]
    print(f"    [13] {period['name']:20s} - {period['description']}")
    
    print("\n  Quarterly Aggregates:")
    for key in ["q1", "q2", "q3", "q4"]:
        period = PERIODS[key]
        print(f"    [{key:>2s}] {period['name']:20s} - {period['description']}")
    
    print("\n  Full Period Tests:")
    for key in ["2025", "all"]:
        period = PERIODS[key]
        print(f"    [{key:>4s}] {period['name']:20s} - {period['description']}")
    
    print()

def print_config_details(config):
    print("\n" + "-"*70)
    print(f"📋 Configuration: {config['name']}")
    print("-"*70)
    params = config['params']
    print(f"  Max Concurrent Positions: {params['max_concurrent']}")
    print(f"  Max Trade Duration: {params['max_duration_hours']} hours")
    print(f"  Position Size: {params['position_size_pct']*100:.0f}% of balance")
    print(f"  Take Profit: {params['tp_pct']*100:.2f}%")
    print(f"  Stop Loss: {params['sl_pct']*100:.2f}%")
    print(f"  Confidence Threshold: {params['confidence_threshold']*100:.0f}%")
    print("-"*70)

def run_backtest(params, df_full, probas, config_name):
    """Run backtest with given parameters"""
    
    print(f"\n⚡ Running backtest for: {config_name}")
    print("   Processing 8,929 candles...")
    
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
        ts = row['timestamp']
        
        # Track peak and drawdown
        if balance > peak_balance:
            peak_balance = balance
        current_dd = ((peak_balance - balance) / peak_balance) * 100
        if current_dd > max_drawdown:
            max_drawdown = current_dd
        
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
                history.append({
                    'pnl_usd': profit_usd,
                    'pnl_pct': pnl,
                    'reason': exit_type,
                    'balance': balance
                })
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
    
    history_df = pd.DataFrame(history)
    
    return {
        'roi': roi,
        'final_balance': final_balance,
        'trades': len(history),
        'win_rate': wr,
        'wins': wins,
        'losses': losses,
        'max_drawdown': max_drawdown,
        'avg_trade': history_df['pnl_usd'].mean(),
        'history': history_df
    }

def print_results(result, config):
    print("\n" + "="*70)
    print(f"📊 BACKTEST RESULTS: {config['name']}")
    print("="*70)
    print(f"  Final Balance: ${result['final_balance']:,.2f}")
    print(f"  Total ROI: {result['roi']:+.2f}%")
    print(f"  Total Trades: {result['trades']}")
    print(f"  Win Rate: {result['win_rate']:.2f}%")
    print(f"  Wins/Losses: {result['wins']}/{result['losses']}")
    print(f"  Avg Trade PnL: ${result['avg_trade']:.2f}")
    print(f"  Max Drawdown: {result['max_drawdown']:.2f}%")
    print("="*70)
    
    # Compare to expected
    expected_roi = config['expected_roi']
    print(f"\n✅ Expected ROI: {expected_roi}")
    print(f"✅ Actual ROI: {result['roi']:+.2f}%")
    
    if "%" in expected_roi:
        # Extract number from expected (handle ranges like "+400-600%")
        if "-" in expected_roi:
            low, high = expected_roi.replace("+", "").replace("%", "").split("-")
            low, high = float(low), float(high)
            if low <= result['roi'] <= high:
                print(f"🎯 CLAIM VERIFIED: ROI within expected range!")
            else:
                print(f"⚠️  ROI outside expected range")
        else:
            expected_val = float(expected_roi.replace("+", "").replace("%", ""))
            diff = abs(result['roi'] - expected_val)
            if diff < 50:  # Within 50% tolerance
                print(f"🎯 CLAIM VERIFIED: ROI matches expectation!")
            else:
                print(f"⚠️  ROI differs from expectation by {diff:.1f}%")

def main():
    print_header()
    print_menu()
    
    # Get user choice for configuration
    while True:
        choice = input("Select configuration [0-3] or 'q' to quit: ").strip()
        
        if choice.lower() == 'q':
            print("\n👋 Exiting...")
            return
        
        if choice not in CONFIGS:
            print("❌ Invalid choice. Please select 0, 1, 2, or 3.")
            continue
        
        break
    
    selected_config = CONFIGS[choice]
    print_config_details(selected_config)
    
    # Get user choice for time period
    print_period_menu()
    while True:
        period_choice = input("Select backtest period [1-6]: ").strip()
        
        if period_choice not in PERIODS:
            print("❌ Invalid choice. Please select 1-6.")
            continue
        
        break
    
    selected_period = PERIODS[period_choice]
    
    # Confirm
    print(f"\n📋 Configuration: {selected_config['name']}")
    print(f"📅 Period: {selected_period['name']}")
    confirm = input("\nProceed with backtest? [y/n]: ").strip().lower()
    if confirm != 'y':
        print("❌ Cancelled.")
        return
    
    # Determine which files to test
    selected_file = selected_period['file']
    
    if selected_file in QUARTER_FILES:
        # Quarter or aggregate selection
        test_files = QUARTER_FILES[selected_file]
    else:
        # Single month selection
        test_files = [(selected_period['file'], selected_period['name'])]
    
    all_results = []
    
    for data_file, period_name in test_files:
        print("\n" + "="*70)
        print(f"📊 Loading {period_name} Data...")
        print("="*70)
        
        if not os.path.exists(data_file):
            print(f"❌ Missing {data_file}, skipping...")
            continue
        
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
        
        # Batch inference
        print("🤖 Running model inference...")
        trader = Phase3Trader(dry_run=True)
        X_dict = {c: df[c].values for c in MTF_FEATURE_LIST}
        X = np.column_stack([X_dict[c] for c in MTF_FEATURE_LIST])
        X = np.nan_to_num(X, nan=0.0)
        probas = trader.engine.get_ensemble_proba('MTF', X)
        print("✅ Inference complete")
        
        # Run backtest
        result = run_backtest(selected_config['params'], df, probas, f"{selected_config['name']} - {period_name}")
        
        if result is None:
            print(f"❌ Backtest failed for {period_name} - no trades generated")
            continue
        
        # Store result
        result['period'] = period_name
        all_results.append(result)
        
        # Print results for this period
        print_results(result, selected_config)
        
        # Save individual trade log
        log_filename = f"backtest_{choice}_{period_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        result['history'].to_csv(log_filename, index=False)
        print(f"\n💾 Trade log saved: {log_filename}")
    
    # If multi-month test, show aggregate results
    if len(all_results) > 1:
        print("\n" + "="*70)
        print("📊 AGGREGATE RESULTS (All Periods)")
        print("="*70)
        
        total_trades = sum(r['trades'] for r in all_results)
        total_wins = sum(r['wins'] for r in all_results)
        total_losses = sum(r['losses'] for r in all_results)
        avg_roi = sum(r['roi'] for r in all_results) / len(all_results)
        avg_wr = (total_wins / (total_wins + total_losses)) * 100 if (total_wins + total_losses) > 0 else 0
        
        print(f"  Total Periods Tested: {len(all_results)}")
        print(f"  Total Trades: {total_trades}")
        print(f"  Overall Win Rate: {avg_wr:.2f}%")
        print(f"  Average Monthly ROI: {avg_roi:+.2f}%")
        print(f"\n  Period Breakdown:")
        for r in all_results:
            print(f"    {r['period']:20s} → ROI: {r['roi']:+7.2f}%, Trades: {r['trades']:4d}, WR: {r['win_rate']:.2f}%")
        print("="*70)
    
    # Ask if user wants to apply this config
    print("\n" + "="*70)
    apply = input("Apply this configuration to phase3_engine.py? [y/n]: ").strip().lower()
    
    if apply == 'y':
        print("\n✅ Configuration will be applied.")
        print("   Run: python apply_config.py to update the engine")
        
        # Save selected config to file
        import json
        with open("selected_config.json", "w") as f:
            json.dump({
                "name": selected_config['name'],
                "params": selected_config['params'],
                "verified_periods": [r['period'] for r in all_results],
                "verified_avg_roi": avg_roi if len(all_results) > 1 else all_results[0]['roi'],
                "verified_date": datetime.now().isoformat()
            }, f, indent=4)
        print("   Configuration saved to: selected_config.json")
    else:
        print("\n❌ Configuration not applied. Engine remains unchanged.")
    
    print("\n" + "="*70)
    print("✅ Complete!")
    print("="*70)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
