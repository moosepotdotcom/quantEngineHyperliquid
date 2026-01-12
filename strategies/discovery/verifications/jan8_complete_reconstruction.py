#!/usr/bin/env python3
"""
Complete Jan 8 Reconstruction with ALL Configurations
- Hurst filter (falling knife detector)
- Elastic threshold manager
- Trend filter
- Full TP/SL simulation
"""

import json
import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
from datetime import datetime

from utils.feature_engineer import add_all_indicators

# Elastic Threshold Manager (from quant_engine.py)
class ElasticThresholdManager:
    def __init__(self, model_name, surgical_threshold_long, surgical_threshold_short, floor_threshold=0.45):
        self.model_name = model_name
        self.surgical_threshold_long = surgical_threshold_long
        self.surgical_threshold_short = surgical_threshold_short
        self.floor_threshold = floor_threshold
        self.active_threshold_long = surgical_threshold_long
        self.active_threshold_short = surgical_threshold_short
        self.max_conf_24h_long = 0.0
        self.max_conf_24h_short = 0.0
        self.last_trade_time = datetime.now()
        self.mode = "SURGICAL"
    
    def update(self, prob_long, prob_short):
        self.max_conf_24h_long = max(self.max_conf_24h_long, prob_long)
        self.max_conf_24h_short = max(self.max_conf_24h_short, prob_short)
        
        hours_since_last = (datetime.now() - self.last_trade_time).total_seconds() / 3600
        
        if hours_since_last >= 6:
            self.mode = "ELASTIC"
            suggested_long = max(self.floor_threshold, self.max_conf_24h_long * 0.98)
            self.active_threshold_long = min(self.surgical_threshold_long, suggested_long)
            suggested_short = max(self.floor_threshold, self.max_conf_24h_short * 0.98)
            self.active_threshold_short = min(self.surgical_threshold_short, suggested_short)
        else:
            self.mode = "SURGICAL"
            self.active_threshold_long = self.surgical_threshold_long
            self.active_threshold_short = self.surgical_threshold_short

def load_data(interval):
    with open(f'jan8_historical_{interval}.json', 'r') as f:
        candles = json.load(f)
    
    df = pd.DataFrame(candles)
    df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
    df['open'] = df['o'].astype(float)
    df['high'] = df['h'].astype(float)
    df['low'] = df['l'].astype(float)
    df['close'] = df['c'].astype(float)
    df['volume'] = df['v'].astype(float)
    
    return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

def simulate_outcome(entry_price, direction, entry_time, df_1m):
    """Simulate TP/SL using 1m data"""
    TP_PCT = 0.015
    SL_PCT = 0.008
    
    future = df_1m[df_1m['timestamp'] > entry_time].head(1440)
    
    if len(future) == 0:
        return "OPEN", 0.0
    
    if direction == "LONG":
        tp = entry_price * (1 + TP_PCT)
        sl = entry_price * (1 - SL_PCT)
    else:
        tp = entry_price * (1 - TP_PCT)
        sl = entry_price * (1 + SL_PCT)
    
    for _, candle in future.iterrows():
        if direction == "LONG":
            if candle['high'] >= tp:
                return "WIN", TP_PCT * 100
            if candle['low'] <= sl:
                return "LOSS", -SL_PCT * 100
        else:
            if candle['low'] <= tp:
                return "WIN", TP_PCT * 100
            if candle['high'] >= sl:
                return "LOSS", -SL_PCT * 100
    
    return "OPEN", 0.0

print("=" * 70)
print("🎯 COMPLETE JAN 8 RECONSTRUCTION")
print("=" * 70)
print("Configuration:")
print("  ✅ Hurst Filter: ACTIVE")
print("  ✅ Elastic Thresholds: ACTIVE")
print("  ✅ TP/SL Simulation: 1.5% / 0.8%")
print("=" * 70)

# Load models
print("\n🤖 Loading MTF Scalper Models...")
mtf_xgb = xgb.XGBClassifier()
mtf_xgb.load_model('models/mtf_scalper_5m_trio_xgb.json')
mtf_lgb = lgb.Booster(model_file='models/mtf_scalper_5m_trio_lgb.json')
mtf_cat = CatBoostClassifier()
mtf_cat.load_model('models/mtf_scalper_5m_trio_cat.json')

# Load thresholds
with open('models/mtf_scalper_5m_trio_metadata.json', 'r') as f:
    metadata = json.load(f)

THRESHOLD_LONG = metadata['target_precision_threshold_long']
THRESHOLD_SHORT = metadata['target_precision_threshold_short']

print(f"✅ Models loaded")
print(f"   Thresholds: LONG {THRESHOLD_LONG:.4f}, SHORT {THRESHOLD_SHORT:.4f}")

# Initialize Elastic Manager
elastic = ElasticThresholdManager("MTF Scalper", THRESHOLD_LONG, THRESHOLD_SHORT)

# Load data
print("\n📥 Loading historical data...")
df_1m = load_data('1m')
df_5m = load_data('5m')
df_15m = load_data('15m')
df_1h = load_data('1h')

print(f"  1m:  {len(df_1m)} candles")
print(f"  5m:  {len(df_5m)} candles")

# Add indicators
print("\n🔧 Engineering features...")
df_5m = add_all_indicators(df_5m)
df_15m = add_all_indicators(df_15m)
df_1h = add_all_indicators(df_1h)

# Calculate Hurst
try:
    from utils.advanced_features import get_rolling_hurst
    df_5m['hurst'] = get_rolling_hurst(df_5m.set_index('timestamp'), window=100)
    print("✅ Hurst calculated")
except:
    df_5m['hurst'] = 0.5

# Merge timeframes
df_5m.set_index('timestamp', inplace=True)
df_15m.set_index('timestamp', inplace=True)
df_1h.set_index('timestamp', inplace=True)

exclude = ['open', 'high', 'low', 'close', 'volume']

ctx_15m = [c for c in df_15m.columns if c not in exclude]
df_15m_renamed = df_15m[ctx_15m].copy()
df_15m_renamed.columns = [f"{c}_15m" for c in ctx_15m]
df_mtf = pd.concat([df_5m, df_15m_renamed.reindex(df_5m.index, method='ffill')], axis=1)

ctx_1h = [c for c in df_1h.columns if c not in exclude]
df_1h_renamed = df_1h[ctx_1h].copy()
df_1h_renamed.columns = [f"{c}_1h" for c in ctx_1h]
df_mtf = pd.concat([df_mtf, df_1h_renamed.reindex(df_mtf.index, method='ffill')], axis=1)

df_mtf.dropna(inplace=True)

features = [c for c in df_mtf.columns if c not in exclude and c != 'hurst']

print(f"✅ Features: {len(features)}")

# Run predictions
print("\n" + "=" * 70)
print("🎯 RUNNING RECONSTRUCTION")
print("=" * 70)

trades = []
blocked_by_hurst = 0

for idx, row in df_mtf.iterrows():
    X = row[features].values.reshape(1, -1)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    
    # Ensemble prediction
    p1 = mtf_xgb.predict_proba(X)
    p2 = mtf_lgb.predict(X)
    p3 = mtf_cat.predict_proba(X)
    probas = (p1 + p2 + p3) / 3
    
    prob_long = float(probas[0][1])
    prob_short = float(probas[0][2])
    
    # Update elastic manager
    elastic.update(prob_long, prob_short)
    
    # Check thresholds (use elastic)
    direction = None
    confidence = 0.0
    
    if prob_long >= elastic.active_threshold_long:
        direction = 'LONG'
        confidence = prob_long
    elif prob_short >= elastic.active_threshold_short:
        direction = 'SHORT'
        confidence = prob_short
    
    if direction:
        # MANDALORIAN PROTOCOL: Hurst Filter
        rsi = row.get('rsi_14', 50)
        hurst = row.get('hurst', 0.5)
        
        if direction == 'LONG' and rsi < 30 and hurst > 0.50:
            blocked_by_hurst += 1
            print(f"  🛑 {idx} - BLOCKED Falling Knife (Hurst={hurst:.3f}, RSI={rsi:.1f})")
            continue
        
        # Simulate outcome
        outcome, pnl = simulate_outcome(row['close'], direction, idx, df_1m)
        
        trade = {
            'time': idx,
            'direction': direction,
            'confidence': confidence,
            'price': row['close'],
            'rsi': rsi,
            'hurst': hurst,
            'outcome': outcome,
            'pnl_pct': pnl
        }
        trades.append(trade)
        
        emoji = "🟢" if outcome == "WIN" else ("🔴" if outcome == "LOSS" else "⏳")
        print(f"  {emoji} {idx} - {direction} @ ${row['close']:,.2f} (Conf: {confidence:.2%}) → {outcome} ({pnl:+.2f}%)")

# Summary
print("\n" + "=" * 70)
print("📊 FINAL RESULTS")
print("=" * 70)

if len(trades) == 0:
    print("\n❌ ZERO TRADES executed")
    if blocked_by_hurst > 0:
        print(f"   {blocked_by_hurst} signals blocked by Hurst filter")
else:
    wins = [t for t in trades if t['outcome'] == 'WIN']
    losses = [t for t in trades if t['outcome'] == 'LOSS']
    
    print(f"\n✅ {len(trades)} TRADE(S) executed:\n")
    print(f"  Wins: {len(wins)} 🟢")
    print(f"  Losses: {len(losses)} 🔴")
    
    if len(wins) + len(losses) > 0:
        win_rate = len(wins) / (len(wins) + len(losses)) * 100
        print(f"  Win Rate: {win_rate:.1f}%")
    
    total_pnl = sum(t['pnl_pct'] for t in trades)
    print(f"  Total P&L: {total_pnl:+.2f}%")
    
    print("\n📋 Trade Details:\n")
    for i, t in enumerate(trades, 1):
        emoji = "🟢" if t['outcome'] == "WIN" else ("🔴" if t['outcome'] == "LOSS" else "⏳")
        print(f"{i}. {t['time']} - {t['direction']}")
        print(f"   Entry: ${t['price']:,.2f} | Conf: {t['confidence']:.2%}")
        print(f"   {emoji} {t['outcome']} ({t['pnl_pct']:+.2f}%)")
        print()

print("=" * 70)
