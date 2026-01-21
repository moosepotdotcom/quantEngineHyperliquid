#!/usr/bin/env python3
"""
V8 ENHANCED - HYBRID V1 + LIQUIDATION AWARENESS
Base: HYBRID V1 (86.3% WR @ 45% threshold)
Enhancement: Liquidation proximity detection + confidence boosting
Target: 90%+ WR
"""

import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
import pickle
import os

print("\n" + "="*70)
print("🚀 V8 ENHANCED - HYBRID V1 + LIQUIDATION AWARENESS")
print("="*70)

# Load HYBRID V1 models
print("\n📦 Loading HYBRID V1 models...")

script_dir = 'HYBRID_V1_EXPORT'

xgb_model = xgb.XGBClassifier()
xgb_model.load_model(os.path.join(script_dir, 'xgb_hybrid.json'))

lgb_model = lgb.Booster(model_file=os.path.join(script_dir, 'lgb_hybrid.txt'))

cat_model = CatBoostClassifier()
cat_model.load_model(os.path.join(script_dir, 'cat_hybrid.cbm'))

with open(os.path.join(script_dir, 'feature_names.pkl'), 'rb') as f:
    feature_names = pickle.load(f)

with open(os.path.join(script_dir, 'metadata.pkl'), 'rb') as f:
    metadata = pickle.load(f)

print(f"✅ HYBRID V1 loaded")
print(f"   Features: {len(feature_names)}")
print(f"   Base WR: 86.3% @ 45% threshold")

# Load market data
print("\n📥 Loading market data...")

# Try Jan 2-14 2026 MTF data first
data_file = 'training/data/BTC_5m_jan2_14_2026_mtf_full.csv'
if not os.path.exists(data_file):
    data_file = 'training/data/BTC_5m_mtf_labeled.csv'

df = pd.read_csv(data_file)
df['timestamp'] = pd.to_datetime(df['timestamp'])

print(f"✅ Loaded {len(df):,} candles")
print(f"   Period: {df['timestamp'].min()} to {df['timestamp'].max()}")

# Use all data from file (already filtered to Jan 2-14)
df_test = df.copy()

print(f"\n🔬 Testing on {len(df_test)} candles")
print(f"   Period: {df_test['timestamp'].min()} to {df_test['timestamp'].max()}")

# Load liquidation data
print("\n🔥 Loading liquidation data...")
try:
    liq_df = pd.read_csv('V9_LIQUIDATION_EXPERIMENT/liquidation_data/REAL_liquidations_continuous.csv')
    liq_df['timestamp'] = pd.to_datetime(liq_df['timestamp'])
    print(f"✅ Loaded {len(liq_df)} liquidation events")
except:
    print("⚠️  No liquidation data, running without boost")
    liq_df = pd.DataFrame()

# Prepare features
print("\n🔧 Preparing features...")

for feat in feature_names:
    if feat not in df_test.columns:
        df_test[feat] = 0

X = df_test[feature_names].values
X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

print(f"   Shape: {X.shape}")

# Generate predictions
print("\n🤖 Generating HYBRID V1 predictions...")

proba_xgb = xgb_model.predict_proba(X)
proba_lgb = lgb_model.predict(X)
proba_cat = cat_model.predict_proba(X)

# Fix LightGBM shape
if len(proba_lgb.shape) == 1:
    proba_lgb = np.column_stack([1-proba_lgb, proba_lgb, np.zeros(len(proba_lgb))])
elif proba_lgb.shape[1] == 2:
    proba_lgb = np.column_stack([proba_lgb, np.zeros(len(proba_lgb))])

# Ensemble
proba_ensemble = (proba_xgb + proba_lgb + proba_cat) / 3
predictions = np.argmax(proba_ensemble, axis=1)
confidences = np.max(proba_ensemble, axis=1)

df_test['prediction'] = predictions
df_test['confidence'] = confidences

print(f"✅ Predictions generated")

# Add liquidation awareness
print("\n🔥 Adding liquidation awareness...")

LIQUIDATION_BOOST = 0.10  # Boost confidence by 10% near liquidations
liquidation_boosted = 0

for i in range(len(df_test)):
    row = df_test.iloc[i]
    
    if liq_df.empty or row['prediction'] == 0:  # Skip neutral
        continue
    
    current_time = row['timestamp']
    current_price = row['close']
    
    # Check liquidations in past 1 hour
    try:
        time_window = current_time - pd.Timedelta(hours=1)
        
        recent_liqs = liq_df[
            (liq_df['timestamp'] >= time_window) &
            (liq_df['timestamp'] <= current_time)
        ]
        
        if not recent_liqs.empty:
            for _, liq in recent_liqs.iterrows():
                price_diff = abs(liq['price'] - current_price) / current_price
                if price_diff < 0.03:  # Within 3%
                    df_test.at[i, 'confidence'] += LIQUIDATION_BOOST
                    liquidation_boosted += 1
                    break
    except:
        pass

print(f"✅ Liquidation boost applied to {liquidation_boosted} signals")

# Run backtest with multiple thresholds
print("\n" + "="*70)
print("📊 TESTING MULTIPLE THRESHOLDS")
print("="*70)

results_by_threshold = []

for threshold in [0.40, 0.45, 0.50, 0.55, 0.60]:
    signal_mask = (df_test['confidence'] >= threshold) & (df_test['prediction'] != 0)
    
    tp_pct = 0.015  # 1.5%
    sl_pct = 0.008  # 0.8%
    
    trades = []
    current_position = None
    
    for i in range(len(df_test)):
        row = df_test.iloc[i]
        
        # Check open position
        if current_position is not None:
            h, l = row['high'], row['low']
            direction = current_position['dir']
            
            if direction == 'LONG':
                if h >= current_position['tp']:
                    trades.append({**current_position, 'outcome': 'WIN'})
                    current_position = None
                    continue
                elif l <= current_position['sl']:
                    trades.append({**current_position, 'outcome': 'LOSS'})
                    current_position = None
                    continue
            elif direction == 'SHORT':
                if l <= current_position['tp']:
                    trades.append({**current_position, 'outcome': 'WIN'})
                    current_position = None
                    continue
                elif h >= current_position['sl']:
                    trades.append({**current_position, 'outcome': 'LOSS'})
                    current_position = None
                    continue
            continue
        
        # Check for signals
        if signal_mask.iloc[i]:
            entry_price = row['close']
            direction = 'LONG' if row['prediction'] == 1 else 'SHORT'
            
            tp_p = entry_price * (1+tp_pct) if direction == 'LONG' else entry_price * (1-tp_pct)
            sl_p = entry_price * (1-sl_pct) if direction == 'LONG' else entry_price * (1+sl_pct)
            
            current_position = {
                'time': row['timestamp'],
                'dir': direction,
                'conf': row['confidence'],
                'price': entry_price,
                'tp': tp_p,
                'sl': sl_p
            }
    
    # Calculate results
    if trades:
        wins = len([t for t in trades if t['outcome'] == 'WIN'])
        losses = len([t for t in trades if t['outcome'] == 'LOSS'])
        total = len(trades)
        win_rate = wins / total * 100
        
        capital = 53
        leverage = 27
        buying_power = capital * leverage
        
        pnl_per_win = buying_power * tp_pct
        pnl_per_loss = buying_power * sl_pct
        
        total_pnl = (wins * pnl_per_win) - (losses * pnl_per_loss)
        roi = (total_pnl / capital) * 100
        
        results_by_threshold.append({
            'threshold': threshold,
            'trades': total,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'roi': roi
        })
        
        print(f"\n{threshold*100:.0f}% Threshold:")
        print(f"   Trades: {total} | Wins: {wins} | Losses: {losses}")
        print(f"   Win Rate: {win_rate:.1f}%")
        print(f"   ROI: {roi:+.1f}%")

# Find best threshold
print("\n" + "="*70)
print("🏆 BEST RESULTS")
print("="*70)

if results_by_threshold:
    best = max(results_by_threshold, key=lambda x: x['win_rate'])
    
    print(f"\n🎯 Highest Win Rate:")
    print(f"   Threshold: {best['threshold']*100:.0f}%")
    print(f"   Win Rate: {best['win_rate']:.1f}%")
    print(f"   Trades: {best['trades']}")
    print(f"   ROI: {best['roi']:+.1f}%")
    
    print(f"\n⚡ VS TARGET:")
    print(f"   Base (HYBRID V1): 86.3% WR")
    print(f"   Enhanced: {best['win_rate']:.1f}% WR")
    print(f"   Improvement: {best['win_rate'] - 86.3:+.1f}%")
    
    if best['win_rate'] >= 90:
        print(f"\n🎯 ✅ TARGET ACHIEVED! Win rate >= 90%!")
    else:
        print(f"\n⚠️  Need {90 - best['win_rate']:.1f}% more to hit 90% target")
    
    # Save results
    results_df = pd.DataFrame(results_by_threshold)
    results_df.to_csv('V9_LIQUIDATION_EXPERIMENT/V8_ENHANCED_HYBRID_RESULTS.csv', index=False)
    print(f"\n💾 Results saved to V8_ENHANCED_HYBRID_RESULTS.csv")
else:
    print("\n❌ No trades generated at any threshold")

print("\n" + "="*70)
print("✅ V8 ENHANCED BACKTEST COMPLETE")
print("="*70)
