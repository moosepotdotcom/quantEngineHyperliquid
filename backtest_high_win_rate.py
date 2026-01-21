#!/usr/bin/env python3
"""
HIGH WIN RATE SINGLE-TRADE BACKTEST
Optimizes Threshold and ADX Filter for 4-5 trades/day with "One Trade at a Time" constraint.
"""

import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
import json
import os
import sys
from datetime import datetime

# --- CONFIGURATION ---
DATA_FILE = 'training/data/BTC_5m_mtf_labeled.csv'
MODEL_DIR = 'models'
OUTPUT_FILE = 'HIGH_WIN_RATE_RESULTS.md'

# --- CONFIGURATION ---
DATA_FILE = 'training/data/BTC_Jan2_11_2026_Hyperliquid.csv'
MODEL_DIR = 'models'
OUTPUT_FILE = 'HIGH_WIN_RATE_RESULTS.md'

# Import Utils
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'utils')) # Fix for internal imports
from utils.feature_engineer import add_all_indicators

# Feature List (Copied from quant_engine.py to ensure 100% match)
MTF_FEATURE_LIST = ["rsi_7","rsi_14","rsi_21","stoch_k","stoch_d","williams_r","roc_5","roc_10","awesome_osc","kama","ppo","ppo_signal","ppo_hist","ema_5","ema_10","ema_20","ema_50","ema_100","ema_200","sma_10","sma_20","sma_50","macd","macd_signal","macd_hist","adx","adx_pos","adx_neg","cci","aroon_up","aroon_down","ichimoku_a","ichimoku_b","bb_high","bb_low","bb_mid","bb_width","bb_pct","atr_7","atr_14","atr_21","kc_high","kc_low","kc_mid","dc_high","dc_low","dc_mid","dc_width","obv","cmf","mfi","adi","eom","vpt","nvi","vwap","price_vs_ema20","price_vs_ema50","price_vs_bb_mid","ema_cross","trend_strength","atr_pct","volatility_regime","rsi_sma","rsi_divergence","vol_sma_20","volume_surge","body_size","upper_wick","lower_wick","is_bullish","return_1","return_3","return_5","return_10","range_pct","range_vs_atr","rsi_7_15m","rsi_14_15m","rsi_21_15m","stoch_k_15m","stoch_d_15m","williams_r_15m","roc_5_15m","roc_10_15m","awesome_osc_15m","kama_15m","ppo_15m","ppo_signal_15m","ppo_hist_15m","ema_5_15m","ema_10_15m","ema_20_15m","ema_50_15m","ema_100_15m","ema_200_15m","sma_10_15m","sma_20_15m","sma_50_15m","macd_15m","macd_signal_15m","macd_hist_15m","adx_15m","adx_pos_15m","adx_neg_15m","cci_15m","aroon_up_15m","aroon_down_15m","ichimoku_a_15m","ichimoku_b_15m","bb_high_15m","bb_low_15m","bb_mid_15m","bb_width_15m","bb_pct_15m","atr_7_15m","atr_14_15m","atr_21_15m","kc_high_15m","kc_low_15m","kc_mid_15m","dc_high_15m","dc_low_15m","dc_mid_15m","dc_width_15m","obv_15m","cmf_15m","mfi_15m","adi_15m","eom_15m","vpt_15m","nvi_15m","vwap_15m","price_vs_ema20_15m","price_vs_ema50_15m","price_vs_bb_mid_15m","ema_cross_15m","trend_strength_15m","atr_pct_15m","volatility_regime_15m","rsi_sma_15m","rsi_divergence_15m","vol_sma_20_15m","volume_surge_15m","body_size_15m","upper_wick_15m","lower_wick_15m","is_bullish_15m","return_1_15m","return_3_15m","return_5_15m","return_10_15m","range_pct_15m","range_vs_atr_15m","rsi_7_1h","rsi_14_1h","rsi_21_1h","stoch_k_1h","stoch_d_1h","williams_r_1h","roc_5_1h","roc_10_1h","awesome_osc_1h","kama_1h","ppo_1h","ppo_signal_1h","ppo_hist_1h","ema_5_1h","ema_10_1h","ema_20_1h","ema_50_1h","ema_100_1h","ema_200_1h","sma_10_1h","sma_20_1h","sma_50_1h","macd_1h","macd_signal_1h","macd_hist_1h","adx_1h","adx_pos_1h","adx_neg_1h","cci_1h","aroon_up_1h","aroon_down_1h","ichimoku_a_1h","ichimoku_b_1h","bb_high_1h","bb_low_1h","bb_mid_1h","bb_width_1h","bb_pct_1h","atr_7_1h","atr_14_1h","atr_21_1h","kc_high_1h","kc_low_1h","kc_mid_1h","dc_high_1h","dc_low_1h","dc_mid_1h","dc_width_1h","obv_1h","cmf_1h","mfi_1h","adi_1h","eom_1h","vpt_1h","nvi_1h","vwap_1h","price_vs_ema20_1h","price_vs_ema50_1h","price_vs_bb_mid_1h","ema_cross_1h","trend_strength_1h","atr_pct_1h","volatility_regime_1h","rsi_sma_1h","rsi_divergence_1h","vol_sma_20_1h","volume_surge_1h","body_size_1h","upper_wick_1h","lower_wick_1h","is_bullish_1h","return_1_1h","return_3_1h","return_5_1h","return_10_1h","range_pct_1h","range_vs_atr_1h","hurst","atr","atr_ratio","wick_ratio_upper","wick_ratio_lower","rsi","rsi_slope","price_slope"]

# Grid Search Space
THRESHOLDS = [1.0, 1.1, 1.2, 1.3, 1.5]
ADX_FILTERS = [10, 15, 20, 25]

print("\n" + "="*70)
print("🚀 HIGH WIN RATE OPTIMIZER")
print("Target: 4-5 trades/day | Constraint: Single Position")
print("="*70)

# 1. Load Data
print("\n📥 Loading data...")
if not os.path.exists(DATA_FILE):
    print(f"❌ Data file not found: {DATA_FILE}")
    sys.exit(1)

df = pd.read_csv(DATA_FILE)
df['timestamp'] = pd.to_datetime(df['timestamp'])

print(f"✅ Loaded {len(df)} candles (Jan 2-11, 2026)")

# 2. Compute Indicators
print("\n🔧 Computing indicators (this may take a moment)...")
df = add_all_indicators(df)
df['hurst'] = 0.5 # Default (Computation is expensive/complex here, assuming neutral for backtest speed)

# Mock MTF columns (15m/1h) by resampling - CRITICAL for model input
print("   Computing MTF approximations...")
df.set_index('timestamp', inplace=True)

# 15m Resample
exclude = ['open', 'high', 'low', 'close', 'volume']
cols_to_resample = [c for c in df.columns if c not in exclude]

df_15m = df.resample('15min').last() # Simplified for speed
df_15m = add_all_indicators(df_15m)
df_15m_renamed = df_15m[[c for c in df_15m.columns if c not in exclude]].add_suffix('_15m')
df = pd.merge_asof(df, df_15m_renamed, left_index=True, right_index=True)

# 1h Resample
df_1h = df.resample('1h').last()
df_1h = add_all_indicators(df_1h)
df_1h_renamed = df_1h[[c for c in df_1h.columns if c not in exclude]].add_suffix('_1h')
df = pd.merge_asof(df, df_1h_renamed, left_index=True, right_index=True)

df.dropna(inplace=True)
print(f"✅ Feature Engineering Complete. Valid Rows: {len(df)}")
df.reset_index(inplace=True)

# 3. Load Models (MTF Scalper Trio)
print("\n📦 Loading MTF Trio models...")
try:
    prefix = os.path.join(MODEL_DIR, 'mtf_scalper_5m_trio_')
    
    xgb_model = xgb.XGBClassifier()
    xgb_model.load_model(f'{prefix}xgb.json')
    
    lgb_model = lgb.Booster(model_file=f'{prefix}lgb.json')
    
    cat_model = CatBoostClassifier()
    cat_model.load_model(f'{prefix}cat.json')
    
    feature_names = MTF_FEATURE_LIST
    
    print(f"✅ Models loaded")
except Exception as e:
    print(f"❌ Failed to load models: {e}")
    sys.exit(1)

# 4. Prepare Features
print("\n🔧 Aligning features...")
# Ensure all features exist
for f in feature_names:
    if f not in df.columns:
        df[f] = 0.0

X = df[feature_names].values
X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

# 5. Generate Predictions
print("\n🤖 Generating base predictions...")
p1 = xgb_model.predict_proba(X)
p2 = lgb_model.predict(X, num_iteration=lgb_model.best_iteration)
p3 = cat_model.predict_proba(X)

ensemble_proba = (p1 + p2 + p3) / 3.0
prob_long = ensemble_proba[:, 1]
prob_short = ensemble_proba[:, 2]
max_probs = np.max(ensemble_proba, axis=1)
predictions = np.argmax(ensemble_proba, axis=1) # 0=Neutral, 1=Long, 2=Short

# Pre-calculate ADX array for speed
if 'adx' in df.columns:
    adx_values = df['adx'].values
else:
    print("⚠️  'adx' column missing! Using dummy ADX=30")
    adx_values = np.full(len(df), 30)

# 5. Run Grid Search
print("\n🔄 Running Grid Search (Constraint: Single Position)...")
print(f"{'Thresh':<8} {'ADX':<5} {'Signals':<8} {'Trades':<8} {'/Day':<6} {'Win%':<6} {'Hold(h)':<8} {'P&L ($)':<10}")
print("-" * 80)

best_result = None
results = []

for thresh in THRESHOLDS:
    for adx_lim in ADX_FILTERS:
        
        # Simulation State
        position = None 
        trades = []
        potential_signals = 0
        
        # Scan through candles
        for i in range(len(df)):
            current_adx = adx_values[i]
            current_prob = max_probs[i]
            pred_class = predictions[i]
            
            # Count Potential (ignoring position)
            if current_prob >= thresh and current_adx >= adx_lim and pred_class != 0:
                potential_signals += 1
            
            row = df.iloc[i]
            h, l, c, ts = row['high'], row['low'], row['close'], row['timestamp']
            
            # --- Manage Existing Position ---
            if position:
                outcome = None
                hold_time = (ts - position['time']).total_seconds() / 3600
                
                if position['type'] == 'LONG':
                    if h >= position['tp']: outcome = 'WIN'
                    elif l <= position['sl']: outcome = 'LOSS'
                else: # SHORT
                    if l <= position['tp']: outcome = 'WIN'
                    elif h >= position['sl']: outcome = 'LOSS'
                
                if outcome:
                    trades.append({'outcome': outcome, 'hold': hold_time})
                    position = None
                
                continue # Skip new signals if position is open
            
            # --- Check New Signal (Relative Strength Mode) ---
            # Ignore Neutral. If Long > Short * Ratio (or vice versa) -> Trade
            ratio = thresh # Reuse 'thresh' variable as ratio (e.g. 1.1, 1.2, 1.3)
            
            p_long = prob_long[i]
            p_short = prob_short[i]
            
            if current_adx < adx_lim: continue
            
            # Minimum confidence floor (e.g. 0.20) to avoid total noise
            if max(p_long, p_short) < 0.20: continue
            
            if p_long > p_short * ratio:
                tp = c * 1.015
                sl = c * 0.992
                position = {'type': 'LONG', 'entry': c, 'tp': tp, 'sl': sl, 'time': ts}
            elif p_short > p_long * ratio:
                tp = c * 0.985
                sl = c * 1.008
                position = {'type': 'SHORT', 'entry': c, 'tp': tp, 'sl': sl, 'time': ts}

        # Calculate Metrics
        matches = len(trades)
        wins = len([t for t in trades if t['outcome'] == 'WIN'])
        win_rate = (wins / matches * 100) if matches > 0 else 0
        trades_per_day = matches / 10.0
        avg_hold = sum([t['hold'] for t in trades]) / matches if matches > 0 else 0
        
        # PnL (Simplified: $53 * 27x * 1.5% win / 0.8% loss)
        # Win: $21.46, Loss: $11.45
        pnl = (wins * 21.46) - ((matches - wins) * 11.45)
        
        # Rating logic: Closer to 5 trades/day is better, provided WR is high
        rating = "---"
        if 3 <= trades_per_day <= 6 and win_rate > 70:
            rating = "⭐⭐⭐"
            if win_rate > 80: rating = "⭐⭐⭐⭐⭐"
            if win_rate > 90: rating = "🔥🔥🔥🔥🔥"
            
        print(f"{thresh:<8.2f} {adx_lim:<5} {matches:<8} {trades_per_day:<6.1f} {win_rate:<6.1f} {pnl:<10.2f} {rating}")
        
        results.append({
            'threshold': thresh,
            'adx': adx_lim,
            'trades': matches,
            'per_day': trades_per_day,
            'win_rate': win_rate,
            'pnl': pnl
        })

print("-" * 65)

# Find Best
valid_results = [r for r in results if 3.5 <= r['per_day'] <= 6.5]
if valid_results:
    best = max(valid_results, key=lambda x: x['win_rate'])
    print(f"\n🏆 BEST CONFIGURATION:")
    print(f"   Threshold: {best['threshold']}")
    print(f"   ADX Filter: {best['adx']}")
    print(f"   Trades/Day: {best['per_day']}")
    print(f"   Win Rate: {best['win_rate']:.1f}%")
    print(f"   Est. PnL: ${best['pnl']:.2f}")
else:
    print("\n⚠️  No configuration matched ideal frequency (3.5-6.5 trades/day).")
    print("   Check the table for the closest match.")
