
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Add path access
sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION'))
sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION/utils'))

from quant_engine import TradingEngine, add_all_indicators, ElasticThresholdManager
from utils.trend_filter import get_regime_info, should_trade

def run_simulation():
    print("🕰️  STARTING FULL WEEK VERIFICATION (JAN 2 - JAN 9)...")
    print("="*70)
    
    engine = TradingEngine()
    
    # 1. Fetch Deep Data Context (4000 candles ~ 14 days)
    print("📥 Fetching historical data (Covering Jan 2 - Jan 11)...")
    limit = 4000
    df_raw = engine.fetch_data('5m', limit) 
    
    if df_raw is None or len(df_raw) == 0:
        print("❌ Failed to fetch data")
        return

    # Base Processing
    df_raw = add_all_indicators(df_raw)
    df_raw['hurst'] = 0.5 
    df_raw.set_index('timestamp', inplace=True)
    
    # 2. Prepare MTF Context
    print("📊 Preparing MTF Context (15M / 1H)...")
    df_15m = add_all_indicators(engine.fetch_data('15m', limit))
    df_1h = add_all_indicators(engine.fetch_data('1h', limit))
    
    df_15m.set_index('timestamp', inplace=True)
    df_1h.set_index('timestamp', inplace=True)
    
    # Merge Logic
    exclude = ['open', 'high', 'low', 'close', 'volume', 'hurst']
    
    # 15m Merge
    c15 = [c for c in df_15m.columns if c not in exclude]
    df15_r = df_15m[c15].copy()
    df15_r.columns = [f"{c}_15m" for c in c15]
    df_merged = pd.concat([df_raw, df15_r.reindex(df_raw.index, method='ffill')], axis=1)
    
    # 1H Merge
    c1h = [c for c in df_1h.columns if c not in exclude]
    df1h_r = df_1h[c1h].copy()
    df1h_r.columns = [f"{c}_1h" for c in c1h]
    df_merged = pd.concat([df_merged, df1h_r.reindex(df_raw.index, method='ffill')], axis=1)
    
    # 3. Setup Simulation State
    start_sim = pd.Timestamp("2026-01-02 00:00:00")
    end_sim = pd.Timestamp("2026-01-09 23:59:59")
    
    # Filter Data
    sim_data = df_merged[(df_merged.index >= start_sim) & (df_merged.index <= end_sim)]
    print(f"✅ Simulation Ready: Analyzing {len(sim_data)} candles from {start_sim} to {end_sim}")
    
    # Initialize Manager (Default Start)
    elastic = ElasticThresholdManager("Sim", 0.50, 0.55, 0.45)
    elastic.last_trade_time = start_sim - pd.Timedelta(hours=10) # Start Elastic?
    # Actually, let's start SURGICAL to be fair.
    elastic.last_trade_time = start_sim 
    elastic.mode = "SURGICAL"
    
    trades = []
    
    # 4. Run Step-by-Step
    for idx, row in sim_data.iterrows():
        # --- A. Update Elastic Logic ---
        hours_since = (idx - elastic.last_trade_time).total_seconds() / 3600
        is_elastic = hours_since >= 6
        
        # --- B. Get Regime (Trend Filter) ---
        cutoff = idx
        regime_window = df_1h[df_1h.index <= cutoff].tail(60)
        
        if len(regime_window) < 50:
            regime = "UNKNOWN"
        else:
            regime = get_regime_info(regime_window)['regime']
            
        # --- C. Predict ---
        row_vals = row.drop(labels=exclude + ['hurst'], errors='ignore')
        X = row_vals.values.reshape(1, -1)
        X = np.nan_to_num(X, nan=0.0)
        if X.shape[1] > 239: X = X[:, :239]
        
        avg_prob = (engine.mtf_xgb.predict_proba(X)[0] + engine.mtf_lgb.predict(X)[0] + engine.mtf_cat.predict_proba(X)[0]) / 3
        conf_long, conf_short = avg_prob[1], avg_prob[2]
        
        # --- D. Decide ---
        thresh_l = elastic.floor_threshold if is_elastic else elastic.surgical_threshold_long
        thresh_s = elastic.floor_threshold if is_elastic else elastic.surgical_threshold_short
        
        signal = None
        if conf_long >= thresh_l: signal = 'LONG'
        elif conf_short >= thresh_s: signal = 'SHORT'
        
        # --- E. Apply Filters & Log ---
        if signal:
            allowed, reason = should_trade(signal, regime)
            ts = idx.strftime('%d-%H:%M')
            conf = max(conf_long, conf_short)
            
            if allowed:
                # TRADE TAKEN!
                entry_price = row['close']
                tp = entry_price * (1.015 if signal == 'LONG' else 0.985)
                sl = entry_price * (0.992 if signal == 'LONG' else 1.008)
                
                outcome = "OPEN"
                pnl = 0.0
                
                # Look forward (Simplified outcome check)
                future_data = df_raw[df_raw.index > idx]
                
                for _, f_row in future_data.iterrows():
                    h, l = f_row['high'], f_row['low']
                    if signal == 'LONG':
                        if h >= tp: outcome = "WIN"; pnl = 1.5; break
                        if l <= sl: outcome = "LOSS"; pnl = -0.8; break
                    else:
                        if l <= tp: outcome = "WIN"; pnl = 1.5; break
                        if h >= sl: outcome = "LOSS"; pnl = -0.8; break
                
                # Double check close price if no TP/SL hit yet (time-based exit not implemented, but ok)
                if outcome == "OPEN":
                    # Assume closed at end of day or simulation? 
                    # Let's just calculate current PnL
                    pass
                
                print(f"✅ {ts} | {signal} TAKEN! Conf {conf:.2%} | Regime: {regime} | Result: {outcome} ({pnl}%)")
                trades.append({'time': ts, 'type': signal, 'result': outcome, 'pnl': pnl})
                
                # Update Manager
                elastic.report_trade(is_win=(outcome=="WIN"))
                elastic.last_trade_time = idx
                
            else:
                 pass 
                 # print(f"🛡️ {ts} | {signal} BLOCKED by {regime} Regime. Conf {conf:.2%}")

    # Summary
    print("\n" + "="*70)
    print(f"📊 VERIFICATION RESULTS (Jan 2 - Jan 9)")
    print(f"   Total Trades Taken: {len(trades)}")
    
    wins = [t for t in trades if t['result'] == 'WIN']
    losses = [t for t in trades if t['result'] == 'LOSS']
    
    print(f"   ✅ Wins: {len(wins)}")
    print(f"   ❌ Losses: {len(losses)}")
    
    if len(trades) > 0:
        wr = len(wins) / len(trades)
        print(f"   🎯 Win Rate: {wr:.1%}")
    else:
        print(f"   🎯 Win Rate: 0%")
        
    total_pnl = sum(t['pnl'] for t in trades)
    print(f"   💰 Total  PnL: {total_pnl:+.2f}%")
    print("="*70)

if __name__ == "__main__":
    run_simulation()
