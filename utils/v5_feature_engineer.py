
import pandas as pd
import numpy as np
import ta

class V5FeatureEngineer:
    """
    Advanced Feature Engineer for V5 Model.
    Combines Order Flow (Volume Delta) with Multi-Timeframe Trend (15m, 1h).
    """
    
    def __init__(self, df_5m):
        self.df_5m = df_5m.copy()
        
    def _calculate_indicators(self, df, suffix=''):
        """Calculates indicators for a given dataframe"""
        # RSI
        df[f'rsi{suffix}'] = ta.momentum.rsi(df['close'], window=14)
        
        # Trend
        df[f'adx{suffix}'] = ta.trend.adx(df['high'], df['low'], df['close'], window=14)
        df[f'ema_50{suffix}'] = ta.trend.ema_indicator(df['close'], window=50)
        df[f'ema_200{suffix}'] = ta.trend.ema_indicator(df['close'], window=200)
        
        # Volatility
        df[f'atr{suffix}'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
        
        # V5 Exclusive: Order Flow (If available)
        if 'taker_buy_base' in df.columns:
            df['taker_sell_base'] = df['volume'] - df['taker_buy_base']
            df[f'volume_delta{suffix}'] = df['taker_buy_base'] - df['taker_sell_base']
            df[f'cvd_1h{suffix}'] = df[f'volume_delta{suffix}'].rolling(12).sum()
            df[f'cvd_4h{suffix}'] = df[f'volume_delta{suffix}'].rolling(48).sum()
            df[f'flow_imbalance{suffix}'] = df[f'volume_delta{suffix}'] / (df['volume'] + 1e-9)
            
        return df

    def generate_features(self):
        # 1. Base 5m Features (Order Flow + Basic Tech)
        df_5m = self._calculate_indicators(self.df_5m, '')
        
        # 2. Resample for Higher Timeframes
        # We need to build 15m and 1h candles from 5m data
        agg_dict = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }
        if 'taker_buy_base' in df_5m.columns:
            agg_dict['taker_buy_base'] = 'sum'
            
        # 15m Resample
        df_15m = df_5m.resample('15min', on='timestamp').agg(agg_dict).dropna()
        df_15m = self._calculate_indicators(df_15m, '_15m')
        
        # 1h Resample
        df_1h = df_5m.resample('1h', on='timestamp').agg(agg_dict).dropna()
        df_1h = self._calculate_indicators(df_1h, '_1h')
        
        # 3. Merge with Lookahead Prevention (Shift=1)
        # We shift the HTF data by 1 period so 12:05 sees 11:45-12:00 candle, NOT 12:00-12:15.
        
        # Select feature columns (exclude raw OHLVC)
        cols_15m = [c for c in df_15m.columns if c not in agg_dict.keys()]
        cols_1h = [c for c in df_1h.columns if c not in agg_dict.keys()]
        
        df_15m_shifted = df_15m[cols_15m].shift(1)
        df_1h_shifted = df_1h[cols_1h].shift(1)
        
        # Reindex to 5m via ffill
        # Ensure 'timestamp' matches index
        if 'timestamp' in df_5m.columns:
            df_5m.set_index('timestamp', inplace=True)
            
        df_15m_aligned = df_15m_shifted.reindex(df_5m.index, method='ffill')
        df_1h_aligned = df_1h_shifted.reindex(df_5m.index, method='ffill')
        
        # Concatenate
        df_final = pd.concat([df_5m, df_15m_aligned, df_1h_aligned], axis=1)
        
        # Clean
        df_final = df_final.replace([np.inf, -np.inf], np.nan).fillna(0)
        df_final.reset_index(inplace=True) # Bring timestamp back
        
        return df_final

def generate_v5_features(df):
    eng = V5FeatureEngineer(df)
    return eng.generate_features()
