
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
    print("🕰️  STARTING TIME MACHINE SIMULATION (JAN 7 - JAN 10)...")
    print("="*70)
    
    engine = TradingEngine()
    
    # 1. Fetch Deep Data Context
    print("📥 Fetching historical data (Covering Jan 7-10)...")
    # We need enough context for Jan 7-10. 
    # 5m data: 4 days * 288 candles = 1152 candles. + 500 buffer = ~2000.
    df_raw = engine.fetch_data('5m', 2000) 
    
    if df_raw is None or len(df_raw) == 0:
        print("❌ Failed to fetch data")
        return

    # Base Processing
    df_raw = add_all_indicators(df_raw)
    df_raw['hurst'] = 0.5 
    df_raw.set_index('timestamp', inplace=True)
    
    # 2. Prepare MTF Context (REQUIRED for Regime)
    print("📊 Preparing MTF Context (15M / 1H)...")
    df_15m = add_all_indicators(engine.fetch_data('15m', 2000))
    df_1h = add_all_indicators(engine.fetch_data('1h', 2000))
    
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
    # Start checking from Jan 7, 08:00 (Right after the last trade)
    start_sim = pd.Timestamp("2026-01-07 08:00:00")
    
    # Filter Data
    sim_data = df_merged[df_merged.index >= start_sim]
    print(f"✅ Simulation Ready: Analyzing {len(sim_data)} candles from {start_sim}")
    
    # Initialize Manager
    # Last trade was Jan 7, 07:40 (Loss) -> SURGICAL MODE
    elastic = ElasticThresholdManager("Sim", 0.50, 0.55, 0.45)
    elastic.last_trade_time = pd.Timestamp("2026-01-07 07:40:00")
    elastic.mode = "SURGICAL" # Explicitly stricter
    
    trades = []
    
    # 4. Run Step-by-Step
    for idx, row in sim_data.iterrows():
        # --- A. Update Elastic Logic ---
        # Mocking time passed
        hours_since = (idx - elastic.last_trade_time).total_seconds() / 3600
        is_elastic = hours_since >= 6
        
        # --- B. Get Regime (Trend Filter) ---
        # We need the 1H data available UP TO this timestamp
        # Optimization: Look up in df_1h directly
        # Find latest 1h candle before/at current time
        cutoff = idx
        # We need at least 50 candles context for regime
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
            # Check Trend Filter
            allowed, reason = should_trade(signal, regime)
            ts = idx.strftime('%d-%H:%M')
            
            if allowed:
                # TRADE TAKEN!
                print(f"✅ {ts} | {signal} TAKEN! Conf {max(conf_long, conf_short):.2%} | Regime: {regime}")
                
                # Simulate Outcome (Simplified)
                # Look ahead for TP (1.5%) / SL (0.8%)
                entry_price = row['close']
                tp = entry_price * (1.015 if signal == 'LONG' else 0.985)
                sl = entry_price * (0.992 if signal == 'LONG' else 1.008)
                
                outcome = "OPEN"
                pnl = 0.0
                
                # Look forward in 5m data
                future_data = df_raw[df_raw.index > idx]
                
                for _, f_row in future_data.iterrows():
                    h, l = f_row['high'], f_row['low']
                    if signal == 'LONG':
                        if h >= tp: outcome = "WIN"; pnl = 1.5; break
                        if l <= sl: outcome = "LOSS"; pnl = -0.8; break
                    else:
                        if l <= tp: outcome = "WIN"; pnl = 1.5; break
                        if h >= sl: outcome = "LOSS"; pnl = -0.8; break
                        
                print(f"   🏁 Result: {outcome} ({pnl}%)")
                trades.append({'time': ts, 'type': signal, 'result': outcome, 'pnl': pnl})
                
                # Update Manager
                elastic.report_trade(is_win=(outcome=="WIN"))
                elastic.last_trade_time = idx
                
            else:
                # BLOCKED
                # Uncomment to see blocks
                # print(f"🛡️ {ts} | {signal} BLOCKED by {regime} Regime")
                pass

    # Summary
    print("\n" + "="*70)
    print(f"📊 SIMULATION RESULTS (Jan 7 - Jan 10)")
    print(f"   Total Trades Taken: {len(trades)}")
    wins = [t for t in trades if t['result'] == 'WIN']
    losses = [t for t in trades if t['result'] == 'LOSS']
    
    print(f"   ✅ Wins: {len(wins)}")
    print(f"   ❌ Losses: {len(losses)}")
    
    total_pnl = sum(t['pnl'] for t in trades)
    print(f"   💰 Hypothetical PnL: {total_pnl:+.2f}%")
    print("="*70)

if __name__ == "__main__":
    run_simulation()
