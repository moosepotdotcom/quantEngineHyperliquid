import pandas as pd
import numpy as np
import ta
import logging

logger = logging.getLogger(__name__)

class FeatureEngineer:
    def __init__(self, df):
        self.df = df.copy()
        
    def generate_features(self):
        """Generate a wide range of technical features"""
        logger.info("🏗️ Generating features...")
        
        # Ensure columns are lowercase
        self.df.columns = [c.lower() for c in self.df.columns]
        
        # 1. Momentum Indicators
        self.df['rsi'] = ta.momentum.rsi(self.df['close'], window=14)
        self.df['rsi_short'] = ta.momentum.rsi(self.df['close'], window=7)
        self.df['rsi_long'] = ta.momentum.rsi(self.df['close'], window=21)
        
        # 2. Trend Indicators
        self.df['macd'] = ta.trend.macd(self.df['close'])
        self.df['macd_signal'] = ta.trend.macd_signal(self.df['close'])
        self.df['macd_diff'] = ta.trend.macd_diff(self.df['close'])
        
        # 3. Volatility Indicators
        self.df['bb_high'] = ta.volatility.bollinger_hband(self.df['close'])
        self.df['bb_low'] = ta.volatility.bollinger_lband(self.df['close'])
        self.df['bb_width'] = (self.df['bb_high'] - self.df['bb_low']) / self.df['close']
        self.df['atr'] = ta.volatility.average_true_range(self.df['high'], self.df['low'], self.df['close'])
        
        # 4. Volume Indicators
        self.df['obv'] = ta.volume.on_balance_volume(self.df['close'], self.df['volume'])
        self.df['mfi'] = ta.volume.money_flow_index(self.df['high'], self.df['low'], self.df['close'], self.df['volume'])
        
        # 5. Statistical Features
        self.df['returns'] = self.df['close'].pct_change()
        self.df['log_returns'] = np.log(self.df['close'] / self.df['close'].shift(1))
        self.df['volatility_sigma'] = self.df['returns'].rolling(window=20).std()
        
        # 6. Target Labels (for future ML models)
        # Look ahead 5 periods: Is the price higher?
        self.df['target_5_up'] = (self.df['close'].shift(-5) > self.df['close']).astype(int)
        
        # Drop NaNs
        self.df.dropna(inplace=True)
        
        logger.info(f"✅ Generated {len(self.df.columns)} features for {len(self.df)} rows.")
        return self.df

if __name__ == "__main__":
    # Test on BTC daily
    df = pd.read_csv("/Users/alifiyaa/Downloads/ATC Bootcamp Code 2025/datasets/BTCUSD-1d-1000wks-data.csv")
    fe = FeatureEngineer(df)
    features_df = fe.generate_features()
    print(features_df.head())
    print(f"\nExample Features: {list(features_df.columns)[:10]}...")
