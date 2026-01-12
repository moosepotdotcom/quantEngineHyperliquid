import numpy as np
import pandas as pd
from datetime import datetime

def check_winner_hunter(engine):
    """
    Extracted logic for Winner Hunter (1H).
    Pass the main 'engine' instance to access shared methods.
    """
    # Fetch 1H base
    df_1h = engine.fetch_data('1h', 500)
    if df_1h is None or len(df_1h) == 0:
        return None, 0.0
    
    from utils.feature_engineer import add_all_indicators
    df_1h = add_all_indicators(df_1h, use_advanced=False)
    df_1h.set_index('timestamp', inplace=True)
    
    # Fetch 5m context
    df_5m = engine.fetch_data('5m', 500)
    if df_5m is not None and len(df_5m) > 0:
        df_5m = add_all_indicators(df_5m, use_advanced=False)
        df_5m.set_index('timestamp', inplace=True)
        exclude = ['open', 'high', 'low', 'close', 'volume']
        ctx_cols_5m = [c for c in df_5m.columns if c not in exclude]
        df_5m_ctx = df_5m[ctx_cols_5m].copy()
        df_5m_ctx.columns = [f"{c}_5m" for c in ctx_cols_5m]
        df_5m_resampled = df_5m_ctx.reindex(df_1h.index, method='ffill')
        df_1h = pd.concat([df_1h, df_5m_resampled], axis=1)
        
    # Fetch 15m context
    df_15m = engine.fetch_data('15m', 500)
    if df_15m is not None and len(df_15m) > 0:
        df_15m = add_all_indicators(df_15m, use_advanced=False)
        df_15m.set_index('timestamp', inplace=True)
        ctx_cols_15m = [c for c in df_15m.columns if (c not in exclude if 'exclude' in locals() else c not in ['open', 'high', 'low', 'close', 'volume'])]
        df_15m_ctx = df_15m[ctx_cols_15m].copy()
        df_15m_ctx.columns = [f"{c}_15m" for c in ctx_cols_15m]
        df_15m_resampled = df_15m_ctx.reindex(df_1h.index, method='ffill')
        df_1h = pd.concat([df_1h, df_15m_resampled], axis=1)

    # Drop NaN and get latest
    df_1h.dropna(inplace=True)
    if len(df_1h) == 0:
        return None, 0.0
    
    exclude_cols = ['open', 'high', 'low', 'close', 'volume']
    features = [c for c in df_1h.columns if c not in exclude_cols]
    latest = df_1h.iloc[-1]
    X = latest[features].values.reshape(1, -1)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    
    try:
        # Reload thresholds via engine method
        engine.load_thresholds()
        
        probas = engine.get_ensemble_proba('WH', X)[0]
        prob_long = float(probas[1])
        prob_short = float(probas[2])
        
        # Update Dual-Bias UI Storage
        engine.last_probs['WH'] = {'long': prob_long, 'short': prob_short}
        
        direction = None
        confidence = 0.0
        
        # Update Elastic Manager
        engine.wh_elastic.update(prob_long, prob_short)
        
        if prob_long >= engine.wh_elastic.active_threshold_long:
            direction = 'LONG'
            confidence = prob_long
        elif prob_short >= engine.wh_elastic.active_threshold_short:
            direction = 'SHORT'
            confidence = prob_short
        
        # Log prediction
        engine.logger.log_prediction(
            model_name='Winner Hunter (1H)',
            timestamp=datetime.now(),
            features=dict(zip(features, X[0])),
            confidence=confidence,
            signal=direction,
            market_data={'close': float(latest['close']), 'volume': float(latest['volume'])}
        )
        
        if direction:
            return {
                'model': 'Winner Hunter (1H)',
                'timestamp': datetime.now(),
                'price': float(latest['close']),
                'direction': direction,
                'confidence': confidence,
                'rsi': latest.get('rsi_14', 0),
                'macd': latest.get('macd_hist', 0),
                'atr_pct': (latest.get('atr_14', 0) / latest['close']) * 100
            }, confidence
        else:
            # Silent logging
            engine.logger.log_prediction(
                model_name='Winner Hunter (1H)',
                timestamp=datetime.now(),
                features={},
                confidence=max(prob_long, prob_short),
                signal=None,
                market_data={'close': float(latest['close'])},
                is_silent=True
            )
        
        return None, max(prob_long, prob_short)
    except Exception as e:
        engine.logger.error(f"   ⚠️ WH Prediction Error: {e}")
        return None, 0.0
