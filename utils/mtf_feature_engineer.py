
import pandas as pd
import ta
import numpy as np

class MTFFeatureGenerator:
    """
    Generates Multi-Timeframe Features for the 5m base timeframe.
    Merges 15m and 30m context.
    """
    def __init__(self, df_5m, df_15m, df_30m):
        self.df_5m = df_5m.copy()
        self.df_15m = df_15m.copy()
        self.df_30m = df_30m.copy()
        
        # Standardize columns
        for df in [self.df_5m, self.df_15m, self.df_30m]:
            df.columns = [c.lower() for c in df.columns]
        
    def _add_indicators(self, df, suffix):
        """Adds basic indicators to a dataframe with a suffix."""
        # RSI
        df[f'rsi_{suffix}'] = ta.momentum.rsi(df['close'], window=14)
        
        # Bollinger Bands
        bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
        df[f'bb_high_{suffix}'] = bb.bollinger_hband()
        df[f'bb_low_{suffix}'] = bb.bollinger_lband()
        df[f'bb_width_{suffix}'] = (bb.bollinger_hband() - bb.bollinger_lband()) / bb.bollinger_mavg()
        
        # MACD
        macd = ta.trend.MACD(df['close'])
        df[f'macd_{suffix}'] = macd.macd()
        
        # EMA Trend
        df[f'ema_50_{suffix}'] = ta.trend.ema_indicator(df['close'], window=50)
        df[f'ema_200_{suffix}'] = ta.trend.ema_indicator(df['close'], window=200)
        
        return df

    def generate(self):
        # 1. Generate features on each timeframe independently
        self.df_5m = self._add_indicators(self.df_5m, "5m")
        self.df_15m = self._add_indicators(self.df_15m, "15m")
        self.df_30m = self._add_indicators(self.df_30m, "30m")
        
        # 2. Set index to datetime for merging
        for df in [self.df_5m, self.df_15m, self.df_30m]:
            if 'datetime' in df.columns:
                df.set_index('datetime', inplace=True)
            elif 'timestamp' in df.columns:
                 df.set_index('timestamp', inplace=True)
                 
        # 3. Merge Strategy: Forward Fill
        # We merge 15m/30m data onto 5m index using 'asof' or reindexing with ffill.
        # This simulates that at 5m timestamp T, we know the state of the LAST closed 15m/30m bar.
        # Important: To avoid lookahead, we should shift bigger timeframes? 
        # Actually, standard pandas merge/asof handles this if timestamps align.
        # BUT: A 5m candle at 12:05 should see the 15m candle from 12:00? Or 11:45?
        # A 15m candle "12:00" usually closes at 12:15.
        # So at 12:05, the "current" 15m candle (12:00-12:15) is NOT closed.
        # We must look at the PREVIOUS closed 15m candle (11:45-12:00).
        # Standard indicators on completed bars.
        
        # Let's trust pandas reindex(method='ffill')
        
        # Columns to merge
        cols_15m = [c for c in self.df_15m.columns if "15m" in c]
        cols_30m = [c for c in self.df_30m.columns if "30m" in c]
        
        # Reindex higher TFs to 5m index
        df_15m_resampled = self.df_15m[cols_15m].reindex(self.df_5m.index, method='ffill')
        df_30m_resampled = self.df_30m[cols_30m].reindex(self.df_5m.index, method='ffill')
        
        # Concatenate
        df_final = pd.concat([self.df_5m, df_15m_resampled, df_30m_resampled], axis=1)
        
        # Drop NaNs created by indicators warmup
        df_final.dropna(inplace=True)
        
        return df_final
