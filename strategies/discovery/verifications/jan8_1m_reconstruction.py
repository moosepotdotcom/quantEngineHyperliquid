#!/usr/bin/env python3
"""
Jan 8 Reconstruction with 1-Minute Data
Uses 1m candles to get closer to the actual trade timestamps
"""

import json
import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
from datetime import datetime

from utils.feature_engineer import add_all_indicators

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

print("=" * 70)
print("🎯 JAN 8 RECONSTRUCTION WITH 1-MINUTE DATA")
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

THRESHOLD_SHORT = metadata['target_precision_threshold_short']
print(f"✅ Models loaded (Threshold: {THRESHOLD_SHORT:.4f})")

# Load data - use 1m for fine-grained analysis
print("\n📥 Loading historical data...")
df_1m = load_data('1m')
df_5m = load_data('5m')
df_15m = load_data('15m')
df_1h = load_data('1h')

print(f"  1m:  {len(df_1m)} candles")
print(f"  5m:  {len(df_5m)} candles")
print(f"  15m: {len(df_15m)} candles")
print(f"  1h:  {len(df_1h)} candles")

# Resample 1m to 5m for feature engineering
print("\n🔧 Resampling 1m to 5m...")
df_1m.set_index('timestamp', inplace=True)
df_5m_from_1m = df_1m.resample('5T').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}).dropna()
df_5m_from_1m.reset_index(inplace=True)

print(f"  Resampled: {len(df_5m_from_1m)} 5m candles")

# Add indicators
print("\n🔧 Engineering features...")
df_5m_feat = add_all_indicators(df_5m_from_1m.copy())
df_15m_feat = add_all_indicators(df_15m.copy())
df_1h_feat = add_all_indicators(df_1h.copy())

# Calculate Hurst
try:
    from utils.advanced_features import get_rolling_hurst
    df_5m_feat['hurst'] = get_rolling_hurst(df_5m_from_1m.set_index('timestamp'), window=100)
    print("✅ Hurst calculated")
except:
    df_5m_feat['hurst'] = 0.5

# Merge timeframes
df_5m_feat.set_index('timestamp', inplace=True)
df_15m_feat.set_index('timestamp', inplace=True)
df_1h_feat.set_index('timestamp', inplace=True)

exclude = ['open', 'high', 'low', 'close', 'volume']

# 15M context
ctx_15m = [c for c in df_15m_feat.columns if c not in exclude]
df_15m_renamed = df_15m_feat[ctx_15m].copy()
df_15m_renamed.columns = [f"{c}_15m" for c in ctx_15m]
df_mtf = pd.concat([df_5m_feat, df_15m_renamed.reindex(df_5m_feat.index, method='ffill')], axis=1)

# 1H context
ctx_1h = [c for c in df_1h_feat.columns if c not in exclude]
df_1h_renamed = df_1h_feat[ctx_1h].copy()
df_1h_renamed.columns = [f"{c}_1h" for c in ctx_1h]
df_mtf = pd.concat([df_mtf, df_1h_renamed.reindex(df_mtf.index, method='ffill')], axis=1)

df_mtf.dropna(inplace=True)

features = [c for c in df_mtf.columns if c not in exclude and c != 'hurst']

print(f"✅ Features: {len(features)}")

# Focus on target window
target_start = pd.Timestamp('2026-01-08 00:30:00')
target_end = pd.Timestamp('2026-01-08 00:40:00')

df_target = df_mtf[(df_mtf.index >= target_start) & (df_mtf.index <= target_end)]

print(f"\n🎯 Target window (00:30-00:40): {len(df_target)} 5m candles")
print("=" * 70)
print("PREDICTIONS")
print("=" * 70)

signals = []

for idx, row in df_target.iterrows():
    X = row[features].values.reshape(1, -1)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    
    # Ensemble
    p1 = mtf_xgb.predict_proba(X)
    p2 = mtf_lgb.predict(X)
    p3 = mtf_cat.predict_proba(X)
    probas = (p1 + p2 + p3) / 3
    
    prob_short = float(probas[0][2])
    
    print(f"\n⏰ {idx}")
    print(f"   Price: ${row['close']:,.2f}")
    print(f"   Prob SHORT: {prob_short:.4f} (threshold: {THRESHOLD_SHORT:.4f})")
    
    if prob_short >= THRESHOLD_SHORT:
        rsi = row.get('rsi_14', 50)
        hurst = row.get('hurst', 0.5)
        
        if rsi < 30 and hurst > 0.50:
            print(f"   🛑 BLOCKED (RSI={rsi:.1f}, Hurst={hurst:.3f})")
        else:
            signals.append({
                'time': idx,
                'confidence': prob_short,
                'price': row['close']
            })
            print(f"   ✅ SIGNAL! SHORT @ {prob_short:.4f}")
    else:
        print(f"   ❌ No signal")

print("\n" + "=" * 70)
print("RESULTS")
print("=" * 70)
print(f"\nSignals found: {len(signals)}")
print(f"Expected: 6")

if len(signals) == 6:
    print("\n✅ PERFECT MATCH!")
elif len(signals) > 0:
    print(f"\n⚠️  PARTIAL MATCH: {len(signals)}/6")
    for i, sig in enumerate(signals, 1):
        print(f"{i}. {sig['time']} - SHORT @ ${sig['price']:,.2f} (Conf: {sig['confidence']:.4f})")
else:
    print("\n❌ NO MATCH")

print("=" * 70)
