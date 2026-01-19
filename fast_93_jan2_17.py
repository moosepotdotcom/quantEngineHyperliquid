
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Logic Imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quant_engine import TradingEngine, add_all_indicators, MTF_FEATURE_LIST, CircuitBreaker

def fast_93_reproduction():
    print("🚀 FAST REPRODUCTION: 93% WIN RATE LOGIC")
    print("   Target: Jan 2 - Jan 17, 2026")
    print("="*70)
    
    engine = TradingEngine()
    
    # 1. Fetch & Pre-calculate
    print("📥 Fetching & Pre-calculating Indicators...", flush=True)
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
    
    # Simulation
    start_date = "2026-01-02 00:00:00"
    end_date = "2026-01-17 23:59:59"
    mask = (df_merged.index >= start_date) & (df_merged.index <= end_date)
    sim_data = df_merged[mask]
    
    print(f"🔄 Simulating {len(sim_data)} timestamps...", flush=True)
    
    # Trackers
    breaker = CircuitBreaker(max_losses=2, window_minutes=60, cooldown_hours=4)
    trades = []
    
    for i, (timestamp, row) in enumerate(sim_data.iterrows()):
        # 1. Skip if Breaker Active
        if breaker.cooldown_until and timestamp < breaker.cooldown_until:
            continue
            
        # 2. Prepare X
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
            
            # --- SHIELD MODE vs BENCHMARK MODE ---
            # Toggle this flag to see difference
            USE_SHIELDS = True
            USE_ATR_PENALTY = False # Isolate if ATR penalty is the volume killer
            
            if USE_SHIELDS:
                # ATR Penalty
                if USE_ATR_PENALTY and atr > 70:
                    required_conf += (atr - 70) * 0.002
                
                # Mandalorian Filter
                hurst = row.get('hurst', 0.5)
                rsi = row.get('rsi_14', 50)
                if direction == 'LONG' and rsi < 30 and hurst > 0.5:
                    continue
                
                # AI Smart Filter
                rsi7 = row.get('rsi_7', 50)
                if direction == 'SHORT' and rsi7 < 25:
                    continue
            
            if confidence < required_conf:
                continue
                
            entry = row['close']
            tp_p = entry * (1.015 if direction == 'LONG' else 0.985)
            sl_p = entry * (0.992 if direction == 'LONG' else 1.008)
            
            # Outcome (lookahead)
            future = df5[df5.index > timestamp].head(200)
            outcome = "EXPIRED"
            for _, f_row in future.iterrows():
                h, l = f_row['high'], f_row['low']
                if direction == 'LONG':
                    if h >= tp_p: outcome = 'WIN'; break
                    if l <= sl_p: outcome = 'LOSS'; break
                else:
                    if l <= tp_p: outcome = 'WIN'; break
                    if h >= sl_p: outcome = 'LOSS'; break
            
            # Update Breaker
            if outcome == 'WIN':
                breaker.cooldown_until = None
            elif outcome == 'LOSS':
                # Re-implementing simplified record_loss for the mock breaker
                if not hasattr(breaker, 'sim_losses'): breaker.sim_losses = []
                breaker.sim_losses = [t for t in breaker.sim_losses if (timestamp - t).total_seconds() < 3600]
                breaker.sim_losses.append(timestamp)
                if len(breaker.sim_losses) >= 2:
                    breaker.cooldown_until = timestamp + pd.Timedelta(hours=4)
                    print(f"   🛑 BREAKER TRIPPED at {timestamp} until {breaker.cooldown_until}")
            
            trades.append({'time': timestamp, 'dir': direction, 'outcome': outcome, 'atr': atr, 'conf': confidence})
            
    # Final Report
    total = len(trades)
    if total > 0:
        wins = len([t for t in trades if t['outcome'] == 'WIN'])
        losses = len([t for t in trades if t['outcome'] == 'LOSS'])
        wr = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
        print(f"\n✅ BACKTEST COMPLETE (SHIELDS={'ON' if USE_SHIELDS else 'OFF'})")
        print(f"   Total Trades: {total}")
        print(f"   Wins: {wins} | Losses: {losses} | Expired: {total - wins - losses}")
        print(f"   Win Rate (Valid): {wr:.1f}%")
        pd.DataFrame(trades).to_csv('reproduction_trades_final.csv')
    else:
        print("\n❌ No trades executed.")

if __name__ == "__main__":
    fast_93_reproduction()
