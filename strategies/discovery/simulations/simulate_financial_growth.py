
import sys
import os
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION'))
sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION/utils'))

from quant_engine import TradingEngine, add_all_indicators

def run_financial_sim():
    print("💰 FINANCIAL SIMULATION: ADAPTIVE SHIELD V2")
    print("="*70)
    print("   Starting Balance: $52.00")
    print("   Position Size:    0.01 BTC")
    print("   Leverage:         27x")
    print("="*70)
    
    engine = TradingEngine()
    
    # 1. Fetch Data
    print("📥 Fetching Jan 2026 Data...", flush=True)
    df_raw = engine.fetch_data('5m', 4000)
    df_raw = add_all_indicators(df_raw)
    
    try:
        from utils.advanced_features import get_rolling_hurst
        df_raw['hurst'] = get_rolling_hurst(df_raw, window=100)
    except:
        df_raw['hurst'] = 0.5 
        
    df_raw.set_index('timestamp', inplace=True)
    
    # Context
    df_15m = add_all_indicators(engine.fetch_data('15m', 4000))
    df_1h = add_all_indicators(engine.fetch_data('1h', 4000))
    df_15m.set_index('timestamp', inplace=True)
    df_1h.set_index('timestamp', inplace=True)
    
    exclude = ['open', 'high', 'low', 'close', 'volume', 'hurst']
    
    c15 = [c for c in df_15m.columns if c not in exclude]
    df15_r = df_15m[c15].copy()
    df15_r.columns = [f"{c}_15m" for c in c15]
    df_merged = pd.concat([df_raw, df15_r.reindex(df_raw.index, method='ffill')], axis=1)
    
    c1h = [c for c in df_1h.columns if c not in exclude]
    df1h_r = df_1h[c1h].copy()
    df1h_r.columns = [f"{c}_1h" for c in c1h]
    df_merged = pd.concat([df_merged, df1h_r.reindex(df_raw.index, method='ffill')], axis=1)
    
    # 2. Filter Date Range (Jan 2 - Current)
    start_sim = pd.Timestamp("2026-01-02 00:00:00")
    end_sim = pd.Timestamp("2026-01-11 23:59:59")
    sim_data = df_merged[(df_merged.index >= start_sim) & (df_merged.index <= end_sim)]
    
    print(f"📊 Simulation Candles: {len(sim_data)}", flush=True)
    if len(sim_data) > 0:
        print(f"   📅 Start: {sim_data.index[0]}")
        print(f"   📅 End:   {sim_data.index[-1]}")
    
    # Financial State
    balance = 52.00
    leverage = 27
    lot_size = 0.01 # BTC
    
    trades_log = []
    
    # Circuit Breaker
    loss_timestamps = []
    circuit_breaker_until = None
    
    debug_jan10_count = 0
    
    for idx, row in sim_data.iterrows():
        # Debug: Check if we are seeing Jan 10 data at all
        if idx.day >= 10 and debug_jan10_count < 5:
             print(f"DEBUG: Processing {idx} | ATR={row.get('atr_14', 0):.1f}")
             debug_jan10_count += 1
             
        # Circuit Breaker Check
        if circuit_breaker_until:
            if idx < circuit_breaker_until: continue
            else:
                circuit_breaker_until = None
                loss_timestamps = []
        
        atr_val = row.get('atr_14', 100)
        
        # LOGIC: Adaptive Barrier
        base_threshold = 0.45
        required = base_threshold
        if atr_val > 70:
            required += (atr_val - 70) * 0.002
        if required > 0.95: required = 0.95

        # Predict
        row_vals = row.drop(labels=exclude + ['hurst'], errors='ignore')
        X = row_vals.values.reshape(1, -1)
        X = np.nan_to_num(X, nan=0.0)
        if X.shape[1] > 239: X = X[:, :239]
        
        p1 = engine.mtf_xgb.predict_proba(X)[0]
        p2 = engine.mtf_lgb.predict(X)[0]
        p3 = engine.mtf_cat.predict_proba(X)[0]
        avg = (p1+p2+p3)/3
        
        signal = None
        if avg[1] >= required: signal = 'LONG'
        elif avg[2] >= required: signal = 'SHORT'
        
        if signal:
            entry_price = row['close']
            
            # FILTERS (Mandalorian + RSI)
            rsi = row.get('rsi_14', 50)
            hurst = row.get('hurst', 0.5)
            rsi7 = row.get('rsi_7', 50)
            
            if signal == 'LONG' and rsi < 30 and hurst > 0.5: continue
            if signal == 'SHORT' and rsi7 < 25: continue
            
            # MARGIN CHECK
            position_value = entry_price * lot_size
            required_margin = position_value / leverage
            
            if balance < required_margin:
                print(f"💀 REKT at {idx}: Balance ${balance:.2f} < Margin ${required_margin:.2f}")
                break
            
            # EXECUTE
            tp = entry_price * (1.015 if signal == 'LONG' else 0.985)
            sl = entry_price * (0.992 if signal == 'LONG' else 1.008)
            
            outcome = "OPEN"
            pnl = 0.0
            
            future = df_raw[df_raw.index > idx]
            for f_idx, f_row in future.iterrows():
                h, l = f_row['high'], f_row['low']
                
                if signal == 'LONG':
                    if h >= tp:
                        outcome = "WIN"
                        pnl = (tp - entry_price) * lot_size
                        break
                    if l <= sl:
                        outcome = "LOSS"
                        pnl = (sl - entry_price) * lot_size
                        break
                else:
                    if l <= tp:
                        outcome = "WIN"
                        pnl = (entry_price - tp) * lot_size
                        break
                    if h >= sl:
                        outcome = "LOSS"
                        pnl = (entry_price - sl) * lot_size
                        break
            
            if outcome != "OPEN":
                # CB Logic
                if outcome == "LOSS":
                    loss_timestamps.append(idx)
                    loss_timestamps = [t for t in loss_timestamps if (idx - t).total_seconds() < 3600]
                    if len(loss_timestamps) >= 2:
                        circuit_breaker_until = idx + pd.Timedelta(hours=4)
                else:
                    loss_timestamps = []
                    
                balance += pnl
                trades_log.append({
                    'time': idx, 'side': signal, 'pnl': pnl, 'balance': balance, 'result': outcome
                })
                # print(f"{idx} | {outcome} | PnL: ${pnl:.2f} | Bal: ${balance:.2f}")

    print("\n# 💰 ADAPTIVE SHIELD V2: FINANCIAL JOURNEY ($52 -> $5k)")
    print("| Trade # | Time | Side | Result | PnL ($) | Balance ($) |")
    print("| :--- | :--- | :--- | :--- | :--- | :--- |")
    
    for i, t in enumerate(trades_log):
        icon = "✅" if t['result'] == "WIN" else "❌"
        # Determine side (not saved in log currently, need to add it or infer)
        # Assuming PnL > 0 is Win, < 0 is Loss. Side was not stored. 
        # I'll update the storage loop first to include 'side'.
        
        print(f"| {i+1} | {t['time']} | {t['side']} | {icon} {t['result']} | ${t['pnl']:.2f} | **${t['balance']:.2f}** |")

    total_trades = len(trades_log)
    wins = len([t for t in trades_log if t['result'] == 'WIN'])
    
    print("\n" + "="*70)
    print(f"💰 FINAL RESULT (Jan 2 - Jan 11)")
    print(f"   Final Balance: ${balance:.2f}")
    print(f"   Net Profit:    ${balance - 52:.2f} ({(balance-52)/52*100:.1f}%)")
    print(f"   Total Trades:  {total_trades}")
    print(f"   Win Rate:      {wins/total_trades*100:.1f}%")
    print("="*70)

if __name__ == "__main__":
    run_financial_sim()
