import numpy as np
import pandas as pd
from datetime import datetime

# Feature list used by this specific model
MTF_FEATURE_LIST = [
    'rsi_14', 'macd', 'macd_signal', 'macd_hist', 'cci_14', 'adx', 'mfi_14', 'willr_14',
    'bollinger_hband', 'bollinger_lband', 'bollinger_mavg', 'stoch_k', 'stoch_d',
    'ema_9', 'ema_21', 'ema_50', 'ema_100', 'ema_200', 'atr_14',
    'rsi_14_15m', 'macd_hist_15m', 'ema_50_15m', 'bollinger_hband_15m',
    'rsi_14_1h', 'macd_hist_1h', 'ema_100_1h', 'bollinger_hband_1h'
]

def check_mtf_scalper(engine):
    """
    Extracted logic for MTF Scalper (5M).
    Pass the main 'engine' instance to access shared methods like fetch_data and get_ensemble_proba.
    """
    # Fetch 5m base
    df_5m = engine.fetch_data('5m', 500)
    if df_5m is None or len(df_5m) == 0:
        return None, 0.0
    
    # Process indicators via shared utility
    from utils.feature_engineer import add_all_indicators
    df_5m = add_all_indicators(df_5m)
    
    # --- MANDALORIAN PROTOCOL: Hurst Exponent ---
    try:
        from utils.advanced_features import get_rolling_hurst
        df_5m['hurst'] = get_rolling_hurst(df_5m, window=100)
    except ImportError:
        engine.logger.info("   ⚠️ Hurst feature missing, defaulting to 0.5")
        df_5m['hurst'] = 0.5

    df_5m.set_index('timestamp', inplace=True)
    
    # Fetch 15m context
    df_15m = engine.fetch_data('15m', 500)
    if df_15m is None or len(df_15m) == 0:
        return None, 0.0
    df_15m = add_all_indicators(df_15m)
    df_15m.set_index('timestamp', inplace=True)
    
    # Merge 15m context
    exclude = ['open', 'high', 'low', 'close', 'volume']
    ctx_cols_15m = [c for c in df_15m.columns if c not in exclude]
    df_15m_renamed = df_15m[ctx_cols_15m].copy()
    df_15m_renamed.columns = [f"{c}_15m" for c in ctx_cols_15m]
    df_15m_resampled = df_15m_renamed.reindex(df_5m.index, method='ffill')
    df_5m = pd.concat([df_5m, df_15m_resampled], axis=1)
    
    # Fetch 1h context
    df_1h = engine.fetch_data('1h', 500)
    if df_1h is None or len(df_1h) == 0:
        return None, 0.0
    df_1h = add_all_indicators(df_1h)
    df_1h.set_index('timestamp', inplace=True)
    
    # Merge 1h context
    ctx_cols_1h = [c for c in df_1h.columns if c not in exclude]
    df_1h_renamed = df_1h[ctx_cols_1h].copy()
    df_1h_renamed.columns = [f"{c}_1h" for c in ctx_cols_1h]
    df_1h_resampled = df_1h_renamed.reindex(df_5m.index, method='ffill')
    df_5m = pd.concat([df_5m, df_1h_resampled], axis=1)
    
    # Drop NaN and get latest
    df_5m.dropna(inplace=True)
    if len(df_5m) == 0:
        return None, 0.0
    
    # Prepare features
    latest_data = df_5m.iloc[-1]
    X_dict = {c: latest_data.get(c, 0.0) for c in MTF_FEATURE_LIST}
    X = np.array([X_dict[c] for c in MTF_FEATURE_LIST]).reshape(1, -1)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    
    # Ensemble Prediction
    probas = engine.get_ensemble_proba('MTF', X)[0]
    prob_long = float(probas[1])
    prob_short = float(probas[2])
    
    # Update Dual-Bias UI Storage
    engine.last_probs['MTF'] = {'long': prob_long, 'short': prob_short}
    
    direction = None
    confidence = 0.0
    
    # Update Elastic Manager
    engine.mtf_elastic.update(prob_long, prob_short)
    
    # Strategy Logic
    use_rel_strength = getattr(engine, 'use_relative_strength', False)
    
    if use_rel_strength:
        # Relative Strength Mode (Ratio)
        min_conf = 0.20
        ratio = engine.mtf_elastic.active_threshold_long # Use threshold as ratio (e.g. 1.2)
        
        if max(prob_long, prob_short) >= min_conf:
            if prob_long > prob_short * ratio:
                direction = 'LONG'
                confidence = prob_long
            elif prob_short > prob_long * ratio:
                direction = 'SHORT'
                confidence = prob_short
    else:
        # Standard Absolute Threshold Mode
        if prob_long >= engine.mtf_elastic.active_threshold_long:
            direction = 'LONG'
            confidence = prob_long
        elif prob_short >= engine.mtf_elastic.active_threshold_short:
            direction = 'SHORT'
            confidence = prob_short
    
    # Log prediction
    engine.logger.log_prediction(
        model_name='MTF Scalper (5M)',
        timestamp=datetime.now(),
        features=dict(zip(MTF_FEATURE_LIST, X[0])),
        confidence=confidence,
        signal=direction,
        market_data={'close': float(latest_data['close']), 'volume': float(latest_data['volume'])}
    )
    
    # Shield Checks
    if direction:
        price = float(latest_data['close'])
        if not price or price <= 0 or pd.isna(price):
            return None, confidence
        
        # Mandalorian Hurst Filter
        rsi = latest_data.get('rsi_14', 50)
        hurst = latest_data.get('hurst', 0.5)
        if engine.use_hurst and direction == 'LONG' and rsi < 30 and hurst > 0.50:
            print(f"   🛑 MANDALORIAN SHIELD: Blocked Falling Knife (Hurst={hurst:.3f}, RSI={rsi:.1f})")
            return None, confidence
        
        # Trend-Fuel Filter (ADX)
        adx_val = latest_data.get('adx', 20)
        if hasattr(engine, 'use_adx_filter') and engine.use_adx_filter and adx_val < 30:
            print(f"   🛑 TREND-FUEL SHIELD: Blocked Choppy Market (ADX={adx_val:.1f} < 30)")
            return None, confidence
        
        # Adaptive ATR Shield
        atr_val = latest_data.get('atr_14', 50)
        required_conf = engine.mtf_elastic.active_threshold_long if direction == 'LONG' else engine.mtf_elastic.active_threshold_short
        
        if engine.use_atr_penalty and atr_val > 70:
            penalty = (atr_val - 70) * 0.002
            required_conf += penalty
            
        if confidence < required_conf:
            print(f"   🛡️ ADAPTIVE SHIELD: Blocked noise (Conf {confidence:.3f} < {required_conf:.3f}, ATR={atr_val:.1f})")
            return None, confidence

        # AI Smart Filter
        rsi7 = latest_data.get('rsi_7', 50)
        if direction == 'SHORT' and rsi7 < 25:
            print(f"   🛑 AI SMART FILTER: Blocked Oversold Short (RSI_7={rsi7:.1f})")
            return None, confidence
        
        return {
            'model': 'MTF Scalper (5M)',
            'timestamp': datetime.now(),
            'price': price,
            'direction': direction,
            'confidence': confidence,
            'rsi': float(latest_data.get('rsi_14', 0)),
            'macd': float(latest_data.get('macd', 0)),
            'atr_pct': (float(latest_data.get('atr_14', 0)) / price * 100) if price > 0 else 0
        }, confidence
    
    return None, max(prob_long, prob_short)
