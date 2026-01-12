import pandas as pd
import ta

class FeatureEngineer:
    """
    Centralized Feature Engineering.
    Uses 'ta' library to generate technical indicators.
    """
    
    @staticmethod
    def add_all_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Add a standard suite of features for ML models.
        """
        df = FeatureEngineer.add_rsi(df)
        df = FeatureEngineer.add_macd(df)
        df = FeatureEngineer.add_bollinger_bands(df)
        df = FeatureEngineer.add_atr(df)
        df = FeatureEngineer.add_returns(df)
        return df.dropna()

    @staticmethod
    def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        rsi = ta.momentum.RSIIndicator(close=df['close'], window=period)
        df['rsi'] = rsi.rsi()
        return df

    @staticmethod
    def add_macd(df: pd.DataFrame) -> pd.DataFrame:
        macd = ta.trend.MACD(close=df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_diff'] = macd.macd_diff()
        return df

    @staticmethod
    def add_bollinger_bands(df: pd.DataFrame, period: int = 20, dev: int = 2) -> pd.DataFrame:
        bb = ta.volatility.BollingerBands(close=df['close'], window=period, window_dev=dev)
        df['bb_high'] = bb.bollinger_hband()
        df['bb_low'] = bb.bollinger_lband()
        df['bb_width'] = bb.bollinger_wband()
        return df
        
    @staticmethod
    def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        atr = ta.volatility.AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=period)
        df['atr'] = atr.average_true_range()
        return df

    @staticmethod
    def add_returns(df: pd.DataFrame) -> pd.DataFrame:
        """Add Log Returns and Lagged Returns"""
        import numpy as np
        df['log_return'] = pd.Series(df['close']).pct_change().apply(lambda x: np.log(1 + x) if x > -1 else 0)
        # Add lags
        for lag in [1, 2, 3, 5]:
            df[f'return_lag_{lag}'] = df['log_return'].shift(lag)
        return df

if __name__ == "__main__":
    # Test with dummy data
    try:
        import numpy as np
        dates = pd.date_range(start='2022-01-01', periods=100, freq='H')
        df = pd.DataFrame({
            'high': np.random.random(100) * 100 + 10,
            'low': np.random.random(100) * 100,
            'close': np.random.random(100) * 100,
            'volume': np.random.random(100) * 1000
        }, index=dates)
        
        df = FeatureEngineer.add_all_features(df)
        print(df.columns)
        print(df.head())
    except Exception as e:
        print(e)
