import pandas as pd
import numpy as np
import ta
import logging
import os

logger = logging.getLogger(__name__)

class AdvancedFeatureGenerator:
    """
    Automatically generates hundreds of technical features for ML models.
    """
    def __init__(self, df):
        self.df = df.copy()
        self.df.columns = [c.lower() for c in self.df.columns]
        
    def add_momentum_features(self):
        for w in [7, 14, 21, 30]:
            self.df[f'rsi_{w}'] = ta.momentum.rsi(self.df['close'], window=w)
            self.df[f'roc_{w}'] = ta.momentum.roc(self.df['close'], window=w)
        self.df['stoch_k'] = ta.momentum.stoch(self.df['high'], self.df['low'], self.df['close'])
        self.df['stoch_d'] = ta.momentum.stoch_signal(self.df['high'], self.df['low'], self.df['close'])
        
    def add_trend_features(self):
        for w in [20, 50, 100, 200]:
            self.df[f'sma_{w}'] = ta.trend.sma_indicator(self.df['close'], window=w)
            self.df[f'ema_{w}'] = ta.trend.ema_indicator(self.df['close'], window=w)
            self.df[f'dist_sma_{w}'] = (self.df['close'] - self.df[f'sma_{w}']) / self.df[f'sma_{w}']
        
        self.df['adx'] = ta.trend.adx(self.df['high'], self.df['low'], self.df['close'])
        self.df['macd'] = ta.trend.macd(self.df['close'])
        self.df['macd_diff'] = ta.trend.macd_diff(self.df['close'])
        
    def add_volatility_features(self):
        self.df['atr'] = ta.volatility.average_true_range(self.df['high'], self.df['low'], self.df['close'])
        self.df['bb_high'] = ta.volatility.bollinger_hband(self.df['close'])
        self.df['bb_low'] = ta.volatility.bollinger_lband(self.df['close'])
        self.df['bb_width'] = (self.df['bb_high'] - self.df['bb_low']) / self.df['close']
        
    def add_volume_features(self):
        self.df['obv'] = ta.volume.on_balance_volume(self.df['close'], self.df['volume'])
        self.df['mfi'] = ta.volume.money_flow_index(self.df['high'], self.df['low'], self.df['close'], self.df['volume'])
        self.df['vol_sma'] = self.df['volume'].rolling(20).mean()
        self.df['vol_ratio'] = self.df['volume'] / self.df['vol_sma']
        
    def add_custom_features(self):
        # Log Returns
        self.df['log_ret'] = np.log(self.df['close'] / self.df['close'].shift(1))
        # Volatility
        self.df['volatility'] = self.df['log_ret'].rolling(20).std()
        # Price Action
        self.df['upper_shadow'] = self.df['high'] - np.maximum(self.df['close'], self.df['open'])
        self.df['lower_shadow'] = np.minimum(self.df['close'], self.df['open']) - self.df['low']
        self.df['body'] = np.abs(self.df['close'] - self.df['open'])
        
    def generate_all(self):
        logger.info("🚀 Generating Advanced Feature Set...")
        self.add_momentum_features()
        self.add_trend_features()
        self.add_volatility_features()
        self.add_volume_features()
        self.add_custom_features()
        
        # Add labels for ML
        # 1: Price goes up in next 5 bars, 0: otherwise
        self.df['target'] = (self.df['close'].shift(-5) > self.df['close']).astype(int)
        
        # Drop initial NaNs from indicators
        self.df.dropna(inplace=True)
        logger.info(f"✅ Generated {len(self.df.columns)} features.")
        return self.df

if __name__ == "__main__":
    # Test on BTC data
    data_path = "/Users/alifiyaa/Downloads/ATC Bootcamp Code 2025/datasets/BTCUSD-1h-500wks-data.csv"
    if os.path.exists(data_path):
        raw_df = pd.read_csv(data_path)
        gen = AdvancedFeatureGenerator(raw_df)
        df_feat = gen.generate_all()
        print(df_feat.tail())
        print(f"Features: {list(df_feat.columns)}")
