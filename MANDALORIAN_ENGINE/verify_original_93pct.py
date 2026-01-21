#!/usr/bin/env python3
"""
Verify original 93% win rate on Jan 2-9 period
"""

import sys
import os
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, '/Users/alifiyaa/Downloads/quantEngineHyperliquid/MANDALORIAN_ENGINE')
from quant_engine import TradingEngine, add_all_indicators, MTF_FEATURE_LIST

# Original config
LEVERAGE = 400
POSITION_SIZE_BTC = 0.5
INITIAL_BALANCE = 100000.0
TP_PCT = 0.015
SL_PCT = 0.008
BASE_THRESHOLD = 0.45
ATR_THRESHOLD = 70
ATR_PENALTY = 0.002

START_DATE = "2026-01-02"
END_DATE = "2026-01-09"  # Original verification period

class Tracker:
    def __init__(self):
        self.trades = []
    
def run_verification():
    print("=" * 80)
    print("🔍 VERIFYING ORIGINAL 93% WIN RATE (Jan 2-9)")
    print("=" * 80)
    
    engine = TradingEngine()
    tracker = Tracker()
    
    print(f"\n📊 Fetching Jan 2-9 data...")
    
    df5 = engine.fetch_data('5m', limit=3000)
    df15 = engine.fetch_data('15m', limit=3000)
    df1h = engine.fetch_data('1h', limit=3000)
    
    df5['timestamp'] = pd.to_datetime(df5['timestamp'])
    df15['timestamp'] = pd.to_datetime(df15['timestamp'])
    df1h['timestamp'] = pd.to_datetime(df1h['timestamp'])
    
    df5 = df5[(df5['timestamp'] >= START_DATE) & (df5['timestamp'] <= END_DATE)]
    df15 = df15[(df15['timestamp'] >= START_DATE) & (df15['timestamp'] <= END_DATE)]
    df1h = df1h[(df1h['timestamp'] >= START_DATE) & (df1h['timestamp'] <= END_DATE)]
    
    print(f"✅ Filtered to {len(df5)} candles")
    
    df5 = add_all_indicators(df5)
    df15 = add_all_indicators(df15)
    df1h = add_all_indicators(df1h)
    
    df5.set_index('timestamp', inplace=True)
    df15.set_index('timestamp', inplace=True)
    df1h.set_index('timestamp', inplace=True)
    
    exclude = ['open', 'high', 'low', 'close', 'volume']
    ctx15 = [c for c in df15.columns if c not in exclude]
    df15_renamed = df15[ctx15].copy().rename(columns={c: f"{c}_15m" for c in ctx15})
    df_merged = pd.concat([df5, df15_renamed.reindex(df5.index, method='ffill')], axis=1)
    
    ctx1h = [c for c in df1h.columns if c not in exclude]
    df1h_renamed = df1h[ctx1h].copy().rename(columns={c: f"{c}_1h" for c in ctx1h})
    df_merged = pd.concat([df_merged, df1h_renamed.reindex(df5.index, method='ffill')], axis=1)
    
    df_merged.dropna(inplace=True)
    
    print(f"🚀 Running verification...\n")
    
    recent_losses = []
    cooldown_until = None
    position = None
    
    for idx, row in df_merged.iterrows():
        timestamp = idx
        
        # Check exit
        if position:
            hit_tp = False
            hit_sl = False
            
            if position['direction'] == "LONG":
                if row['high'] >= position['tp_price']:
                    hit_tp = True
                elif row['low'] <= position['sl_price']:
                    hit_sl = True
            else:
                if row['low'] <= position['tp_price']:
                    hit_tp = True
                elif row['high'] >= position['sl_price']:
                    hit_sl = True
            
            if hit_tp or hit_sl:
                result = "WIN" if hit_tp else "LOSS"
                tracker.trades.append(result)
                emoji = "✅" if hit_tp else "❌"
                print(f"{emoji} Trade #{len(tracker.trades)}: {position['direction']} | {result} | ATR: {position['atr']:.1f} | Threshold: {position['threshold']*100:.1f}%")
                
                if result == "LOSS":
                    recent_losses = [t for t in recent_losses if (timestamp - t).total_seconds() < 3600]
                    recent_losses.append(timestamp)
                    if len(recent_losses) >= 2:
                        cooldown_until = timestamp + pd.Timedelta(hours=4)
                        print(f"   🛑 CIRCUIT BREAKER")
                else:
                    recent_losses = []
                
                position = None
        
        # Check entry
        if not position:
            if cooldown_until and timestamp < cooldown_until:
                continue
            
            X_dict = {c: row.get(c, 0.0) for c in MTF_FEATURE_LIST}
            X = np.array([X_dict[c] for c in MTF_FEATURE_LIST]).reshape(1, -1)
            X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
            
            probas = engine.get_ensemble_proba('MTF', X)[0]
            prob_long, prob_short = float(probas[1]), float(probas[2])
            
            atr_val = row.get('atr_14', 100)
            required_threshold = BASE_THRESHOLD
            
            if atr_val > ATR_THRESHOLD:
                excess_atr = atr_val - ATR_THRESHOLD
                penalty = excess_atr * ATR_PENALTY
                required_threshold = BASE_THRESHOLD + penalty
                if required_threshold > 0.95:
                    required_threshold = 0.95
            
            direction = None
            confidence = 0.0
            
            if prob_long >= required_threshold:
                direction = 'LONG'
                confidence = prob_long
            elif prob_short >= required_threshold:
                direction = 'SHORT'
                confidence = prob_short
            
            if direction:
                hurst = row.get('hurst', 0.5)
                rsi = row.get('rsi_14', 50)
                rsi7 = row.get('rsi_7', 50)
                
                if direction == 'LONG' and rsi < 30 and hurst > 0.5:
                    continue
                if direction == 'SHORT' and rsi7 < 25:
                    continue
                
                tp_price = row['close'] * (1 + TP_PCT) if direction == "LONG" else row['close'] * (1 - TP_PCT)
                sl_price = row['close'] * (1 - SL_PCT) if direction == "LONG" else row['close'] * (1 + SL_PCT)
                
                position = {
                    'direction': direction,
                    'entry_price': row['close'],
                    'tp_price': tp_price,
                    'sl_price': sl_price,
                    'atr': atr_val,
                    'threshold': required_threshold
                }
                
                print(f"📍 Trade #{len(tracker.trades)+1}: OPEN {direction} @ ${row['close']:,.0f} | Confidence: {confidence*100:.1f}%")
    
    print("\n" + "=" * 80)
    print("📊 VERIFICATION RESULTS (Jan 2-9)")
    print("=" * 80)
    
    total = len(tracker.trades)
    wins = tracker.trades.count("WIN")
    losses = tracker.trades.count("LOSS")
    wr = (wins/total * 100) if total > 0 else 0
    
    print(f"Total Trades: {total}")
    print(f"Wins: {wins} | Losses: {losses}")
    print(f"Win Rate: {wr:.1f}%")
    print("=" * 80)

if __name__ == "__main__":
    run_verification()
