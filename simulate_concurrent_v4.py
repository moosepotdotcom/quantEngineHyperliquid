
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys

# Add root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.fetch_data import fetch_live_data
from utils.feature_engineer import add_all_indicators
from utils.mtf_feature_engineer import MTFFeatureGenerator
from model_engines.mtf_scalper_v3.logic import MTFScalperV3Logic

def simulate_concurrent_v4():
    print("🚀 Simulating 'Max 3 Concurrent Trades' + Circuit Breaker...")
    
    # 1. SETUP
    params = {
        'initial_capital': 10000,
        'position_size': 10000, # Per trade
        'max_concurrent': 3,
        'cb_threshold_losses': 2,
        'cb_pause_hours': 4,
        'tp_pct': 0.015,
        'sl_pct': 0.008,
        'fee': 0.0004
    }
    
    start_date = "2026-01-02"
    end_date = "2026-01-14"
    
    # 2. DATA
    print("   📥 Fetching Data...")
    def get_data(tf):
        df = fetch_live_data("BTC", tf, limit=4500)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        s = pd.Timestamp(start_date).tz_localize('UTC')
        e = pd.Timestamp(end_date).tz_localize('UTC') + pd.Timedelta(days=1)
        df = df[(df['timestamp'] >= s) & (df['timestamp'] <= e)]
        df = add_all_indicators(df)
        return df.sort_values('timestamp').reset_index(drop=True)

    df_5m = get_data('5m')
    df_15m = get_data('15m')
    df_30m = get_data('30m')
    
    # 3. PREDICTIONS
    print("   🧠 Generating Predictions...")
    logic = MTFScalperV3Logic()
    gen = MTFFeatureGenerator(df_5m, df_15m, df_30m)
    X_feat, price_df = gen.generate()
    X_feat = X_feat.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    probs = logic.model.predict_proba(X_feat.values)
    
    full_df = df_5m.set_index('timestamp').reindex(price_df.index)
    atr_values = full_df['atr_14'].values
    
    # 4. SIMULATION LOOP
    print("\n⚡ Running Simulation Loop...")
    
    balance = params['initial_capital']
    positions = [] # List of dicts
    trades = []
    
    # Circuit Breaker State
    consecutive_losses = 0
    pause_until = None
    
    max_drawdown = 0
    peak_balance = balance
    
    for i in range(len(price_df)):
        ts = price_df.index[i]
        price = price_df['close'].iloc[i]
        high = price_df['high'].iloc[i]
        low = price_df['low'].iloc[i]
        
        # A. Check Exits (First!)
        # Iterate backwards to allow removal
        closed_indices = []
        for idx, p in enumerate(positions):
            exit_p = None
            reason = None
            
            if p['type'] == 'LONG':
                if low <= p['sl']: exit_p = p['sl']; reason = 'SL'
                elif high >= p['tp']: exit_p = p['tp']; reason = 'TP'
            elif p['type'] == 'SHORT':
                if high >= p['sl']: exit_p = p['sl']; reason = 'SL'
                elif low <= p['tp']: exit_p = p['tp']; reason = 'TP'
                
            if exit_p:
                raw = (exit_p - p['entry'])/p['entry'] if p['type']=='LONG' else (p['entry'] - exit_p)/p['entry']
                net = raw - (params['fee']*2)
                amt = p['size'] * net
                balance += amt
                
                # Logic for CB
                if amt > 0:
                    outcome = 'WIN'
                    consecutive_losses = 0 # Reset on win? Or strict sequence? 
                    # User said: "2 wrong trades then pause". Usually implies consecutive.
                else:
                    outcome = 'LOSS'
                    consecutive_losses += 1
                
                # Check Trigger
                if consecutive_losses >= params['cb_threshold_losses']:
                    pause_until = ts + timedelta(hours=params['cb_pause_hours'])
                    print(f"      ⛔ CB TRIGGERED at {ts}: {consecutive_losses} losses. Paused until {pause_until}")
                    consecutive_losses = 0 # Reset counter after triggering? Or keep until win?
                    # Typically reset to avoid permaban
                
                trades.append({
                    'time': ts, 'type': p['type'], 'result': outcome, 'pnl': amt, 
                    'bal': balance, 'active_at_time': len(positions)
                })
                closed_indices.append(idx)
        
        # Remove closed
        for idx in sorted(closed_indices, reverse=True):
            positions.pop(idx)
            
        # Track Drawdown
        if balance > peak_balance: peak_balance = balance
        dd = (peak_balance - balance) / peak_balance
        if dd > max_drawdown: max_drawdown = dd

        # B. Check Entry
        # 1. Are we paused?
        if pause_until and ts < pause_until:
            continue
        if pause_until and ts >= pause_until:
            pause_until = None # Lift pause
        
        # 2. Can we add new?
        if len(positions) < params['max_concurrent']:
            
            p_long = probs[i][1]
            p_short = probs[i][2]
            atr = atr_values[i]
            
            signal = None
            
            # --- V4 STABLE LOGIC (Regime Shield) ---
            if p_long > p_short:
                if p_long > 0.80: signal = 'LONG'
                elif p_long > 0.50 and atr < 70: signal = 'LONG'
            elif p_short > p_long:
                if p_short > 0.80: signal = 'SHORT'
                elif p_short > 0.50 and atr < 70: signal = 'SHORT'
            
            if signal:
                # Check duplication? V4 might fire every candle. 
                # We shouldn't open 3 longs on same candle or adj candles?
                # User wants "Simultaneous" -> assumedly different opportunities or scale-in
                # BUT V4 on 5m will fire 'LONG' at 12:00, 12:05, 12:10 if signal persists.
                # If we open 3 times on same trend, risk is tripled. 
                # Let's simple-check: Don't open if we already have a position in same direction entered recently?
                # Or just max trades. Let's do raw max trades to see worst case (clustering).
                
                tp = price * (1 + params['tp_pct']) if signal == 'LONG' else price * (1 - params['tp_pct'])
                sl = price * (1 - params['sl_pct']) if signal == 'LONG' else price * (1 + params['sl_pct'])
                
                positions.append({
                    'type': signal, 'entry': price, 'size': params['position_size'], 
                    'tp': tp, 'sl': sl, 'entry_ts': ts
                })

    # 5. RESULTS
    print("\n📊 CONCURRENT TRADES SIMULATION (Max 3):")
    print(f"   Period: {start_date} -> {end_date}")
    
    wins = len([t for t in trades if t['pnl'] > 0])
    total = len(trades)
    wr = wins/total if total>0 else 0
    pnl = balance - params['initial_capital']
    
    print(f"   Final Balance: ${balance:.2f} (Start: ${params['initial_capital']})")
    print(f"   Trades: {total} (~{total/12:.1f}/day)")
    print(f"   Win Rate: {wr:.1%} ({wins} W / {total-wins} L)")
    print(f"   PnL: ${pnl:.2f} ({pnl/params['initial_capital']*100:.1f}%)")
    print(f"   Max Drawdown: {max_drawdown:.1%}")
    
    print("\n   Concurrent Load:")
    # How often did we actually have >1 trade?
    multi = len([t for t in trades if t['active_at_time'] > 1]) # Rough proxy
    print(f"   Trades closing with others active: {multi}")

if __name__ == "__main__":
    simulate_concurrent_v4()
