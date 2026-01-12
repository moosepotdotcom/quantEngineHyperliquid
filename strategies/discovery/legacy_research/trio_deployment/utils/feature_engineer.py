#!/usr/bin/env python3
"""
⚡ Ultra Feature Engineer
Generates 100+ features across all timeframes for ML training.
Last updated: 2025-12-28 12:39:00 - Comprehensive error handling for all indicators
"""

import os
import pandas as pd
import numpy as np
import ta
from ta.utils import dropna

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

def add_all_indicators(df):
    """Add comprehensive technical indicators to a dataframe"""
    # Don't drop NA rows at the start - we need all the data for calculations
    
    print(f"      🔧 add_all_indicators START: {len(df)} rows, {len(df.columns)} cols", flush=True)
    
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
            print(f"      ⚠️  Indicator failed: {e}", flush=True)
            # Return a Series of the default value
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
    except (ValueError, IndexError, Exception):
        df['macd'] = pd.Series(0, index=df.index)
        df['macd_signal'] = pd.Series(0, index=df.index)
        df['macd_hist'] = pd.Series(0, index=df.index)
    
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
    except (ValueError, IndexError, Exception):
        df['bb_high'] = df['close']
        df['bb_low'] = df['close']
        df['bb_mid'] = df['close']
        df['bb_width'] = pd.Series(0, index=df.index)
        df['bb_pct'] = pd.Series(0.5, index=df.index)
    
    df['atr_7'] = safe_indicator(lambda: ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=7))
    df['atr_14'] = safe_indicator(lambda: ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14))
    df['atr_21'] = safe_indicator(lambda: ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=21))
    
    try:
        kc = ta.volatility.KeltnerChannel(df['high'], df['low'], df['close'])
        df['kc_high'] = kc.keltner_channel_hband()
        df['kc_low'] = kc.keltner_channel_lband()
        df['kc_mid'] = kc.keltner_channel_mband()
    except (ValueError, IndexError, Exception):
        df['kc_high'] = df['close']
        df['kc_low'] = df['close']
        df['kc_mid'] = df['close']
    
    try:
        dc = ta.volatility.DonchianChannel(df['high'], df['low'], df['close'])
        df['dc_high'] = dc.donchian_channel_hband()
        df['dc_low'] = dc.donchian_channel_lband()
        df['dc_mid'] = dc.donchian_channel_mband()
        df['dc_width'] = dc.donchian_channel_wband()
    except (ValueError, IndexError, Exception):
        df['dc_high'] = df['close']
        df['dc_low'] = df['close']
        df['dc_mid'] = df['close']
        df['dc_width'] = pd.Series(0, index=df.index)
    
    # ===== VOLUME =====
    df['obv'] = safe_indicator(lambda: ta.volume.on_balance_volume(df['close'], df['volume']))
    df['cmf'] = safe_indicator(lambda: ta.volume.chaikin_money_flow(df['high'], df['low'], df['close'], df['volume']))
    df['mfi'] = safe_indicator(lambda: ta.volume.money_flow_index(df['high'], df['low'], df['close'], df['volume']))
    df['adi'] = safe_indicator(lambda: ta.volume.acc_dist_index(df['high'], df['low'], df['close'], df['volume']))
    df['eom'] = safe_indicator(lambda: ta.volume.ease_of_movement(df['high'], df['low'], df['volume']))
    df['vpt'] = safe_indicator(lambda: ta.volume.volume_price_trend(df['close'], df['volume']))
    df['nvi'] = safe_indicator(lambda: ta.volume.negative_volume_index(df['close'], df['volume']))
    df['vwap'] = safe_indicator(lambda: ta.volume.volume_weighted_average_price(df['high'], df['low'], df['close'], df['volume']))
    
    # ===== CUSTOM FEATURES =====
    # Price Position
    df['price_vs_ema20'] = (df['close'] - df['ema_20']) / df['ema_20']
    df['price_vs_ema50'] = (df['close'] - df['ema_50']) / df['ema_50']
    df['price_vs_bb_mid'] = (df['close'] - df['bb_mid']) / df['bb_mid']
    
    # Trend Direction
    df['ema_cross'] = (df['ema_10'] > df['ema_20']).astype(int)
    df['trend_strength'] = df['adx'] * (df['adx_pos'] - df['adx_neg']).apply(np.sign)
    
    # Volatility Regime
    df['atr_pct'] = df['atr_14'] / df['close']
    df['volatility_regime'] = (df['atr_pct'] > df['atr_pct'].rolling(50).mean()).astype(int)
    
    # Momentum Divergence
    df['rsi_sma'] = df['rsi_14'].rolling(5).mean()
    df['rsi_divergence'] = df['rsi_14'] - df['rsi_sma']
    
    # Volume Surge
    df['vol_sma_20'] = df['volume'].rolling(20).mean()
    df['volume_surge'] = df['volume'] / df['vol_sma_20']
    
    # Candlestick Patterns
    df['body_size'] = abs(df['close'] - df['open']) / df['atr_14']
    df['upper_wick'] = (df['high'] - df[['open', 'close']].max(axis=1)) / df['atr_14']
    df['lower_wick'] = (df[['open', 'close']].min(axis=1) - df['low']) / df['atr_14']
    df['is_bullish'] = (df['close'] > df['open']).astype(int)
    
    # Returns
    df['return_1'] = df['close'].pct_change(1)
    df['return_3'] = df['close'].pct_change(3)
    df['return_5'] = df['close'].pct_change(5)
    df['return_10'] = df['close'].pct_change(10)
    
    # Range
    df['range_pct'] = (df['high'] - df['low']) / df['close']
    df['range_vs_atr'] = (df['high'] - df['low']) / df['atr_14']
    
    # Fill NaN values with 0 (for the first few rows where indicators can't be calculated)
    df = df.fillna(0)
    
    return df

def generate_mtf_features():
    """Load all timeframes and generate features"""
    timeframes = ['1m', '3m', '5m', '15m', '30m', '1h', '4h', '1d']
    result = {}
    
    print("⚡ Generating Features Across All Timeframes...")
    
    for tf in timeframes:
        filepath = os.path.join(DATA_DIR, f'BTC_{tf}.csv')
        if os.path.exists(filepath):
            print(f"   🔧 Processing {tf}...", end=" ")
            df = pd.read_csv(filepath)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = add_all_indicators(df)
            
            # Save enriched data
            out_path = os.path.join(DATA_DIR, f'BTC_{tf}_features.csv')
            df.to_csv(out_path, index=False)
            
            n_features = len([c for c in df.columns if c not in ['timestamp', 'open', 'high', 'low', 'close', 'volume']])
            print(f"✅ {n_features} features")
            result[tf] = df
    
    print("\n🎉 Feature engineering complete!")
    return result

if __name__ == '__main__':
    generate_mtf_features()
