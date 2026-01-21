#!/usr/bin/env python3
"""
🎯 93% ML ENGINE BACKTEST: Jan 2-16, 2026
400x Leverage | 0.5 BTC Position Size | $100,000 Initial Balance
Full ML Models + Shields + Circuit Breaker
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Logic Imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quant_engine import TradingEngine, add_all_indicators, MTF_FEATURE_LIST, CircuitBreaker

# ==================== CONFIGURATION ====================
LEVERAGE = 400
POSITION_SIZE_BTC = 0.5
INITIAL_BALANCE = 100000.0
TP_PCT = 0.015  # 1.5%
SL_PCT = 0.008  # 0.8%

START_DATE = "2026-01-02 00:00:00"
END_DATE = "2026-01-16 23:59:59"

def ml_engine_backtest():
    print("=" * 80)
    print("🎯 93% ML ENGINE BACKTEST")
    print(f"   Period: Jan 2 - Jan 16, 2026")
    print(f"   Leverage: {LEVERAGE}x | Position Size: {POSITION_SIZE_BTC} BTC")
    print(f"   Initial Balance: ${INITIAL_BALANCE:,.0f}")
    print("=" * 80)
    
    engine = TradingEngine()
    
    # 1. Fetch & Pre-calculate
    print("\n📥 Fetching & Pre-calculating Indicators...", flush=True)
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
    mask = (df_merged.index >= START_DATE) & (df_merged.index <= END_DATE)
    sim_data = df_merged[mask]
    
    print(f"🔄 Simulating {len(sim_data)} timestamps...")
    print("=" * 80)
    
    # Trackers
    breaker = CircuitBreaker(max_losses=2, window_minutes=60, cooldown_hours=4)
    trades = []
    balance = INITIAL_BALANCE
    trade_id = 0
    
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
            
            # --- SHIELDS ENABLED (NO ATR PENALTY) ---
            USE_SHIELDS = True
            
            if USE_SHIELDS:
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
            tp_p = entry * (1 + TP_PCT) if direction == 'LONG' else entry * (1 - TP_PCT)
            sl_p = entry * (1 - SL_PCT) if direction == 'LONG' else entry * (1 + SL_PCT)
            
            # Calculate margin
            margin = (POSITION_SIZE_BTC * entry) / LEVERAGE
            
            # Outcome (lookahead) - SEARCH ALL FUTURE DATA UNTIL TP/SL
            future = df5[df5.index > timestamp]  # NO LIMIT - search until resolved
            outcome = "EXPIRED"
            exit_price = entry
            exit_time = timestamp
            
            for exit_time, f_row in future.iterrows():
                h, l = f_row['high'], f_row['low']
                if direction == 'LONG':
                    if h >= tp_p: 
                        outcome = 'WIN'
                        exit_price = tp_p
                        break
                    if l <= sl_p: 
                        outcome = 'LOSS'
                        exit_price = sl_p
                        break
                else:
                    if l <= tp_p: 
                        outcome = 'WIN'
                        exit_price = tp_p
                        break
                    if h >= sl_p: 
                        outcome = 'LOSS'
                        exit_price = sl_p
                        break
            
            # Calculate PnL
            if direction == 'LONG':
                price_change = exit_price - entry
            else:
                price_change = entry - exit_price
            
            pnl_usd = price_change * POSITION_SIZE_BTC
            roe = (pnl_usd / margin) * 100
            balance += pnl_usd
            
            # Update Breaker
            if outcome == 'WIN':
                breaker.cooldown_until = None
            elif outcome == 'LOSS':
                if not hasattr(breaker, 'sim_losses'): breaker.sim_losses = []
                breaker.sim_losses = [t for t in breaker.sim_losses if (timestamp - t).total_seconds() < 3600]
                breaker.sim_losses.append(timestamp)
                if len(breaker.sim_losses) >= 2:
                    breaker.cooldown_until = timestamp + pd.Timedelta(hours=4)
                    print(f"   🛑 CIRCUIT BREAKER ACTIVATED until {breaker.cooldown_until.strftime('%m-%d %H:%M')}")
            
            trade_id += 1
            duration = (exit_time - timestamp).total_seconds() / 60
            
            # Log trade
            emoji = "✅" if outcome == "WIN" else "❌" if outcome == "LOSS" else "⏱️"
            if outcome != "EXPIRED":
                print(f"{emoji} #{trade_id:03d} | {direction:5s} | ${entry:>7,.0f} → ${exit_price:>7,.0f} | {outcome:4s} | ${pnl_usd:>+8,.2f} | ROE: {roe:>+6.1f}% | {duration:.0f}m | Bal: ${balance:>10,.2f}")
            
            trades.append({
                'id': trade_id,
                'timestamp': timestamp,
                'exit_timestamp': exit_time,
                'direction': direction,
                'entry_price': entry,
                'exit_price': exit_price,
                'tp_price': tp_p,
                'sl_price': sl_p,
                'outcome': outcome,
                'pnl_usd': pnl_usd,
                'roe': roe,
                'margin': margin,
                'balance': balance,
                'atr': atr,
                'confidence': confidence,
                'duration_minutes': duration
            })
            
    # Final Report
    print("\n" + "=" * 80)
    print("📊 BACKTEST RESULTS")
    print("=" * 80)
    
    total = len(trades)
    if total > 0:
        wins = len([t for t in trades if t['outcome'] == 'WIN'])
        losses = len([t for t in trades if t['outcome'] == 'LOSS'])
        expired = len([t for t in trades if t['outcome'] == 'EXPIRED'])
        
        valid_trades = wins + losses
        wr = (wins / valid_trades * 100) if valid_trades > 0 else 0
        
        total_pnl = sum(t['pnl_usd'] for t in trades if t['outcome'] != 'EXPIRED')
        roi = ((balance - INITIAL_BALANCE) / INITIAL_BALANCE) * 100
        
        print(f"Total Trades:     {total}")
        print(f"Wins:             {wins} ✅")
        print(f"Losses:           {losses} ❌")
        print(f"Expired:          {expired} ⏱️")
        print(f"Win Rate:         {wr:.1f}% ({wins}/{valid_trades} valid)")
        print(f"Total PnL:        ${total_pnl:+,.2f}")
        print(f"Final Balance:    ${balance:,.2f}")
        print(f"ROI:              {roi:+.2f}%")
        
        # Save detailed log
        df_trades = pd.DataFrame(trades)
        df_trades.to_csv('backtest_ml_jan2_jan16_detailed.csv', index=False)
        print(f"\n💾 Detailed trade log saved to: backtest_ml_jan2_jan16_detailed.csv")
    else:
        print("❌ No trades executed.")
    
    print("=" * 80)

if __name__ == "__main__":
    ml_engine_backtest()
