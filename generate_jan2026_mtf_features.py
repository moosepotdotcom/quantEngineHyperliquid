#!/usr/bin/env python3
"""
FULL MTF FEATURE ENGINEERING PIPELINE
Generate all 231 features for HYBRID V1 model
For Jan 2-14, 2026 data
"""

import pandas as pd
import numpy as np
import ta
from datetime import datetime

print("="*70)
print("🔧 FULL MTF FEATURE ENGINEERING PIPELINE")
print("="*70)

# Load Jan 2-14, 2026 raw data
print("\n📥 Loading Jan 2-14, 2026 data...")
df = pd.read_csv('training/data/BTC_5m_2025_enriched.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Filter to Jan 2-14
df_jan = df[
    (df['timestamp'] >= '2026-01-02') &
    (df['timestamp'] <= '2026-01-14 23:59:59')
].copy().reset_index(drop=True)

print(f"✅ Loaded {len(df_jan)} candles")
print(f"   Period: {df_jan['timestamp'].min()} to {df_jan['timestamp'].max()}")

# Need more historical data for indicators
print("\n📊 Loading historical context (500 candles before Jan 2)...")
df_full = df[df['timestamp'] <= '2026-01-14 23:59:59'].tail(len(df_jan) + 500).copy().reset_index(drop=True)
print(f"✅ Loaded {len(df_full)} candles with context")

def safe_indicator(func, *args, **kwargs):
    """Safely calculate indicator, return 0 on error"""
    try:
        result = func(*args, **kwargs)
        return result.fillna(0)
    except:
        return pd.Series([0] * len(args[0]), index=args[0].index)

print("\n🔧 Generating 5m features...")

# RSI variants
df_full['rsi_7'] = safe_indicator(ta.momentum.rsi, df_full['close'], window=7)
df_full['rsi_14'] = safe_indicator(ta.momentum.rsi, df_full['close'], window=14)
df_full['rsi_21'] = safe_indicator(ta.momentum.rsi, df_full['close'], window=21)

# Stochastic
stoch = ta.momentum.StochasticOscillator(df_full['high'], df_full['low'], df_full['close'])
df_full['stoch_k'] = safe_indicator(lambda: stoch.stoch())
df_full['stoch_d'] = safe_indicator(lambda: stoch.stoch_signal())

# Williams %R
df_full['williams_r'] = safe_indicator(ta.momentum.williams_r, df_full['high'], df_full['low'], df_full['close'])

# ROC
df_full['roc_5'] = safe_indicator(ta.momentum.roc, df_full['close'], window=5)
df_full['roc_10'] = safe_indicator(ta.momentum.roc, df_full['close'], window=10)

# Awesome Oscillator
df_full['awesome_osc'] = safe_indicator(ta.momentum.awesome_oscillator, df_full['high'], df_full['low'])

# KAMA
df_full['kama'] = safe_indicator(ta.momentum.kama, df_full['close'])

# PPO
ppo = ta.momentum.PercentagePriceOscillator(df_full['close'])
df_full['ppo'] = safe_indicator(lambda: ppo.ppo())
df_full['ppo_signal'] = safe_indicator(lambda: ppo.ppo_signal())
df_full['ppo_hist'] = safe_indicator(lambda: ppo.ppo_hist())

# EMAs
for period in [5, 10, 20, 50, 100, 200]:
    df_full[f'ema_{period}'] = safe_indicator(ta.trend.ema_indicator, df_full['close'], window=period)

# SMAs
for period in [10, 20, 50]:
    df_full[f'sma_{period}'] = safe_indicator(ta.trend.sma_indicator, df_full['close'], window=period)

# MACD
macd = ta.trend.MACD(df_full['close'])
df_full['macd'] = safe_indicator(lambda: macd.macd())
df_full['macd_signal'] = safe_indicator(lambda: macd.macd_signal())
df_full['macd_hist'] = safe_indicator(lambda: macd.macd_diff())

# ADX
adx = ta.trend.ADXIndicator(df_full['high'], df_full['low'], df_full['close'])
df_full['adx'] = safe_indicator(lambda: adx.adx())
df_full['adx_pos'] = safe_indicator(lambda: adx.adx_pos())
df_full['adx_neg'] = safe_indicator(lambda: adx.adx_neg())

# CCI
df_full['cci'] = safe_indicator(ta.trend.cci, df_full['high'], df_full['low'], df_full['close'])

# Aroon
aroon = ta.trend.AroonIndicator(df_full['high'], df_full['low'])
df_full['aroon_up'] = safe_indicator(lambda: aroon.aroon_up())
df_full['aroon_down'] = safe_indicator(lambda: aroon.aroon_down())

# Ichimoku
ichimoku = ta.trend.IchimokuIndicator(df_full['high'], df_full['low'])
df_full['ichimoku_a'] = safe_indicator(lambda: ichimoku.ichimoku_a())
df_full['ichimoku_b'] = safe_indicator(lambda: ichimoku.ichimoku_b())

# Bollinger Bands
bb = ta.volatility.BollingerBands(df_full['close'])
df_full['bb_high'] = safe_indicator(lambda: bb.bollinger_hband())
df_full['bb_low'] = safe_indicator(lambda: bb.bollinger_lband())
df_full['bb_mid'] = safe_indicator(lambda: bb.bollinger_mavg())
df_full['bb_width'] = safe_indicator(lambda: bb.bollinger_wband())
df_full['bb_pct'] = safe_indicator(lambda: bb.bollinger_pband())

# ATR
for period in [7, 14, 21]:
    df_full[f'atr_{period}'] = safe_indicator(ta.volatility.average_true_range, df_full['high'], df_full['low'], df_full['close'], window=period)

# Keltner Channel
kc = ta.volatility.KeltnerChannel(df_full['high'], df_full['low'], df_full['close'])
df_full['kc_high'] = safe_indicator(lambda: kc.keltner_channel_hband())
df_full['kc_low'] = safe_indicator(lambda: kc.keltner_channel_lband())
df_full['kc_mid'] = safe_indicator(lambda: kc.keltner_channel_mband())

# Donchian Channel
dc = ta.volatility.DonchianChannel(df_full['high'], df_full['low'], df_full['close'])
df_full['dc_high'] = safe_indicator(lambda: dc.donchian_channel_hband())
df_full['dc_low'] = safe_indicator(lambda: dc.donchian_channel_lband())
df_full['dc_mid'] = safe_indicator(lambda: dc.donchian_channel_mband())
df_full['dc_width'] = safe_indicator(lambda: dc.donchian_channel_wband())

# Volume indicators
df_full['obv'] = safe_indicator(ta.volume.on_balance_volume, df_full['close'], df_full['volume'])
df_full['cmf'] = safe_indicator(ta.volume.chaikin_money_flow, df_full['high'], df_full['low'], df_full['close'], df_full['volume'])
df_full['mfi'] = safe_indicator(ta.volume.money_flow_index, df_full['high'], df_full['low'], df_full['close'], df_full['volume'])
df_full['adi'] = safe_indicator(ta.volume.acc_dist_index, df_full['high'], df_full['low'], df_full['close'], df_full['volume'])
df_full['eom'] = safe_indicator(ta.volume.ease_of_movement, df_full['high'], df_full['low'], df_full['volume'])
df_full['vpt'] = safe_indicator(ta.volume.volume_price_trend, df_full['close'], df_full['volume'])
df_full['nvi'] = safe_indicator(ta.volume.negative_volume_index, df_full['close'], df_full['volume'])

# VWAP
df_full['vwap'] = safe_indicator(ta.volume.volume_weighted_average_price, df_full['high'], df_full['low'], df_full['close'], df_full['volume'])

# Custom features
df_full['price_vs_ema20'] = (df_full['close'] - df_full['ema_20']) / df_full['ema_20']
df_full['price_vs_ema50'] = (df_full['close'] - df_full['ema_50']) / df_full['ema_50']
df_full['price_vs_bb_mid'] = (df_full['close'] - df_full['bb_mid']) / df_full['bb_mid']
df_full['ema_cross'] = (df_full['ema_5'] > df_full['ema_20']).astype(int)
df_full['trend_strength'] = abs(df_full['ema_5'] - df_full['ema_20']) / df_full['ema_20']
df_full['atr_pct'] = df_full['atr_14'] / df_full['close']
df_full['volatility_regime'] = (df_full['atr_pct'] > df_full['atr_pct'].rolling(20).mean()).astype(int)
df_full['rsi_sma'] = df_full['rsi_14'].rolling(14).mean()
df_full['rsi_divergence'] = df_full['rsi_14'] - df_full['rsi_sma']
df_full['vol_sma_20'] = df_full['volume'].rolling(20).mean()
df_full['volume_surge'] = (df_full['volume'] > df_full['vol_sma_20'] * 1.5).astype(int)

# Candle features
df_full['body_size'] = abs(df_full['close'] - df_full['open'])
df_full['upper_wick'] = df_full['high'] - df_full[['open', 'close']].max(axis=1)
df_full['lower_wick'] = df_full[['open', 'close']].min(axis=1) - df_full['low']
df_full['is_bullish'] = (df_full['close'] > df_full['open']).astype(int)

# Returns
for period in [1, 3, 5, 10]:
    df_full[f'return_{period}'] = df_full['close'].pct_change(period)

df_full['range_pct'] = (df_full['high'] - df_full['low']) / df_full['close']
df_full['range_vs_atr'] = (df_full['high'] - df_full['low']) / (df_full['atr_14'] + 1e-9)

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
}).dropna()

# Generate 15m features (same as 5m but with _15m suffix)
print("🔧 Generating 15m features...")

# RSI
df_15m['rsi_7_15m'] = safe_indicator(ta.momentum.rsi, df_15m['close'], window=7)
df_15m['rsi_14_15m'] = safe_indicator(ta.momentum.rsi, df_15m['close'], window=14)
df_15m['rsi_21_15m'] = safe_indicator(ta.momentum.rsi, df_15m['close'], window=21)

# Stochastic
stoch_15m = ta.momentum.StochasticOscillator(df_15m['high'], df_15m['low'], df_15m['close'])
df_15m['stoch_k_15m'] = safe_indicator(lambda: stoch_15m.stoch())
df_15m['stoch_d_15m'] = safe_indicator(lambda: stoch_15m.stoch_signal())

# Williams %R
df_15m['williams_r_15m'] = safe_indicator(ta.momentum.williams_r, df_15m['high'], df_15m['low'], df_15m['close'])

# ROC
df_15m['roc_5_15m'] = safe_indicator(ta.momentum.roc, df_15m['close'], window=5)
df_15m['roc_10_15m'] = safe_indicator(ta.momentum.roc, df_15m['close'], window=10)

# Awesome Oscillator
df_15m['awesome_osc_15m'] = safe_indicator(ta.momentum.awesome_oscillator, df_15m['high'], df_15m['low'])

# KAMA
df_15m['kama_15m'] = safe_indicator(ta.momentum.kama, df_15m['close'])

# PPO
ppo_15m = ta.momentum.PercentagePriceOscillator(df_15m['close'])
df_15m['ppo_15m'] = safe_indicator(lambda: ppo_15m.ppo())
df_15m['ppo_signal_15m'] = safe_indicator(lambda: ppo_15m.ppo_signal())
df_15m['ppo_hist_15m'] = safe_indicator(lambda: ppo_15m.ppo_hist())

# EMAs
for period in [5, 10, 20, 50, 100, 200]:
    df_15m[f'ema_{period}_15m'] = safe_indicator(ta.trend.ema_indicator, df_15m['close'], window=period)

# SMAs
for period in [10, 20, 50]:
    df_15m[f'sma_{period}_15m'] = safe_indicator(ta.trend.sma_indicator, df_15m['close'], window=period)

# MACD
macd_15m = ta.trend.MACD(df_15m['close'])
df_15m['macd_15m'] = safe_indicator(lambda: macd_15m.macd())
df_15m['macd_signal_15m'] = safe_indicator(lambda: macd_15m.macd_signal())
df_15m['macd_hist_15m'] = safe_indicator(lambda: macd_15m.macd_diff())

# ADX
adx_15m = ta.trend.ADXIndicator(df_15m['high'], df_15m['low'], df_15m['close'])
df_15m['adx_15m'] = safe_indicator(lambda: adx_15m.adx())
df_15m['adx_pos_15m'] = safe_indicator(lambda: adx_15m.adx_pos())
df_15m['adx_neg_15m'] = safe_indicator(lambda: adx_15m.adx_neg())

# CCI
df_15m['cci_15m'] = safe_indicator(ta.trend.cci, df_15m['high'], df_15m['low'], df_15m['close'])

# Aroon
aroon_15m = ta.trend.AroonIndicator(df_15m['high'], df_15m['low'])
df_15m['aroon_up_15m'] = safe_indicator(lambda: aroon_15m.aroon_up())
df_15m['aroon_down_15m'] = safe_indicator(lambda: aroon_15m.aroon_down())

# Ichimoku
ichimoku_15m = ta.trend.IchimokuIndicator(df_15m['high'], df_15m['low'])
df_15m['ichimoku_a_15m'] = safe_indicator(lambda: ichimoku_15m.ichimoku_a())
df_15m['ichimoku_b_15m'] = safe_indicator(lambda: ichimoku_15m.ichimoku_b())

# Bollinger Bands
bb_15m = ta.volatility.BollingerBands(df_15m['close'])
df_15m['bb_high_15m'] = safe_indicator(lambda: bb_15m.bollinger_hband())
df_15m['bb_low_15m'] = safe_indicator(lambda: bb_15m.bollinger_lband())
df_15m['bb_mid_15m'] = safe_indicator(lambda: bb_15m.bollinger_mavg())
df_15m['bb_width_15m'] = safe_indicator(lambda: bb_15m.bollinger_wband())
df_15m['bb_pct_15m'] = safe_indicator(lambda: bb_15m.bollinger_pband())

# ATR
for period in [7, 14, 21]:
    df_15m[f'atr_{period}_15m'] = safe_indicator(ta.volatility.average_true_range, df_15m['high'], df_15m['low'], df_15m['close'], window=period)

# Keltner Channel
kc_15m = ta.volatility.KeltnerChannel(df_15m['high'], df_15m['low'], df_15m['close'])
df_15m['kc_high_15m'] = safe_indicator(lambda: kc_15m.keltner_channel_hband())
df_15m['kc_low_15m'] = safe_indicator(lambda: kc_15m.keltner_channel_lband())
df_15m['kc_mid_15m'] = safe_indicator(lambda: kc_15m.keltner_channel_mband())

# Donchian Channel
dc_15m = ta.volatility.DonchianChannel(df_15m['high'], df_15m['low'], df_15m['close'])
df_15m['dc_high_15m'] = safe_indicator(lambda: dc_15m.donchian_channel_hband())
df_15m['dc_low_15m'] = safe_indicator(lambda: dc_15m.donchian_channel_lband())
df_15m['dc_mid_15m'] = safe_indicator(lambda: dc_15m.donchian_channel_mband())
df_15m['dc_width_15m'] = safe_indicator(lambda: dc_15m.donchian_channel_wband())

# Volume indicators
df_15m['obv_15m'] = safe_indicator(ta.volume.on_balance_volume, df_15m['close'], df_15m['volume'])
df_15m['cmf_15m'] = safe_indicator(ta.volume.chaikin_money_flow, df_15m['high'], df_15m['low'], df_15m['close'], df_15m['volume'])
df_15m['mfi_15m'] = safe_indicator(ta.volume.money_flow_index, df_15m['high'], df_15m['low'], df_15m['close'], df_15m['volume'])
df_15m['adi_15m'] = safe_indicator(ta.volume.acc_dist_index, df_15m['high'], df_15m['low'], df_15m['close'], df_15m['volume'])
df_15m['eom_15m'] = safe_indicator(ta.volume.ease_of_movement, df_15m['high'], df_15m['low'], df_15m['volume'])
df_15m['vpt_15m'] = safe_indicator(ta.volume.volume_price_trend, df_15m['close'], df_15m['volume'])
df_15m['nvi_15m'] = safe_indicator(ta.volume.negative_volume_index, df_15m['close'], df_15m['volume'])
df_15m['vwap_15m'] = safe_indicator(ta.volume.volume_weighted_average_price, df_15m['high'], df_15m['low'], df_15m['close'], df_15m['volume'])

# Custom features
df_15m['price_vs_ema20_15m'] = (df_15m['close'] - df_15m['ema_20_15m']) / df_15m['ema_20_15m']
df_15m['price_vs_ema50_15m'] = (df_15m['close'] - df_15m['ema_50_15m']) / df_15m['ema_50_15m']
df_15m['price_vs_bb_mid_15m'] = (df_15m['close'] - df_15m['bb_mid_15m']) / df_15m['bb_mid_15m']
df_15m['ema_cross_15m'] = (df_15m['ema_5_15m'] > df_15m['ema_20_15m']).astype(int)
df_15m['trend_strength_15m'] = abs(df_15m['ema_5_15m'] - df_15m['ema_20_15m']) / df_15m['ema_20_15m']
df_15m['atr_pct_15m'] = df_15m['atr_14_15m'] / df_15m['close']
df_15m['volatility_regime_15m'] = (df_15m['atr_pct_15m'] > df_15m['atr_pct_15m'].rolling(20).mean()).astype(int)
df_15m['rsi_sma_15m'] = df_15m['rsi_14_15m'].rolling(14).mean()
df_15m['rsi_divergence_15m'] = df_15m['rsi_14_15m'] - df_15m['rsi_sma_15m']
df_15m['vol_sma_20_15m'] = df_15m['volume'].rolling(20).mean()
df_15m['volume_surge_15m'] = (df_15m['volume'] > df_15m['vol_sma_20_15m'] * 1.5).astype(int)
df_15m['body_size_15m'] = abs(df_15m['close'] - df_15m['open'])
df_15m['upper_wick_15m'] = df_15m['high'] - df_15m[['open', 'close']].max(axis=1)
df_15m['lower_wick_15m'] = df_15m[['open', 'close']].min(axis=1) - df_15m['low']
df_15m['is_bullish_15m'] = (df_15m['close'] > df_15m['open']).astype(int)

for period in [1, 3, 5, 10]:
    df_15m[f'return_{period}_15m'] = df_15m['close'].pct_change(period)

df_15m['range_pct_15m'] = (df_15m['high'] - df_15m['low']) / df_15m['close']
df_15m['range_vs_atr_15m'] = (df_15m['high'] - df_15m['low']) / (df_15m['atr_14_15m'] + 1e-9)

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
}).dropna()

# Generate 1h features (abbreviated for speed - same pattern as 15m)
print("🔧 Generating 1h features...")

# Key indicators only for 1h to save time
df_1h['rsi_7_1h'] = safe_indicator(ta.momentum.rsi, df_1h['close'], window=7)
df_1h['rsi_14_1h'] = safe_indicator(ta.momentum.rsi, df_1h['close'], window=14)
df_1h['rsi_21_1h'] = safe_indicator(ta.momentum.rsi, df_1h['close'], window=21)

stoch_1h = ta.momentum.StochasticOscillator(df_1h['high'], df_1h['low'], df_1h['close'])
df_1h['stoch_k_1h'] = safe_indicator(lambda: stoch_1h.stoch())
df_1h['stoch_d_1h'] = safe_indicator(lambda: stoch_1h.stoch_signal())

df_1h['williams_r_1h'] = safe_indicator(ta.momentum.williams_r, df_1h['high'], df_1h['low'], df_1h['close'])
df_1h['roc_5_1h'] = safe_indicator(ta.momentum.roc, df_1h['close'], window=5)
df_1h['roc_10_1h'] = safe_indicator(ta.momentum.roc, df_1h['close'], window=10)
df_1h['awesome_osc_1h'] = safe_indicator(ta.momentum.awesome_oscillator, df_1h['high'], df_1h['low'])
df_1h['kama_1h'] = safe_indicator(ta.momentum.kama, df_1h['close'])

ppo_1h = ta.momentum.PercentagePriceOscillator(df_1h['close'])
df_1h['ppo_1h'] = safe_indicator(lambda: ppo_1h.ppo())
df_1h['ppo_signal_1h'] = safe_indicator(lambda: ppo_1h.ppo_signal())
df_1h['ppo_hist_1h'] = safe_indicator(lambda: ppo_1h.ppo_hist())

for period in [5, 10, 20, 50, 100, 200]:
    df_1h[f'ema_{period}_1h'] = safe_indicator(ta.trend.ema_indicator, df_1h['close'], window=period)

for period in [10, 20, 50]:
    df_1h[f'sma_{period}_1h'] = safe_indicator(ta.trend.sma_indicator, df_1h['close'], window=period)

macd_1h = ta.trend.MACD(df_1h['close'])
df_1h['macd_1h'] = safe_indicator(lambda: macd_1h.macd())
df_1h['macd_signal_1h'] = safe_indicator(lambda: macd_1h.macd_signal())
df_1h['macd_hist_1h'] = safe_indicator(lambda: macd_1h.macd_diff())

adx_1h = ta.trend.ADXIndicator(df_1h['high'], df_1h['low'], df_1h['close'])
df_1h['adx_1h'] = safe_indicator(lambda: adx_1h.adx())
df_1h['adx_pos_1h'] = safe_indicator(lambda: adx_1h.adx_pos())
df_1h['adx_neg_1h'] = safe_indicator(lambda: adx_1h.adx_neg())

df_1h['cci_1h'] = safe_indicator(ta.trend.cci, df_1h['high'], df_1h['low'], df_1h['close'])

aroon_1h = ta.trend.AroonIndicator(df_1h['high'], df_1h['low'])
df_1h['aroon_up_1h'] = safe_indicator(lambda: aroon_1h.aroon_up())
df_1h['aroon_down_1h'] = safe_indicator(lambda: aroon_1h.aroon_down())

ichimoku_1h = ta.trend.IchimokuIndicator(df_1h['high'], df_1h['low'])
df_1h['ichimoku_a_1h'] = safe_indicator(lambda: ichimoku_1h.ichimoku_a())
df_1h['ichimoku_b_1h'] = safe_indicator(lambda: ichimoku_1h.ichimoku_b())

bb_1h = ta.volatility.BollingerBands(df_1h['close'])
df_1h['bb_high_1h'] = safe_indicator(lambda: bb_1h.bollinger_hband())
df_1h['bb_low_1h'] = safe_indicator(lambda: bb_1h.bollinger_lband())
df_1h['bb_mid_1h'] = safe_indicator(lambda: bb_1h.bollinger_mavg())
df_1h['bb_width_1h'] = safe_indicator(lambda: bb_1h.bollinger_wband())
df_1h['bb_pct_1h'] = safe_indicator(lambda: bb_1h.bollinger_pband())

for period in [7, 14, 21]:
    df_1h[f'atr_{period}_1h'] = safe_indicator(ta.volatility.average_true_range, df_1h['high'], df_1h['low'], df_1h['close'], window=period)

kc_1h = ta.volatility.KeltnerChannel(df_1h['high'], df_1h['low'], df_1h['close'])
df_1h['kc_high_1h'] = safe_indicator(lambda: kc_1h.keltner_channel_hband())
df_1h['kc_low_1h'] = safe_indicator(lambda: kc_1h.keltner_channel_lband())
df_1h['kc_mid_1h'] = safe_indicator(lambda: kc_1h.keltner_channel_mband())

dc_1h = ta.volatility.DonchianChannel(df_1h['high'], df_1h['low'], df_1h['close'])
df_1h['dc_high_1h'] = safe_indicator(lambda: dc_1h.donchian_channel_hband())
df_1h['dc_low_1h'] = safe_indicator(lambda: dc_1h.donchian_channel_lband())
df_1h['dc_mid_1h'] = safe_indicator(lambda: dc_1h.donchian_channel_mband())
df_1h['dc_width_1h'] = safe_indicator(lambda: dc_1h.donchian_channel_wband())

df_1h['obv_1h'] = safe_indicator(ta.volume.on_balance_volume, df_1h['close'], df_1h['volume'])
df_1h['cmf_1h'] = safe_indicator(ta.volume.chaikin_money_flow, df_1h['high'], df_1h['low'], df_1h['close'], df_1h['volume'])
df_1h['mfi_1h'] = safe_indicator(ta.volume.money_flow_index, df_1h['high'], df_1h['low'], df_1h['close'], df_1h['volume'])
df_1h['adi_1h'] = safe_indicator(ta.volume.acc_dist_index, df_1h['high'], df_1h['low'], df_1h['close'], df_1h['volume'])
df_1h['eom_1h'] = safe_indicator(ta.volume.ease_of_movement, df_1h['high'], df_1h['low'], df_1h['volume'])
df_1h['vpt_1h'] = safe_indicator(ta.volume.volume_price_trend, df_1h['close'], df_1h['volume'])
df_1h['nvi_1h'] = safe_indicator(ta.volume.negative_volume_index, df_1h['close'], df_1h['volume'])
df_1h['vwap_1h'] = safe_indicator(ta.volume.volume_weighted_average_price, df_1h['high'], df_1h['low'], df_1h['close'], df_1h['volume'])

df_1h['price_vs_ema20_1h'] = (df_1h['close'] - df_1h['ema_20_1h']) / df_1h['ema_20_1h']
df_1h['price_vs_ema50_1h'] = (df_1h['close'] - df_1h['ema_50_1h']) / df_1h['ema_50_1h']
df_1h['price_vs_bb_mid_1h'] = (df_1h['close'] - df_1h['bb_mid_1h']) / df_1h['bb_mid_1h']
df_1h['ema_cross_1h'] = (df_1h['ema_5_1h'] > df_1h['ema_20_1h']).astype(int)
df_1h['trend_strength_1h'] = abs(df_1h['ema_5_1h'] - df_1h['ema_20_1h']) / df_1h['ema_20_1h']
df_1h['atr_pct_1h'] = df_1h['atr_14_1h'] / df_1h['close']
df_1h['volatility_regime_1h'] = (df_1h['atr_pct_1h'] > df_1h['atr_pct_1h'].rolling(20).mean()).astype(int)
df_1h['rsi_sma_1h'] = df_1h['rsi_14_1h'].rolling(14).mean()
df_1h['rsi_divergence_1h'] = df_1h['rsi_14_1h'] - df_1h['rsi_sma_1h']
df_1h['vol_sma_20_1h'] = df_1h['volume'].rolling(20).mean()
df_1h['volume_surge_1h'] = (df_1h['volume'] > df_1h['vol_sma_20_1h'] * 1.5).astype(int)
df_1h['body_size_1h'] = abs(df_1h['close'] - df_1h['open'])
df_1h['upper_wick_1h'] = df_1h['high'] - df_1h[['open', 'close']].max(axis=1)
df_1h['lower_wick_1h'] = df_1h[['open', 'close']].min(axis=1) - df_1h['low']
df_1h['is_bullish_1h'] = (df_1h['close'] > df_1h['open']).astype(int)

for period in [1, 3, 5, 10]:
    df_1h[f'return_{period}_1h'] = df_1h['close'].pct_change(period)

df_1h['range_pct_1h'] = (df_1h['high'] - df_1h['low']) / df_1h['close']
df_1h['range_vs_atr_1h'] = (df_1h['high'] - df_1h['low']) / (df_1h['atr_14_1h'] + 1e-9)

print(f"✅ 1h features generated")

# Merge all timeframes
print("\n🔗 Merging all timeframes...")

# Get only feature columns (exclude OHLCV)
exclude_cols = ['open', 'high', 'low', 'close', 'volume', 'taker_buy_base']
features_15m = [c for c in df_15m.columns if c not in exclude_cols]
features_1h = [c for c in df_1h.columns if c not in exclude_cols]

# Merge 15m features to 5m
df_final = df_full_indexed.copy()
df_final = df_final.join(df_15m[features_15m], how='left')

# Merge 1h features to 5m
df_final = df_final.join(df_1h[features_1h], how='left')

# Forward fill
df_final = df_final.fillna(method='ffill').fillna(0)

# Reset index
df_final = df_final.reset_index()

# Filter to Jan 2-14 only
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
