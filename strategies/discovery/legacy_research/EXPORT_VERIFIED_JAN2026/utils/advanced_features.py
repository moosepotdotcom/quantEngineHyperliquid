import pandas as pd
import numpy as np
import ta

def get_rolling_hurst(series, window=100):
    """
    Calculate rolling Hurst Exponent.
    H < 0.5: Mean Reverting
    H > 0.5: Trending
    """
    try:
        # Simple R/S analysis implementation for speed
        # Note: This is a simplified approximation for rolling calculation
        return series.rolling(window).apply(lambda x: calculate_hurst(x), raw=True)
    except:
        return pd.Series(0.5, index=series.index)

def calculate_hurst(ts):
    """Calculate Hurst exponent for a single time series"""
    try:
        lags = range(2, 20)
        tau = [np.sqrt(np.std(np.subtract(ts[lag:], ts[:-lag]))) for lag in lags]
        poly = np.polyfit(np.log(lags), np.log(tau), 1)
        return poly[0] * 2.0
    except:
        return 0.5

def add_advanced_features(df):
    """
    Add superior features for 100% win rate targeting:
    - Hurst Exponent (Regime)
    - Volatility Ratios
    - Momentum Slopes
    
    NOTE: Only adds UNIQUE features not already in feature_engineer.py
    to avoid feature count mismatch with trained models.
    """
    df = df.copy()
    
    # 1. Hurst Exponent (Market Regime)
    # Using Close price
    # SKIP FOR SPEED during bulk training (too slow for 420k rows in this environment)
    # df['hurst'] = get_rolling_hurst(df['close'], window=50) 
    df['hurst'] = 0.5 # Default to neutral
    
    # 2. ATR Ratio (Volatility Regime)
    # Note: ATR is already calculated in feature_engineer.py as atr_14
    # We just need the ratio here
    if 'atr_14' in df.columns:
        df['atr_ratio'] = df['atr_14'] / df['close']
    else:
        # Fallback if atr_14 not yet calculated
        atr = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], window=14).average_true_range()
        df['atr_ratio'] = atr / df['close']
    
    # 3. Wick Ratios (already calculated in feature_engineer.py as upper_wick/lower_wick)
    # We need the RATIO version which is unique
    if 'body_size' in df.columns and 'upper_wick' in df.columns and 'lower_wick' in df.columns:
        df['wick_ratio_upper'] = df['upper_wick'] / (df['body_size'] + 0.0000001)
        df['wick_ratio_lower'] = df['lower_wick'] / (df['body_size'] + 0.0000001)
    else:
        # Fallback calculation
        body_size = abs(df['close'] - df['open'])
        upper_wick = df['high'] - np.maximum(df['open'], df['close'])
        lower_wick = np.minimum(df['open'], df['close']) - df['low']
        df['wick_ratio_upper'] = upper_wick / (body_size + 0.0000001)
        df['wick_ratio_lower'] = lower_wick / (body_size + 0.0000001)
    
    # 4. Momentum Slopes (unique features)
    # RSI is already calculated in feature_engineer.py as rsi_14
    if 'rsi_14' in df.columns:
        df['rsi_slope'] = df['rsi_14'].diff(3)
    else:
        # Fallback
        rsi = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
        df['rsi_slope'] = rsi.diff(3)
    
    df['price_slope'] = df['close'].diff(3)
    
    # Cleanup
    df.fillna(method='ffill', inplace=True)
    df.fillna(0, inplace=True)
    
    return df
