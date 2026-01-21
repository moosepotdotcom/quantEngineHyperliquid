
import pandas as pd
import numpy as np
from datetime import datetime
import os
import sys

# Add root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.fetch_data import fetch_live_data
from utils.feature_engineer import add_all_indicators
from utils.mtf_feature_engineer import MTFFeatureGenerator
from model_engines.mtf_scalper_v3.logic import MTFScalperV3Logic

def verify_regime_shield():
    print("🚀 Verifying 'V4 + Regime Shield' Composite Logic...")
    
    # 1. SETUP
    params = {
        'initial_capital': 10000,
        'position_size': 10000,
        'tp_pct': 0.015,
        'sl_pct': 0.008,
        'fee': 0.0004
    }
    
    start_date = "2026-01-02"
    end_date = "2026-01-14"
    
    # 2. DATA
    print("   📥 Fetching 5m/15m/30m Data...")
    def get_data(tf):
        df = fetch_live_data("BTC", tf, limit=4500)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        # Filter
        s = pd.Timestamp(start_date).tz_localize('UTC')
        e = pd.Timestamp(end_date).tz_localize('UTC') + pd.Timedelta(days=1)
        df = df[(df['timestamp'] >= s) & (df['timestamp'] <= e)]
        # Indicators
        df = add_all_indicators(df)
        return df.sort_values('timestamp').reset_index(drop=True)

    df_5m = get_data('5m')
    df_15m = get_data('15m')
    df_30m = get_data('30m')
    
    # 3. PREDICTIONS
    print("   🧠 Generating Model Predictions...")
    logic = MTFScalperV3Logic()
    gen = MTFFeatureGenerator(df_5m, df_15m, df_30m)
    X_feat, price_df = gen.generate()
    X_feat = X_feat.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    probs = logic.model.predict_proba(X_feat.values)
    
    # Align ATR with predictions
    # price_df index aligns with X_feat rows
    # We need ATR from original df_5m corresponding to these timestamps
    full_df = df_5m.set_index('timestamp').reindex(price_df.index)
    atr_values = full_df['atr_14'].values
    
    # 4. SIMULATION LOOP (With Composite Logic)
    print("\n⚡ Running Simulation Loop...")
    
    balance = params['initial_capital']
    trades = []
    position = None # {type, entry, size, sl, tp}
    
    for i in range(len(price_df)):
        ts = price_df.index[i]
        price = price_df['close'].iloc[i]
        high = price_df['high'].iloc[i]
        low = price_df['low'].iloc[i]
        
        # A. Check Entry
        if not position:
            p_long = probs[i][1]
            p_short = probs[i][2]
            atr = atr_values[i]
            
            signal = None
            
            # --- COMPOSITE LOGIC ---
            if p_long > p_short:
                # 1. Sniper
                if p_long > 0.80: 
                    signal = 'LONG'
                # 2. Shield (Low Volatility Rescue)
                elif p_long > 0.50 and atr < 70:
                    signal = 'LONG'
                    
            elif p_short > p_long:
                # 1. Sniper
                if p_short > 0.80:
                    signal = 'SHORT'
                # 2. Shield
                elif p_short > 0.50 and atr < 70:
                    signal = 'SHORT'
            # -----------------------
            
            if signal:
                # Enter
                # Risk calc
                tp = price * (1 + params['tp_pct']) if signal == 'LONG' else price * (1 - params['tp_pct'])
                sl = price * (1 - params['sl_pct']) if signal == 'LONG' else price * (1 + params['sl_pct'])
                
                position = {
                    'type': signal, 'entry': price, 'size': params['position_size'],
                    'tp': tp, 'sl': sl, 'time': ts
                }
                
        # B. Check Exit (Same candle assumption for simplifiction, or next? 
        # Standard backtest checks exit on current candle if OHLC allows)
        if position:
            p = position
            exit_price = None
            reason = None
            
            # Long Exit
            if p['type'] == 'LONG':
                if low <= p['sl']: exit_price = p['sl']; reason = 'SL'
                elif high >= p['tp']: exit_price = p['tp']; reason = 'TP'
            
            # Short Exit
            elif p['type'] == 'SHORT':
                if high >= p['sl']: exit_price = p['sl']; reason = 'SL'
                elif low <= p['tp']: exit_price = p['tp']; reason = 'TP'
                
            if exit_price:
                # Calc PnL
                raw_roi = (exit_price - p['entry']) / p['entry'] if p['type'] == 'LONG' else (p['entry'] - exit_price) / p['entry']
                net_roi = raw_roi - (params['fee'] * 2) # Entry + Exit fee
                
                pnl_amt = p['size'] * net_roi
                balance += pnl_amt
                
                trades.append({
                    'time': ts, 'type': p['type'], 'reason': reason,
                    'pnl': pnl_amt, 'bal': balance, 'conf': max(probs[i][1], probs[i][2]),
                    'atr': atr_values[i]
                })
                position = None

    # 5. REPORT
    print("\n📊 FINAL RESULTS (V4 + Regime Shield):")
    print(f"   Period: {start_date} -> {end_date}")
    print(f"   Final Balance: ${balance:.2f} (Start: ${params['initial_capital']})")
    
    wins = len([t for t in trades if t['pnl'] > 0])
    losses = len([t for t in trades if t['pnl'] <= 0])
    total = wins + losses
    wr = (wins/total*100) if total > 0 else 0
    
    print(f"   Trades: {total}")
    print(f"   Win Rate: {wr:.1f}% ({wins} W / {losses} L)")
    print(f"   PnL: ${balance - params['initial_capital']:.2f}")
    
    # Analyze Shield Contribution
    shield_trades = [t for t in trades if t['conf'] < 0.80]
    sniper_trades = [t for t in trades if t['conf'] >= 0.80]
    
    print("\n🔍 Breakdown:")
    print(f"   Sniper (>0.80): {len(sniper_trades)} trades")
    print(f"   Shield (<0.80): {len(shield_trades)} trades (ATR < 70)")
    
    if len(shield_trades) > 0:
        shield_wins = len([t for t in shield_trades if t['pnl'] > 0])
        print(f"   Shield Win Rate: {(shield_wins/len(shield_trades))*100:.1f}%")

if __name__ == "__main__":
    verify_regime_shield()
