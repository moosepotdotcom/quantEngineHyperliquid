
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

def test_93_model_concurrent():
    print("🎯 93% WR Model with MAX 3 CONCURRENT TRADES (Jan 2026)")
    print("="*70)
    
    engine = TradingEngine()
    
    # Fetch data
    print("📥 Fetching Data...", flush=True)
    limit = 4000
    df5 = engine.fetch_data('5m', limit)
    df15 = engine.fetch_data('15m', limit)
    df1h = engine.fetch_data('1h', limit)
    
    if df5 is None or len(df5) == 0:
        print("❌ Data fetch failed.")
        return
    
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
    
    # Simulation period: Jan 1-14, 2026
    start_date = "2026-01-01 00:00:00"
    end_date = "2026-01-14 23:59:59"
    mask = (df_merged.index >= start_date) & (df_merged.index <= end_date)
    sim_data = df_merged[mask]
    
    print(f"🔄 Simulating {len(sim_data)} timestamps with MAX 3 CONCURRENT TRADES...", flush=True)
    
    # Trackers
    breaker = CircuitBreaker(max_losses=2, window_minutes=60, cooldown_hours=4)
    active_trades = []
    completed_trades = []
    max_concurrent = 0
    
    for i, (timestamp, row) in enumerate(sim_data.iterrows()):
        # Manage active trades
        for trade in active_trades[:]:
            h, l = row['high'], row['low']
            if trade['direction'] == 'LONG':
                if h >= trade['tp']:
                    completed_trades.append({
                        'entry_time': trade['time'],
                        'exit_time': timestamp,
                        'direction': 'LONG',
                        'entry_price': trade['entry'],
                        'tp_price': trade['tp'],
                        'sl_price': trade['sl'],
                        'exit_price': trade['tp'],
                        'exit_reason': 'TP_HIT',
                        'outcome': 'WIN',
                        'gross_pnl_pct': 0.015,
                        'fee_pct': TAKER_FEE * 2,
                        'net_pnl_pct': 0.015 - (TAKER_FEE * 2)
                    })
                    active_trades.remove(trade)
                elif l <= trade['sl']:
                    completed_trades.append({
                        'entry_time': trade['time'],
                        'exit_time': timestamp,
                        'direction': 'LONG',
                        'entry_price': trade['entry'],
                        'tp_price': trade['tp'],
                        'sl_price': trade['sl'],
                        'exit_price': trade['sl'],
                        'exit_reason': 'SL_HIT',
                        'outcome': 'LOSS',
                        'gross_pnl_pct': -0.008,
                        'fee_pct': TAKER_FEE * 2,
                        'net_pnl_pct': -0.008 - (TAKER_FEE * 2)
                    })
                    active_trades.remove(trade)
            else:  # SHORT
                if l <= trade['tp']:
                    completed_trades.append({
                        'entry_time': trade['time'],
                        'exit_time': timestamp,
                        'direction': 'SHORT',
                        'entry_price': trade['entry'],
                        'tp_price': trade['tp'],
                        'sl_price': trade['sl'],
                        'exit_price': trade['tp'],
                        'exit_reason': 'TP_HIT',
                        'outcome': 'WIN',
                        'gross_pnl_pct': 0.015,
                        'fee_pct': TAKER_FEE * 2,
                        'net_pnl_pct': 0.015 - (TAKER_FEE * 2)
                    })
                    active_trades.remove(trade)
                elif h >= trade['sl']:
                    completed_trades.append({
                        'entry_time': trade['time'],
                        'exit_time': timestamp,
                        'direction': 'SHORT',
                        'entry_price': trade['entry'],
                        'tp_price': trade['tp'],
                        'sl_price': trade['sl'],
                        'exit_price': trade['sl'],
                        'exit_reason': 'SL_HIT',
                        'outcome': 'LOSS',
                        'gross_pnl_pct': -0.008,
                        'fee_pct': TAKER_FEE * 2,
                        'net_pnl_pct': -0.008 - (TAKER_FEE * 2)
                    })
                    active_trades.remove(trade)
        
        # Check for new signal (only if < 3 active trades)
        if len(active_trades) >= 3:
            continue
            
        # Skip if breaker active
        if breaker.cooldown_until and timestamp < breaker.cooldown_until:
            continue
        
        # Prepare X
        X_dict = {c: row.get(c, 0.0) for c in MTF_FEATURE_LIST}
        X = np.array([X_dict[c] for c in MTF_FEATURE_LIST]).reshape(1, -1)
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        
        probas = engine.get_ensemble_proba('MTF', X)[0]
        prob_long, prob_short = float(probas[1]), float(probas[2])
        
        direction = None
        confidence = 0.0
        
        if prob_long >= 0.45:
            direction = 'LONG'; confidence = prob_long
        elif prob_short >= 0.45:
            direction = 'SHORT'; confidence = prob_short
        
        if direction:
            atr = row.get('atr_14', 50)
            required_conf = 0.45
            
            # Shields
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
            
            if len(active_trades) > max_concurrent:
                max_concurrent = len(active_trades)
    
    # Results
    df_trades = pd.DataFrame(completed_trades)
    
    if len(df_trades) > 0:
        wins = len(df_trades[df_trades['outcome'] == 'WIN'])
        losses = len(df_trades[df_trades['outcome'] == 'LOSS'])
        total = len(df_trades)
        
        gross_pnl_pct = df_trades['gross_pnl_pct'].sum()
        total_fees_pct = df_trades['fee_pct'].sum()
        net_pnl_pct = df_trades['net_pnl_pct'].sum()
        
        print(f"\n✅ RESULTS:")
        print(f"   Total Trades: {total}")
        print(f"   Wins: {wins}, Losses: {losses}")
        print(f"   Win Rate: {wins/total:.1%}")
        print(f"   Max Concurrent: {max_concurrent} positions")
        print(f"   Trades/Day: {total/14:.1f}")
        print()
        print(f"   Gross PnL (no fees):     {gross_pnl_pct*100:+.2f}%")
        print(f"   Total Fees:              -{total_fees_pct*100:.2f}%")
        print(f"   Net PnL (after fees):    {net_pnl_pct*100:+.2f}%")
        
        # Save detailed trade log
        df_trades.to_csv('93_MODEL_TRADE_LOG.csv', index=False)
        print(f"\n   📝 Trade log saved to 93_MODEL_TRADE_LOG.csv")
        
        # Show first 5 trades
        print(f"\n   📋 First 5 Trades:")
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        print(df_trades.head(5).to_string(index=False))
        
        # Show last 5 trades
        print(f"\n   📋 Last 5 Trades:")
        print(df_trades.tail(5).to_string(index=False))
        
        # Statistics
        print(f"\n   📊 Trade Statistics:")
        print(f"      Avg Win: +{df_trades[df_trades['outcome']=='WIN']['gross_pnl_pct'].mean()*100:.2f}%")
        print(f"      Avg Loss: {df_trades[df_trades['outcome']=='LOSS']['gross_pnl_pct'].mean()*100:.2f}%")
        print(f"      Fee per trade: {(total_fees_pct/total)*100:.2f}%")
        
        if net_pnl_pct > 0:
            print(f"\n   ✅ PROFITABLE after fees!")
            print(f"   Final Balance: ${10000 * (1 + net_pnl_pct):.2f}")
            print(f"   At 27x leverage: {net_pnl_pct * 27 * 100:+.2f}%")
        else:
            print(f"\n   ❌ NOT PROFITABLE after fees")
    else:
        print("\n❌ No trades executed.")

if __name__ == "__main__":
    test_93_model_concurrent()
