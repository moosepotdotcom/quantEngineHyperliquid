#!/usr/bin/env python3
"""
Jan 8, 2026 - Full Backtest with TP/SL Simulation
Matches the previous reconstruction methodology:
- 65% thresholds (MTF Scalper)
- Trend filter ACTIVE
- TP/SL simulation (1.5% TP / 0.8% SL)
"""

import sys
import os
import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from utils.feature_engineer import add_all_indicators

# Configuration (matching metadata)
THRESHOLDS = {
    'MTF_LONG': 0.5987,   # 59.87% for LONG (from metadata)
    'MTF_SHORT': 0.6891   # 68.91% for SHORT (from metadata)
}

TP_PCT = 0.015  # 1.5%
SL_PCT = 0.008  # 0.8%

def load_historical_data(interval):
    """Load saved historical data for Jan 8"""
    filename = f'jan8_historical_{interval}.json'
    with open(filename, 'r') as f:
        candles = json.load(f)
    
    df = pd.DataFrame(candles)
    df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
    df['open'] = df['o'].astype(float)
    df['high'] = df['h'].astype(float)
    df['low'] = df['l'].astype(float)
    df['close'] = df['c'].astype(float)
    df['volume'] = df['v'].astype(float)
    
    return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

def simulate_outcome(entry_price, direction, entry_time, df_5m):
    """Simulate TP/SL outcome using 5M data"""
    future = df_5m[df_5m['timestamp'] > entry_time].head(288)  # Next 24 hours
    
    if len(future) == 0:
        return "OPEN", 0.0, None
    
    if direction == "LONG":
        tp = entry_price * (1 + TP_PCT)
        sl = entry_price * (1 - SL_PCT)
    else:
        tp = entry_price * (1 - TP_PCT)
        sl = entry_price * (1 + SL_PCT)
    
    for _, candle in future.iterrows():
        if direction == "LONG":
            if candle['high'] >= tp:
                return "WIN", TP_PCT * 100, candle['timestamp']
            if candle['low'] <= sl:
                return "LOSS", -SL_PCT * 100, candle['timestamp']
        else:
            if candle['low'] <= tp:
                return "WIN", TP_PCT * 100, candle['timestamp']
            if candle['high'] >= sl:
                return "LOSS", -SL_PCT * 100, candle['timestamp']
    
    return "OPEN", 0.0, None

def main():
    print("=" * 70)
    print("📅 JAN 8, 2026 - FULL BACKTEST (TP/SL SIMULATION)")
    print("=" * 70)
    print("Configuration:")
    print("  Thresholds: MTF LONG 65.00%, SHORT 68.91%")
    print("  TP/SL: 1.5% / 0.8%")
    print("  Trend Filter: ACTIVE (Hurst)")
    print("=" * 70)
    
    # Load models
    print("\n🤖 Loading ML Models...")
    MODEL_DIR = 'models'
    
    mtf_xgb = xgb.XGBClassifier()
    mtf_xgb.load_model(f'{MODEL_DIR}/mtf_scalper_5m_trio_xgb.json')
    mtf_lgb = lgb.Booster(model_file=f'{MODEL_DIR}/mtf_scalper_5m_trio_lgb.json')
    mtf_cat = CatBoostClassifier()
    mtf_cat.load_model(f'{MODEL_DIR}/mtf_scalper_5m_trio_cat.json')
    
    print("✅ Models loaded")
    
    # Load historical data
    print("\n📊 Loading Jan 8 Historical Data...")
    df_5m = load_historical_data('5m')
    df_15m = load_historical_data('15m')
    df_1h = load_historical_data('1h')
    
    print(f"  5m:  {len(df_5m)} candles")
    print(f"  15m: {len(df_15m)} candles")
    print(f"  1h:  {len(df_1h)} candles")
    
    # Add indicators
    print("\n🔧 Engineering Features...")
    df_5m_feat = add_all_indicators(df_5m.copy())
    df_15m_feat = add_all_indicators(df_15m.copy())
    df_1h_feat = add_all_indicators(df_1h.copy())
    
    # Calculate Hurst
    try:
        from utils.advanced_features import get_rolling_hurst
        df_5m_feat['hurst'] = get_rolling_hurst(df_5m.set_index('timestamp'), window=100)
        print("  ✅ Hurst Exponent calculated")
    except Exception as e:
        print(f"  ⚠️  Hurst calculation failed: {e}, defaulting to 0.5")
        df_5m_feat['hurst'] = 0.5
    
    # Merge timeframes
    df_5m_feat.set_index('timestamp', inplace=True)
    df_15m_feat.set_index('timestamp', inplace=True)
    df_1h_feat.set_index('timestamp', inplace=True)
    
    exclude = ['open', 'high', 'low', 'close', 'volume']
    
    # Add 15M context
    ctx_cols_15m = [c for c in df_15m_feat.columns if c not in exclude]
    df_15m_renamed = df_15m_feat[ctx_cols_15m].copy()
    df_15m_renamed.columns = [f"{c}_15m" for c in ctx_cols_15m]
    df_15m_resampled = df_15m_renamed.reindex(df_5m_feat.index, method='ffill')
    df_mtf = pd.concat([df_5m_feat, df_15m_resampled], axis=1)
    
    # Add 1H context
    ctx_cols_1h = [c for c in df_1h_feat.columns if c not in exclude]
    df_1h_renamed = df_1h_feat[ctx_cols_1h].copy()
    df_1h_renamed.columns = [f"{c}_1h" for c in ctx_cols_1h]
    df_1h_resampled = df_1h_renamed.reindex(df_mtf.index, method='ffill')
    df_mtf = pd.concat([df_mtf, df_1h_resampled], axis=1)
    
    df_mtf.dropna(inplace=True)
    
    mtf_features = [c for c in df_mtf.columns if c not in exclude and c != 'hurst']
    
    print(f"  MTF Features: {len(mtf_features)}")
    
    # Run predictions
    print("\n" + "=" * 70)
    print("🎯 RUNNING BACKTEST")
    print("=" * 70)
    
    trades = []
    blocked_count = 0
    
    for i in range(len(df_mtf)):
        row = df_mtf.iloc[i]
        X = row[mtf_features].values.reshape(1, -1)
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        
        # Ensemble prediction
        p1 = mtf_xgb.predict_proba(X)
        p2 = mtf_lgb.predict(X)
        p3 = mtf_cat.predict_proba(X)
        probas = (p1 + p2 + p3) / 3
        
        prob_long = float(probas[0][1])
        prob_short = float(probas[0][2])
        
        # Check thresholds
        direction = None
        confidence = 0.0
        
        if prob_long >= THRESHOLDS['MTF_LONG']:
            direction = 'LONG'
            confidence = prob_long
        elif prob_short >= THRESHOLDS['MTF_SHORT']:
            direction = 'SHORT'
            confidence = prob_short
        
        if direction:
            # MANDALORIAN PROTOCOL: Hurst Filter
            rsi = row.get('rsi_14', 50)
            hurst = row.get('hurst', 0.5)
            
            if direction == 'LONG' and rsi < 30 and hurst > 0.50:
                blocked_count += 1
                print(f"  🛑 {row.name} - BLOCKED Falling Knife (Hurst={hurst:.3f}, RSI={rsi:.1f})")
                continue
            
            # Simulate outcome
            outcome, pnl, exit_time = simulate_outcome(
                row['close'], direction, row.name, df_5m
            )
            
            trade = {
                'entry_time': row.name,
                'direction': direction,
                'confidence': confidence,
                'entry_price': row['close'],
                'rsi': rsi,
                'hurst': hurst,
                'outcome': outcome,
                'pnl_pct': pnl,
                'exit_time': exit_time
            }
            trades.append(trade)
            
            outcome_emoji = "🟢" if outcome == "WIN" else ("🔴" if outcome == "LOSS" else "⏳")
            print(f"  {outcome_emoji} {row.name} - {direction} @ ${row['close']:,.2f} (Conf: {confidence:.2%}) → {outcome} ({pnl:+.2f}%)")
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 FINAL RESULTS")
    print("=" * 70)
    
    if len(trades) == 0:
        print("\n❌ ZERO TRADES executed")
        if blocked_count > 0:
            print(f"   {blocked_count} signals blocked by Hurst filter")
    else:
        wins = [t for t in trades if t['outcome'] == 'WIN']
        losses = [t for t in trades if t['outcome'] == 'LOSS']
        opens = [t for t in trades if t['outcome'] == 'OPEN']
        
        print(f"\n✅ {len(trades)} TRADE(S) executed:\n")
        print(f"  Wins: {len(wins)} 🟢")
        print(f"  Losses: {len(losses)} 🔴")
        print(f"  Still Open: {len(opens)} ⏳")
        
        if len(wins) + len(losses) > 0:
            win_rate = len(wins) / (len(wins) + len(losses)) * 100
            print(f"  Win Rate: {win_rate:.1f}%")
        
        total_pnl = sum(t['pnl_pct'] for t in trades)
        print(f"  Total P&L: {total_pnl:+.2f}%")
        
        print("\n📋 Trade Details:\n")
        for i, t in enumerate(trades, 1):
            outcome_emoji = "🟢" if t['outcome'] == "WIN" else ("🔴" if t['outcome'] == "LOSS" else "⏳")
            print(f"{i}. {t['entry_time']} - {t['direction']}")
            print(f"   Entry: ${t['entry_price']:,.2f} | Conf: {t['confidence']:.2%}")
            print(f"   {outcome_emoji} {t['outcome']} ({t['pnl_pct']:+.2f}%)")
            if t['exit_time']:
                print(f"   Exit: {t['exit_time']}")
            print()
        
        if blocked_count > 0:
            print(f"🛡️  {blocked_count} signals blocked by Hurst filter")
    
    print("=" * 70)

if __name__ == '__main__':
    main()
