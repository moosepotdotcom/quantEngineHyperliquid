#!/usr/bin/env python3
"""
FULL MTF FEATURE ENGINEERING PIPELINE - SCALED VERSION
Generate all 231 features for HYBRID V1 model with SCALED VOLUME
For Jan 2-14, 2026 data
"""

import pandas as pd
import numpy as np
import ta
import sys
import os

print("="*70)
print("🔧 FULL MTF FEATURE ENGINEERING PIPELINE (SCALED)")
print("="*70)

# Load Jan 2-14, 2026 SCALED data
print("\n📥 Loading Jan 2-14, 2026 SCALED data...")
# Check if scaled file exists
scaled_file = 'force_reload_to_scale_price.csv' # Force reload
if os.path.exists(scaled_file):
    df_jan = pd.read_csv(scaled_file)
    print(f"✅ Loaded scaled file: {scaled_file}")
else:
    print("⚠️ Scaled file not found, loading enriched and scaling...")
    df = pd.read_csv('training/data/BTC_5m_2025_enriched.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df_jan = df[
        (df['timestamp'] >= '2026-01-02') &
        (df['timestamp'] <= '2026-01-14 23:59:59')
    ].copy().reset_index(drop=True)
    
    # Volume scaling (KEEP THIS)
    VOLUME_SCALE_FACTOR = 263.36 / 50.88
    df_jan['volume'] = df_jan['volume'] * VOLUME_SCALE_FACTOR
    df_jan['taker_buy_base'] = df_jan['taker_buy_base'] * VOLUME_SCALE_FACTOR
    
    # SCALE PRICE (DISABLED - Model has seen 126k prices)
    # Training mean price: ~56,109
    # Jan 2026 mean price: ~91,683
    # PRICE_SCALE_FACTOR = 56109.0 / 91683.0
    # print(f"⚖️ Scaling PRICE by {PRICE_SCALE_FACTOR:.4f} to match training distribution...")
    # for col in ['open', 'high', 'low', 'close']:
    #     df_jan[col] = df_jan[col] * PRICE_SCALE_FACTOR

df_jan['timestamp'] = pd.to_datetime(df_jan['timestamp'])
print(f"✅ Loaded {len(df_jan)} candles")
print(f"   Period: {df_jan['timestamp'].min()} to {df_jan['timestamp'].max()}")
print(f"   Volume Mean: {df_jan['volume'].mean():.2f}")
print(f"   Price Mean:  {df_jan['close'].mean():.2f}")

# Need more historical data for indicators
print("\n📊 Loading historical context (500 candles before Jan 2)...")
# We need to load original data again for context, but we must be careful.
# The context data (Dec 2025) has high volume (~263). The new data (Jan 2026) has low volume (~50).
# If we append specific context, we need to ensure the transition is smooth if we want perfect indicators.
# However, `df_jan` is already scaled to ~263 mean. So we can append context from Dec 2025 (which is natively ~263) directly.
df_orig = pd.read_csv('training/data/BTC_5m_2025_enriched.csv')
df_orig['timestamp'] = pd.to_datetime(df_orig['timestamp'])
df_context = df_orig[df_orig['timestamp'] < '2026-01-02'].tail(500).copy()

# Combine context (Dec) + scaled data (Jan)
df_full = pd.concat([df_context, df_jan]).reset_index(drop=True)

print(f"✅ Combined data: {len(df_full)} candles (500 context + {len(df_jan)} test)")
print(f"   Volume Check (Context): {df_context['volume'].mean():.2f}")
print(f"   Volume Check (Test):    {df_jan['volume'].mean():.2f}")

# --- IMPORTED LOGIC FROM utils/feature_engineer.py ---

def add_all_indicators(df):
    """
    Add comprehensive list of technical indicators including advanced regime features.
    Exact copy of logic from utils/feature_engineer.py to ensure model compatibility.
    """
    df = df.copy()
    
    # Helper function to safely calculate indicators
    def safe_indicator(func, default=0):
        try:
            # Ensure the result is a Series of the same length as df
            result = func()
            if isinstance(result, pd.Series) and len(result) == len(df):
                return result
            # If it's a single value or different length, broadcast it
            return pd.Series(result, index=df.index) if not isinstance(result, pd.Series) else result
        except (ValueError, IndexError, Exception) as e:
            # print(f"      ⚠️  Indicator failed: {e}", flush=True)
            return pd.Series(default, index=df.index)
    
    # ===== MOMENTUM =====
    df['rsi_7'] = safe_indicator(lambda: ta.momentum.rsi(df['close'], window=7))
    df['rsi_14'] = safe_indicator(lambda: ta.momentum.rsi(df['close'], window=14))
    df['rsi_21'] = safe_indicator(lambda: ta.momentum.rsi(df['close'], window=21))
    df['stoch_k'] = safe_indicator(lambda: ta.momentum.stoch(df['high'], df['low'], df['close'], window=14))
    df['stoch_d'] = safe_indicator(lambda: ta.momentum.stoch_signal(df['high'], df['low'], df['close'], window=14))
    df['williams_r'] = safe_indicator(lambda: ta.momentum.williams_r(df['high'], df['low'], df['close']))
    df['roc_5'] = safe_indicator(lambda: ta.momentum.roc(df['close'], window=5))
    df['roc_10'] = safe_indicator(lambda: ta.momentum.roc(df['close'], window=10))
    df['awesome_osc'] = safe_indicator(lambda: ta.momentum.awesome_oscillator(df['high'], df['low']))
    df['kama'] = safe_indicator(lambda: ta.momentum.kama(df['close']))
    df['ppo'] = safe_indicator(lambda: ta.momentum.ppo(df['close']))
    df['ppo_signal'] = safe_indicator(lambda: ta.momentum.ppo_signal(df['close']))
    df['ppo_hist'] = safe_indicator(lambda: ta.momentum.ppo_hist(df['close']))
    
    # ===== TREND =====
    df['ema_5'] = safe_indicator(lambda: ta.trend.ema_indicator(df['close'], window=5))
    df['ema_10'] = safe_indicator(lambda: ta.trend.ema_indicator(df['close'], window=10))
    df['ema_20'] = safe_indicator(lambda: ta.trend.ema_indicator(df['close'], window=20))
    df['ema_50'] = safe_indicator(lambda: ta.trend.ema_indicator(df['close'], window=50))
    df['ema_100'] = safe_indicator(lambda: ta.trend.ema_indicator(df['close'], window=100))
    df['ema_200'] = safe_indicator(lambda: ta.trend.ema_indicator(df['close'], window=200))
    df['sma_10'] = safe_indicator(lambda: ta.trend.sma_indicator(df['close'], window=10))
    df['sma_20'] = safe_indicator(lambda: ta.trend.sma_indicator(df['close'], window=20))
    df['sma_50'] = safe_indicator(lambda: ta.trend.sma_indicator(df['close'], window=50))
    
    # MACD
    try:
        macd = ta.trend.MACD(df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_hist'] = macd.macd_diff()
    except:
        df['macd'] = 0
        df['macd_signal'] = 0
        df['macd_hist'] = 0
    
    # ADX
    df['adx'] = safe_indicator(lambda: ta.trend.adx(df['high'], df['low'], df['close']), 25.0)
    df['adx_pos'] = safe_indicator(lambda: ta.trend.adx_pos(df['high'], df['low'], df['close']), 25.0)
    df['adx_neg'] = safe_indicator(lambda: ta.trend.adx_neg(df['high'], df['low'], df['close']), 25.0)
    
    df['cci'] = safe_indicator(lambda: ta.trend.cci(df['high'], df['low'], df['close']))
    df['aroon_up'] = safe_indicator(lambda: ta.trend.aroon_up(df['high'], df['low']))
    df['aroon_down'] = safe_indicator(lambda: ta.trend.aroon_down(df['high'], df['low']))
    df['ichimoku_a'] = safe_indicator(lambda: ta.trend.ichimoku_a(df['high'], df['low']))
    df['ichimoku_b'] = safe_indicator(lambda: ta.trend.ichimoku_b(df['high'], df['low']))
    
    # ===== VOLATILITY =====
    try:
        bb = ta.volatility.BollingerBands(df['close'])
        df['bb_high'] = bb.bollinger_hband()
        df['bb_low'] = bb.bollinger_lband()
        df['bb_mid'] = bb.bollinger_mavg()
        df['bb_width'] = bb.bollinger_wband()
        df['bb_pct'] = bb.bollinger_pband()
    except:
        df['bb_high'] = df['close']
        df['bb_low'] = df['close']
        df['bb_mid'] = df['close']
        df['bb_width'] = 0
        df['bb_pct'] = 0.5
    
    df['atr_7'] = safe_indicator(lambda: ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=7))
    df['atr_14'] = safe_indicator(lambda: ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14))
    df['atr_21'] = safe_indicator(lambda: ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=21))
    
    try:
        kc = ta.volatility.KeltnerChannel(df['high'], df['low'], df['close'])
        df['kc_high'] = kc.keltner_channel_hband()
        df['kc_low'] = kc.keltner_channel_lband()
        df['kc_mid'] = kc.keltner_channel_mband()
    except:
        df['kc_high'] = df['close']
        df['kc_low'] = df['close']
        df['kc_mid'] = df['close']
    
    try:
        dc = ta.volatility.DonchianChannel(df['high'], df['low'], df['close'])
        df['dc_high'] = dc.donchian_channel_hband()
        df['dc_low'] = dc.donchian_channel_lband()
        df['dc_mid'] = dc.donchian_channel_mband()
        df['dc_width'] = dc.donchian_channel_wband()
    except:
        df['dc_high'] = df['close']
        df['dc_low'] = df['close']
        df['dc_mid'] = df['close']
        df['dc_width'] = 0
    
    # ===== VOLUME =====
    df['obv'] = safe_indicator(lambda: ta.volume.on_balance_volume(df['close'], df['volume']))
    df['cmf'] = safe_indicator(lambda: ta.volume.chaikin_money_flow(df['high'], df['low'], df['close'], df['volume']))
    df['mfi'] = safe_indicator(lambda: ta.volume.money_flow_index(df['high'], df['low'], df['close'], df['volume']))
    df['adi'] = safe_indicator(lambda: ta.volume.acc_dist_index(df['high'], df['low'], df['close'], df['volume']))
    df['eom'] = safe_indicator(lambda: ta.volume.ease_of_movement(df['high'], df['low'], df['volume']))
    df['vpt'] = safe_indicator(lambda: ta.volume.volume_price_trend(df['close'], df['volume']))
    df['nvi'] = safe_indicator(lambda: ta.volume.negative_volume_index(df['close'], df['volume']))
    df['vwap'] = safe_indicator(lambda: ta.volume.volume_weighted_average_price(df['high'], df['low'], df['close'], df['volume']))
    
    # ===== CUSTOM FEATURES (EXACT MATCH) =====
    # Price Position
    df['price_vs_ema20'] = (df['close'] - df['ema_20']) / df['ema_20']
    df['price_vs_ema50'] = (df['close'] - df['ema_50']) / df['ema_50']
    df['price_vs_bb_mid'] = (df['close'] - df['bb_mid']) / df['bb_mid']
    
    # Trend Direction
    df['ema_cross'] = (df['ema_10'] > df['ema_20']).astype(int)
    
    # FIX 1: Trend Strength uses ADX sign logic, not EMA ratio
    df['trend_strength'] = df['adx'] * (df['adx_pos'] - df['adx_neg']).apply(np.sign)
    
    # Volatility Regime
    df['atr_pct'] = df['atr_14'] / df['close']
    df['volatility_regime'] = (df['atr_pct'] > df['atr_pct'].rolling(50).mean()).astype(int)
    
    # Momentum Divergence
    df['rsi_sma'] = df['rsi_14'].rolling(5).mean()
    df['rsi_divergence'] = df['rsi_14'] - df['rsi_sma']
    
    # FIX 2: Volume Surge is a ratio, not boolean
    df['vol_sma_20'] = df['volume'].rolling(20).mean()
    df['volume_surge'] = df['volume'] / (df['vol_sma_20'] + 1e-9)
    
    # FIX 3: Normalized Candle features
    df['body_size'] = abs(df['close'] - df['open']) / (df['atr_14'] + 1e-9)
    df['upper_wick'] = (df['high'] - df[['open', 'close']].max(axis=1)) / (df['atr_14'] + 1e-9)
    df['lower_wick'] = (df[['open', 'close']].min(axis=1) - df['low']) / (df['atr_14'] + 1e-9)
    df['is_bullish'] = (df['close'] > df['open']).astype(int)
    
    # Returns
    df['return_1'] = df['close'].pct_change(1)
    df['return_3'] = df['close'].pct_change(3)
    df['return_5'] = df['close'].pct_change(5)
    df['return_10'] = df['close'].pct_change(10)
    
    # Range
    df['range_pct'] = (df['high'] - df['low']) / df['close']
    df['range_vs_atr'] = (df['high'] - df['low']) / (df['atr_14'] + 1e-9)
    
    df = df.fillna(0)
    return df

print("\n🔧 Generating 5m features (Exact Match)...")
df_full = add_all_indicators(df_full)

print(f"✅ 5m features: {len([c for c in df_full.columns if not c.endswith('_15m') and not c.endswith('_1h')])} columns")

# Resample to 15m
print("\n🔧 Resampling to 15m...")
df_full_indexed = df_full.set_index('timestamp')
df_15m = df_full_indexed.resample('15min').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum',
    'taker_buy_base': 'sum'
}).dropna().reset_index()

print("🔧 Generating 15m features (Exact Match)...")
df_15m = add_all_indicators(df_15m)

# Rename to _15m
suffix_cols = {c: f"{c}_15m" for c in df_15m.columns if c not in ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'taker_buy_base']}
df_15m = df_15m.rename(columns=suffix_cols)
print(f"✅ 15m features generated")

# Resample to 1h
print("\n🔧 Resampling to 1h...")
df_1h = df_full_indexed.resample('1h').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum',
    'taker_buy_base': 'sum'
}).dropna().reset_index()

print("🔧 Generating 1h features (Exact Match)...")
df_1h = add_all_indicators(df_1h)

# Rename to _1h
suffix_cols = {c: f"{c}_1h" for c in df_1h.columns if c not in ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'taker_buy_base']}
df_1h = df_1h.rename(columns=suffix_cols)
print(f"✅ 1h features generated")

# Merge
print("\n🔗 Merging all timeframes...")
df_final = df_full.copy()
df_final['timestamp'] = pd.to_datetime(df_final['timestamp'])
df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])
df_1h['timestamp'] = pd.to_datetime(df_1h['timestamp'])

# Merge 15m (use asof or merge on time)
# Note: 15m data should be merged such that 5m candles get the valid 15m data available at that time
# Forward fill is appropriate
df_final = df_final.set_index('timestamp')
df_15m = df_15m.set_index('timestamp')
df_1h = df_1h.set_index('timestamp')

# Join features (exclude core candles from 15m/1h)
feat_cols_15m = [c for c in df_15m.columns if c.endswith('_15m')]
feat_cols_1h = [c for c in df_1h.columns if c.endswith('_1h')]

# Using merge_asof logic via reindex/ffill
df_final = df_final.join(df_15m[feat_cols_15m], how='left')
df_final = df_final.join(df_1h[feat_cols_1h], how='left')

df_final = df_final.fillna(method='ffill').fillna(0).reset_index()

# Filter context out (Jan only)
df_final = df_final[
    (df_final['timestamp'] >= '2026-01-02') &
    (df_final['timestamp'] <= '2026-01-14 23:59:59')
].copy()

print(f"✅ Final dataset: {len(df_final)} candles, {len(df_final.columns)} columns")

# Save
output_file = 'training/data/BTC_5m_jan2_14_2026_mtf_full.csv'
df_final.to_csv(output_file, index=False)

print(f"\n💾 Saved to {output_file}")

print("\n" + "="*70)
print("✅ FEATURE ENGINEERING COMPLETE!")
print("="*70)
print(f"\nReady for HYBRID V1 backtest with {len(df_final.columns)} features!")
