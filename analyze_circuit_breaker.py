
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, '/Users/alifiyaa/Downloads/quantEngineHyperliquid/EXPORT')
from quant_engine import TradingEngine, add_all_indicators, MTF_FEATURE_LIST, CircuitBreaker

TAKER_FEE = 0.0005

def analyze_circuit_breaker_behavior():
    print("🔍 CIRCUIT BREAKER BEHAVIOR ANALYSIS")
    print("="*70)
    
    engine = TradingEngine()
    
    # Fetch data
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
    
    print(f"🔄 Running simulation with detailed circuit breaker tracking...")
    print()
    
    # Use optimal settings
    base_conf = 0.40
    max_concurrent = 6
    
    breaker = CircuitBreaker(max_losses=2, window_minutes=60, cooldown_hours=4)
    active_trades = []
    completed_trades = []
    breaker_events = []
    
    for i, (timestamp, row) in enumerate(sim_data.iterrows()):
        # Track active trades during breaker
        active_count_before = len(active_trades)
        
        # Manage active trades (ALWAYS runs, even during cooldown)
        for trade in active_trades[:]:
            h, l = row['high'], row['low']
            
            # Check if this trade closes during cooldown
            during_cooldown = breaker.cooldown_until and timestamp < breaker.cooldown_until
            
            if trade['direction'] == 'LONG':
                if h >= trade['tp']:
                    completed_trades.append({
                        'entry_time': trade['time'],
                        'exit_time': timestamp,
                        'outcome': 'WIN',
                        'during_cooldown': during_cooldown
                    })
                    active_trades.remove(trade)
                elif l <= trade['sl']:
                    completed_trades.append({
                        'entry_time': trade['time'],
                        'exit_time': timestamp,
                        'outcome': 'LOSS',
                        'during_cooldown': during_cooldown
                    })
                    active_trades.remove(trade)
                    
                    # Track if this triggers breaker
                    if not hasattr(breaker, 'sim_losses'): breaker.sim_losses = []
                    breaker.sim_losses = [t for t in breaker.sim_losses if (timestamp - t).total_seconds() < 3600]
                    breaker.sim_losses.append(timestamp)
                    if len(breaker.sim_losses) >= 2 and not during_cooldown:
                        breaker.cooldown_until = timestamp + pd.Timedelta(hours=4)
                        breaker_events.append({
                            'trigger_time': timestamp,
                            'cooldown_until': breaker.cooldown_until,
                            'active_trades_at_trigger': len(active_trades)
                        })
            else:  # SHORT
                if l <= trade['tp']:
                    completed_trades.append({
                        'entry_time': trade['time'],
                        'exit_time': timestamp,
                        'outcome': 'WIN',
                        'during_cooldown': during_cooldown
                    })
                    active_trades.remove(trade)
                elif h >= trade['sl']:
                    completed_trades.append({
                        'entry_time': trade['time'],
                        'exit_time': timestamp,
                        'outcome': 'LOSS',
                        'during_cooldown': during_cooldown
                    })
                    active_trades.remove(trade)
                    
                    if not hasattr(breaker, 'sim_losses'): breaker.sim_losses = []
                    breaker.sim_losses = [t for t in breaker.sim_losses if (timestamp - t).total_seconds() < 3600]
                    breaker.sim_losses.append(timestamp)
                    if len(breaker.sim_losses) >= 2 and not during_cooldown:
                        breaker.cooldown_until = timestamp + pd.Timedelta(hours=4)
                        breaker_events.append({
                            'trigger_time': timestamp,
                            'cooldown_until': breaker.cooldown_until,
                            'active_trades_at_trigger': len(active_trades)
                        })
        
        # Check for new signal (BLOCKED during cooldown)
        if len(active_trades) >= max_concurrent:
            continue
            
        if breaker.cooldown_until and timestamp < breaker.cooldown_until:
            continue  # NEW TRADES BLOCKED
        
        # [Rest of signal logic - same as before]
        X_dict = {c: row.get(c, 0.0) for c in MTF_FEATURE_LIST}
        X = np.array([X_dict[c] for c in MTF_FEATURE_LIST]).reshape(1, -1)
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        
        probas = engine.get_ensemble_proba('MTF', X)[0]
        prob_long, prob_short = float(probas[1]), float(probas[2])
        
        direction = None
        if prob_long >= base_conf:
            direction = 'LONG'
        elif prob_short >= base_conf:
            direction = 'SHORT'
        
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
            
            if prob_long >= required_conf or prob_short >= required_conf:
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
    
    # Analysis
    df_trades = pd.DataFrame(completed_trades)
    
    print(f"📊 CIRCUIT BREAKER ANALYSIS:")
    print(f"   Total Breaker Activations: {len(breaker_events)}")
    
    if len(breaker_events) > 0:
        print(f"\n   🛑 Breaker Events:")
        for i, event in enumerate(breaker_events, 1):
            print(f"      Event {i}:")
            print(f"         Triggered: {event['trigger_time']}")
            print(f"         Cooldown Until: {event['cooldown_until']}")
            print(f"         Active Trades at Trigger: {event['active_trades_at_trigger']}")
    
    if len(df_trades) > 0:
        trades_during_cooldown = len(df_trades[df_trades['during_cooldown'] == True])
        wins_during_cooldown = len(df_trades[(df_trades['during_cooldown'] == True) & (df_trades['outcome'] == 'WIN')])
        
        print(f"\n   📈 Trades During Cooldown:")
        print(f"      Total: {trades_during_cooldown}")
        print(f"      Wins: {wins_during_cooldown}")
        print(f"      Losses: {trades_during_cooldown - wins_during_cooldown}")
        
        print(f"\n   📊 Overall Results:")
        print(f"      Total Trades: {len(df_trades)}")
        print(f"      Wins: {len(df_trades[df_trades['outcome']=='WIN'])}")
        print(f"      Win Rate: {len(df_trades[df_trades['outcome']=='WIN'])/len(df_trades):.1%}")
        
        # Save detailed log
        df_trades.to_csv('CIRCUIT_BREAKER_ANALYSIS.csv', index=False)
        print(f"\n   📝 Detailed log saved to CIRCUIT_BREAKER_ANALYSIS.csv")

if __name__ == "__main__":
    analyze_circuit_breaker_behavior()
