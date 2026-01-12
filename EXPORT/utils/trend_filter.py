#!/usr/bin/env python3
"""
Trend Filter - Market Regime Detection
Prevents counter-trend trades by analyzing market structure
"""
import pandas as pd
import numpy as np

def get_market_regime(df):
    """
    Determine if market is bullish, bearish, or ranging
    
    Args:
        df: DataFrame with 'close' column
        
    Returns:
        str: "BULLISH", "BEARISH", or "RANGING"
    """
    if len(df) < 50:
        return "UNKNOWN"
    
    # Calculate EMAs
    ema_20 = df['close'].ewm(span=20, adjust=False).mean().iloc[-1]
    ema_50 = df['close'].ewm(span=50, adjust=False).mean().iloc[-1]
    current_price = df['close'].iloc[-1]
    
    # 0.5% buffer to avoid whipsaws
    bullish_threshold = 1.005
    bearish_threshold = 0.995
    
    # Determine regime
    if ema_20 > ema_50 * bullish_threshold:
        regime = "BULLISH"
    elif ema_20 < ema_50 * bearish_threshold:
        regime = "BEARISH"
    else:
        regime = "RANGING"
    
    # Additional confirmation: price vs EMA20
    if regime == "BULLISH" and current_price < ema_20 * 0.99:
        regime = "RANGING"  # Price below EMA in "bullish" = not confirmed
    elif regime == "BEARISH" and current_price > ema_20 * 1.01:
        regime = "RANGING"  # Price above EMA in "bearish" = not confirmed
    
    return regime

def should_trade(signal_direction, market_regime):
    """
    Determine if signal aligns with market trend
    
    Args:
        signal_direction: "LONG" or "SHORT"
        market_regime: "BULLISH", "BEARISH", or "RANGING"
        
    Returns:
        tuple: (bool, str) - (should_trade, reason)
    """
    # Only trade if signal aligns with trend
    if signal_direction == "LONG":
        if market_regime == "BULLISH":
            return True, "LONG aligned with BULLISH trend"
        elif market_regime == "RANGING":
            return False, "LONG rejected - market RANGING (risky)"
        else:
            return False, f"LONG rejected - market is {market_regime}"
    
    elif signal_direction == "SHORT":
        if market_regime == "BEARISH":
            return True, "SHORT aligned with BEARISH trend"
        elif market_regime == "RANGING":
            return False, "SHORT rejected - market RANGING (risky)"
        else:
            return False, f"SHORT rejected - market is {market_regime}"
    
    return False, "Unknown signal direction"

def get_trend_strength(df):
    """
    Calculate trend strength (0-100)
    
    Args:
        df: DataFrame with 'close' column
        
    Returns:
        float: Trend strength (0 = weak, 100 = strong)
    """
    if len(df) < 50:
        return 0.0
    
    # Calculate ADX-like metric
    ema_20 = df['close'].ewm(span=20, adjust=False).mean()
    ema_50 = df['close'].ewm(span=50, adjust=False).mean()
    
    # Distance between EMAs as % of price
    separation = abs(ema_20.iloc[-1] - ema_50.iloc[-1]) / df['close'].iloc[-1] * 100
    
    # Normalize to 0-100 (assume 2% separation = strong trend)
    strength = min(separation / 0.02 * 100, 100)
    
    return strength

def get_regime_info(df):
    """
    Get comprehensive regime information
    
    Args:
        df: DataFrame with 'close' column
        
    Returns:
        dict: Regime information
    """
    regime = get_market_regime(df)
    strength = get_trend_strength(df)
    
    ema_20 = df['close'].ewm(span=20, adjust=False).mean().iloc[-1]
    ema_50 = df['close'].ewm(span=50, adjust=False).mean().iloc[-1]
    current_price = df['close'].iloc[-1]
    
    return {
        'regime': regime,
        'strength': strength,
        'ema_20': ema_20,
        'ema_50': ema_50,
        'current_price': current_price,
        'price_vs_ema20': (current_price - ema_20) / ema_20 * 100,
        'ema_separation': (ema_20 - ema_50) / ema_50 * 100
    }
