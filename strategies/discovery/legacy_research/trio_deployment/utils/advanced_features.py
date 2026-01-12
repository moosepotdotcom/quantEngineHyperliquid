import numpy as np
import pandas as pd

def calculate_hurst(series, min_window=10, max_window=None):
    """
    Calculate the Hurst Exponent of a time series.
    H < 0.5: Mean Reverting (Anti-persistent)
    H ~ 0.5: Random Walk
    H > 0.5: Trending (Persistent)
    """
    if len(series) < 100:
        return 0.5  # Not enough data
        
    if max_window is None:
        max_window = len(series) // 2
        
    try:
        # Range of lag values
        lags = range(2, min(max_window, 20))
        
        # Calculate variogram
        tau = [np.sqrt(np.std(np.subtract(series[lag:], series[:-lag]))) for lag in lags]
        
        # Fit linear regression to log-log plot
        m = np.polyfit(np.log(lags), np.log(tau), 1)
        hurst = m[0] * 2.0
        
        return hurst
    except:
        return 0.5

def get_rolling_hurst(df, window=100):
    """
    Apply rolling Hurst exponent
    """
    results = []
    # Need efficient rolling
    # For now, simplistic loop (can be slow on huge data, fine for 1 day)
    series = df['close'].values
    
    hurst_values = np.full(len(df), 0.5)
    
    for i in range(window, len(df)):
        chunk = series[i-window:i]
        h = calculate_hurst(chunk)
        hurst_values[i] = h
        
    return hurst_values

def detect_regime(df, window=100):
    """
    Simple Regime Detection using Volatility Z-Score
    High Volatility = Crash/Stress Regime
    Low Volatility = Stable/Bull Regime
    """
    df['returns'] = df['close'].pct_change()
    df['volatility'] = df['returns'].rolling(window=20).std()
    
    # Calculate Z-Score of volatility
    vol_mean = df['volatility'].rolling(window=window).mean()
    vol_std = df['volatility'].rolling(window=window).std()
    
    df['vol_z_score'] = (df['volatility'] - vol_mean) / vol_std
    
    # Threshold: Z > 2.0 implies "Extreme Volatility" (Crash/Explosion)
    return df['vol_z_score']
