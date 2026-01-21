
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Logic Imports
sys.path.insert(0, '/Users/alifiyaa/Downloads/quantEngineHyperliquid/EXPORT')
from quant_engine import TradingEngine, add_all_indicators, MTF_FEATURE_LIST, CircuitBreaker

# Hyperliquid fees
TAKER_FEE = 0.0005  # 0.05%

def test_parameter_sweep():
    print("🔬 PARAMETER OPTIMIZATION SWEEP")
    print("="*70)
    
    engine = TradingEngine()
    
    # Fetch data once
    print("📥 Fetching Data...")
    limit = 4000
    df5 = engine.fetch_data('5m', limit)
    df15 = engine.fetch_data('15m', limit)
    df1h = engine.fetch_data('1h', limit)
    
    df5 = add_all_indicators(df5)
    df15 = add_all_indicators(df15)
    df1h = add_all_indicators(df1h)
    
    df5.set_index('timestamp', inplace=True)
    df15.set_index('timestamp', inplace=True)
    df1h.set_index('timestamp', inplace=True)
    
    # Merge
    exclude = ['open', 'high', 'low', 'close', 'volume']
    ctx15 = [c for c in df15.columns if c not in exclude]
    df15_renamed = df15[ctx15].copy().rename(columns={c: f"{c}_15m" for c in ctx15})
    df_merged = pd.concat([df5, df15_renamed.reindex(df5.index, method='ffill')], axis=1)
    
    ctx1h = [c for c in df1h.columns if c not in exclude]
    df1h_renamed = df1h[ctx1h].copy().rename(columns={c: f"{c}_1h" for c in ctx1h})
    df_merged = pd.concat([df_merged, df1h_renamed.reindex(df5.index, method='ffill')], axis=1)
    
    df_merged.dropna(inplace=True)
    
    # Test period
    start_date = "2026-01-01 00:00:00"
    end_date = "2026-01-14 23:59:59"
    mask = (df_merged.index >= start_date) & (df_merged.index <= end_date)
    sim_data = df_merged[mask]
    
    print(f"🔄 Testing different configurations...")
    print()
    
    results = []
    
    # Test different confidence thresholds and max concurrent
    for base_conf in [0.40, 0.42, 0.45, 0.47, 0.50]:
        for max_concurrent in [3, 4, 5, 6]:
            
            breaker = CircuitBreaker(max_losses=2, window_minutes=60, cooldown_hours=4)
            active_trades = []
            completed_trades = []
            
            for i, (timestamp, row) in enumerate(sim_data.iterrows()):
                # Manage active trades
                for trade in active_trades[:]:
                    h, l = row['high'], row['low']
                    if trade['direction'] == 'LONG':
                        if h >= trade['tp']:
                            completed_trades.append({'outcome': 'WIN', 'pnl': 0.015 - (TAKER_FEE * 2)})
                            active_trades.remove(trade)
                        elif l <= trade['sl']:
                            completed_trades.append({'outcome': 'LOSS', 'pnl': -0.008 - (TAKER_FEE * 2)})
                            active_trades.remove(trade)
                    else:
                        if l <= trade['tp']:
                            completed_trades.append({'outcome': 'WIN', 'pnl': 0.015 - (TAKER_FEE * 2)})
                            active_trades.remove(trade)
                        elif h >= trade['sl']:
                            completed_trades.append({'outcome': 'LOSS', 'pnl': -0.008 - (TAKER_FEE * 2)})
                            active_trades.remove(trade)
                
                # Check for new signal
                if len(active_trades) >= max_concurrent:
                    continue
                    
                if breaker.cooldown_until and timestamp < breaker.cooldown_until:
                    continue
                
                X_dict = {c: row.get(c, 0.0) for c in MTF_FEATURE_LIST}
                X = np.array([X_dict[c] for c in MTF_FEATURE_LIST]).reshape(1, -1)
                X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
                
                probas = engine.get_ensemble_proba('MTF', X)[0]
                prob_long, prob_short = float(probas[1]), float(probas[2])
                
                direction = None
                confidence = 0.0
                
                if prob_long >= base_conf:
                    direction = 'LONG'; confidence = prob_long
                elif prob_short >= base_conf:
                    direction = 'SHORT'; confidence = prob_short
                
                if direction:
                    atr = row.get('atr_14', 50)
                    required_conf = base_conf
                    
                    if atr > 70:
                        required_conf += (atr - 70) * 0.002
                    
                    hurst = row.get('hurst', 0.5)
                    rsi = row.get('rsi_14', 50)
                    if direction == 'LONG' and rsi < 30 and hurst > 0.5:
                        continue
                    
                    rsi7 = row.get('rsi_7', 50)
                    if direction == 'SHORT' and rsi7 < 25:
                        continue
                    
                    if confidence < required_conf:
                        continue
                    
                    entry = row['close']
                    tp_p = entry * (1.015 if direction == 'LONG' else 0.985)
                    sl_p = entry * (0.992 if direction == 'LONG' else 1.008)
                    
                    active_trades.append({
                        'direction': direction,
                        'entry': entry,
                        'tp': tp_p,
                        'sl': sl_p,
                        'time': timestamp
                    })
            
            # Calculate results
            if len(completed_trades) > 0:
                wins = len([t for t in completed_trades if t['outcome'] == 'WIN'])
                total = len(completed_trades)
                wr = wins / total
                net_pnl = sum([t['pnl'] for t in completed_trades])
                
                results.append({
                    'base_conf': base_conf,
                    'max_concurrent': max_concurrent,
                    'trades': total,
                    'wins': wins,
                    'wr': wr,
                    'net_pnl_pct': net_pnl * 100,
                    'trades_per_day': total / 14
                })
    
    # Display results
    df_results = pd.DataFrame(results).sort_values('net_pnl_pct', ascending=False)
    
    print("📊 TOP 10 CONFIGURATIONS:")
    print(df_results.head(10).to_string(index=False))
    
    print(f"\n🏆 BEST CONFIGURATION:")
    best = df_results.iloc[0]
    print(f"   Confidence: {best['base_conf']:.2f}")
    print(f"   Max Concurrent: {int(best['max_concurrent'])}")
    print(f"   Trades: {int(best['trades'])} ({best['trades_per_day']:.1f}/day)")
    print(f"   Win Rate: {best['wr']:.1%}")
    print(f"   Net PnL: {best['net_pnl_pct']:+.2f}%")
    
    # Save results
    df_results.to_csv('PARAMETER_SWEEP_RESULTS.csv', index=False)
    print(f"\n   📝 Full results saved to PARAMETER_SWEEP_RESULTS.csv")

if __name__ == "__main__":
    test_parameter_sweep()
