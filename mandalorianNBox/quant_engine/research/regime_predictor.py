#!/usr/bin/env python3
"""
🔮 Market Regime Predictor
Classifies current market regime and predicts expected trade frequency.
"""

import os
import sys
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.cluster import KMeans
import warnings
warnings.filterwarnings('ignore')

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'utils'))

from feature_engineer import add_all_indicators

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')

class MarketRegimeClassifier:
    """Classifies market into distinct regimes"""
    
    def __init__(self):
        self.regimes = {
            0: "Trending Bull",
            1: "Trending Bear", 
            2: "High Volatility Range",
            3: "Low Volatility Range",
            4: "Choppy/Whipsaw"
        }
        
    def classify_regime(self, df):
        """
        Classify market regime based on features:
        - Trend: EMA slopes, ADX
        - Volatility: ATR, BB Width
        - Momentum: RSI, MACD
        """
        
        # Calculate regime features
        latest = df.iloc[-20:]  # Last 20 bars for regime analysis
        
        # Trend strength
        ema_20 = latest['ema_20'].iloc[-1]
        ema_50 = latest['ema_50'].iloc[-1]
        price = latest['close'].iloc[-1]
        
        trend_direction = 1 if ema_20 > ema_50 else -1
        trend_strength = abs(ema_20 - ema_50) / ema_50
        
        # Volatility
        atr_pct = latest['atr_14'].mean() / price
        bb_width = (latest['bb_high'] - latest['bb_low']).mean() / latest['bb_mid'].mean()
        
        # Momentum consistency
        rsi_std = latest['rsi_14'].std()
        macd_hist_changes = (latest['macd_hist'].diff().abs()).mean()
        
        # Price action
        returns = latest['close'].pct_change()
        return_volatility = returns.std()
        directional_moves = (returns.abs() > 0.005).sum() / len(returns)
        
        # Regime classification logic
        regime_features = {
            'trend_strength': trend_strength,
            'trend_direction': trend_direction,
            'atr_pct': atr_pct,
            'bb_width': bb_width,
            'rsi_std': rsi_std,
            'return_volatility': return_volatility,
            'directional_moves': directional_moves
        }
        
        # Simple rule-based classification
        if trend_strength > 0.02 and trend_direction > 0:
            regime = 0  # Trending Bull
        elif trend_strength > 0.02 and trend_direction < 0:
            regime = 1  # Trending Bear
        elif atr_pct > 0.015 and bb_width > 0.04:
            regime = 2  # High Volatility Range
        elif atr_pct < 0.008 and bb_width < 0.02:
            regime = 3  # Low Volatility Range
        else:
            regime = 4  # Choppy/Whipsaw
            
        return regime, regime_features

class TradeFrequencyPredictor:
    """Predicts expected trades based on market regime"""
    
    def __init__(self):
        self.regime_stats = None
        
    def analyze_historical_regimes(self, timeframe='1h'):
        """Analyze historical data to build regime-trade frequency mapping"""
        
        print(f"\n📊 Analyzing Historical Regimes ({timeframe})...")
        
        # Load historical data with features
        data_path = os.path.join(DATA_DIR, f'BTC_{timeframe}_features.csv')
        df = pd.read_csv(data_path)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Load model
        model_name = 'winner_hunter_1h' if timeframe == '1h' else 'mtf_scalper_5m'
        model = xgb.XGBClassifier()
        model.load_model(os.path.join(MODEL_DIR, f'{model_name}.json'))
        
        # Classify regime for each window
        classifier = MarketRegimeClassifier()
        
        regime_data = []
        window_size = 100
        
        for i in range(window_size, len(df), 24):  # Daily windows
            window = df.iloc[i-window_size:i]
            
            # Classify regime
            regime, features = classifier.classify_regime(window)
            
            # Count signals in this window
            exclude = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            feature_cols = [c for c in window.columns if c not in exclude]
            
            signals = 0
            for j in range(len(window)):
                try:
                    X = window.iloc[j][feature_cols].values.reshape(1, -1)
                    prob = model.predict_proba(X)[0][1]
                    if prob > 0.95:
                        signals += 1
                except:
                    pass
            
            regime_data.append({
                'regime': regime,
                'signals': signals,
                'volatility': features['atr_pct'],
                'trend_strength': features['trend_strength']
            })
        
        # Aggregate by regime
        regime_df = pd.DataFrame(regime_data)
        stats = regime_df.groupby('regime').agg({
            'signals': ['mean', 'std', 'count'],
            'volatility': 'mean',
            'trend_strength': 'mean'
        }).round(2)
        
        self.regime_stats = stats
        return stats
    
    def predict_trades(self, current_regime, timeframe='1h'):
        """Predict expected trades for current regime"""
        
        if self.regime_stats is None:
            self.analyze_historical_regimes(timeframe)
        
        try:
            regime_row = self.regime_stats.loc[current_regime]
            expected_trades = regime_row[('signals', 'mean')]
            std_trades = regime_row[('signals', 'std')]
            
            return {
                'expected_trades_per_day': expected_trades,
                'std_deviation': std_trades,
                'confidence_range': (max(0, expected_trades - std_trades), 
                                   expected_trades + std_trades)
            }
        except:
            return {
                'expected_trades_per_day': 0,
                'std_deviation': 0,
                'confidence_range': (0, 0)
            }

def run_regime_analysis():
    """Run complete regime analysis and prediction"""
    
    print("="*60)
    print("🔮 MARKET REGIME PREDICTOR")
    print("="*60)
    
    # Load current data
    import requests
    
    def fetch_binance(interval='1h', limit=100):
        url = 'https://api.binance.com/api/v3/klines'
        params = {'symbol': 'BTCUSDT', 'interval': interval, 'limit': limit}
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        return df
    
    # Analyze 1H Winner Hunter
    print("\n🏆 Winner Hunter (1H) Analysis:")
    df_1h = fetch_binance('1h', 100)
    df_1h = add_all_indicators(df_1h)
    
    classifier = MarketRegimeClassifier()
    regime_1h, features_1h = classifier.classify_regime(df_1h)
    
    print(f"   Current Regime: {classifier.regimes[regime_1h]}")
    print(f"   Trend Strength: {features_1h['trend_strength']:.4f}")
    print(f"   Volatility (ATR%): {features_1h['atr_pct']:.4f}")
    print(f"   RSI Stability: {features_1h['rsi_std']:.2f}")
    
    predictor_1h = TradeFrequencyPredictor()
    prediction_1h = predictor_1h.predict_trades(regime_1h, '1h')
    
    print(f"\n   📈 Expected Trades (24h):")
    print(f"      Mean: {prediction_1h['expected_trades_per_day']:.1f}")
    print(f"      Range: {prediction_1h['confidence_range'][0]:.1f} - {prediction_1h['confidence_range'][1]:.1f}")
    
    # Analyze 5M Scalper
    print("\n⚡ MTF Scalper (5m) Analysis:")
    df_5m = fetch_binance('5m', 100)
    df_5m = add_all_indicators(df_5m)
    
    regime_5m, features_5m = classifier.classify_regime(df_5m)
    
    print(f"   Current Regime: {classifier.regimes[regime_5m]}")
    print(f"   Trend Strength: {features_5m['trend_strength']:.4f}")
    print(f"   Volatility (ATR%): {features_5m['atr_pct']:.4f}")
    
    predictor_5m = TradeFrequencyPredictor()
    prediction_5m = predictor_5m.predict_trades(regime_5m, '5m')
    
    print(f"\n   📈 Expected Trades (24h):")
    print(f"      Mean: {prediction_5m['expected_trades_per_day']:.1f}")
    print(f"      Range: {prediction_5m['confidence_range'][0]:.1f} - {prediction_5m['confidence_range'][1]:.1f}")
    
    print("\n" + "="*60)
    print("✅ Regime Analysis Complete!")
    print("="*60)

if __name__ == '__main__':
    run_regime_analysis()
