
import pandas as pd
import numpy as np
import sys
import os

# Import the heavy indicator generator
from .feature_engineer import add_all_indicators

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
        # 1. Generate features on each timeframe independently using Heavy Indicators
        self.df_5m = add_all_indicators(self.df_5m)
        self.df_15m = add_all_indicators(self.df_15m)
        self.df_30m = add_all_indicators(self.df_30m)
        
        # Add interval specific suffixes to avoid column name collisions before merge
        # Actually add_all_indicators might already have names. 
        # But we need them to match what the model expects: e.g. 'rsi_14_15m'
        
        # Suffix handling
        cols_15m = [c for c in self.df_15m.columns if c not in ['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        self.df_15m.rename(columns={c: f"{c}_15m" for c in cols_15m}, inplace=True)
        
        cols_30m = [c for c in self.df_30m.columns if c not in ['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        self.df_30m.rename(columns={c: f"{c}_30m" for c in cols_30m}, inplace=True)
        
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
        
        # Columns to merge (exclude base OHLCV from 15m/30m)
        current_cols_15m = [c for c in self.df_15m.columns if "_15m" in c]
        current_cols_30m = [c for c in self.df_30m.columns if "_30m" in c]
        
        # Reindex higher TFs to 5m index
        # ⚠️ CRITICAL SENSITIVE FIX: LOOKAHEAD PREVENTION
        # We MUST shift the higher timeframe data by 1 row.
        # Why? 
        # Candle 15m at 12:00 covers 12:00-12:15.
        # Candle 5m  at 12:05 is INSIDE this period.
        # If we ffill 12:05 -> it matches 12:00 15m candle.
        # BUT 12:00 15m candle data (Close, RSI, etc) is finalized at 12:15.
        # Trading at 12:05 using 12:15 close is CHEATING (Future Leak).
        # FIX: Shift data so 12:00 row contains 11:45 data.
        
        df_15m_shifted = self.df_15m[current_cols_15m].shift(1)
        df_30m_shifted = self.df_30m[current_cols_30m].shift(1)
        
        df_15m_resampled = df_15m_shifted.reindex(self.df_5m.index, method='ffill')
        df_30m_resampled = df_30m_shifted.reindex(self.df_5m.index, method='ffill')
        
        # Concatenate
        df_final = pd.concat([self.df_5m, df_15m_resampled, df_30m_resampled], axis=1)
        
        # Drop NaNs created by indicators warmup
        df_final.dropna(inplace=True)
        
        # --- ENSURE EXACT 231 FEATURES FOR V2 ---
        # The V2 model expects exactly the 77 indicators * 3 timeframes = 231
        # Indicators list (77 per TF)
        base_indicators = [
            "rsi_7","rsi_14","rsi_21","stoch_k","stoch_d","williams_r","roc_5","roc_10","awesome_osc","kama",
            "ppo","ppo_signal","ppo_hist","ema_5","ema_10","ema_20","ema_50","ema_100","ema_200","sma_10",
            "sma_20","sma_50","macd","macd_signal","macd_hist","adx","adx_pos","adx_neg","cci","aroon_up",
            "aroon_down","ichimoku_a","ichimoku_b","bb_high","bb_low","bb_mid","bb_width","bb_pct","atr_7",
            "atr_14","atr_21","kc_high","kc_low","kc_mid","dc_high","dc_low","dc_mid","dc_width","obv",
            "cmf","mfi","adi","eom","vpt","nvi","vwap","price_vs_ema20","price_vs_ema50","price_vs_bb_mid",
            "ema_cross","trend_strength","atr_pct","volatility_regime","rsi_sma","rsi_divergence","vol_sma_20",
            "volume_surge","body_size","upper_wick","lower_wick","is_bullish","return_1","return_3","return_5",
            "return_10","range_pct","range_vs_atr"
        ]
        
        # Build the exact list of 231 features in the expected order
        v2_features = []
        v2_features.extend(base_indicators)
        v2_features.extend([f"{c}_15m" for c in base_indicators])
        v2_features.extend([f"{c}_30m" for c in base_indicators])
        
        if len(v2_features) != 231:
             print(f"⚠️ MTFFeatureGenerator: INTERNAL Feature count mismatch! Built {len(v2_features)}, expected 231")
        
        return df_final[v2_features], df_final[['open', 'high', 'low', 'close', 'volume']]
