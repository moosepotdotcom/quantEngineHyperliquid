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
    # If price is below EMA20 in a Bull Trend, it might be a pullback or reversal (Weak Bull)
    # But for strict filtering, we stick to the EMA crossover regime.
    
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
    # UNKNOWN Regime -> Allow with caution (or block?) -> Allow for now
    if market_regime == "UNKNOWN":
        return True, "Unknown Regime - Caution"

    if signal_direction == "LONG":
        if market_regime == "BULLISH":
            return True, "✅ LONG aligned with BULLISH trend"
        elif market_regime == "RANGING":
            return False, "❌ LONG rejected - market RANGING (risky)"
        else:
            return False, f"❌ LONG rejected - market is {market_regime}"
    
    elif signal_direction == "SHORT":
        if market_regime == "BEARISH":
            return True, "✅ SHORT aligned with BEARISH trend"
        elif market_regime == "RANGING":
            return False, "❌ SHORT rejected - market RANGING (risky)"
        else:
            return False, f"❌ SHORT rejected - market is {market_regime}"
    
    return False, "Unknown signal direction"
