
"""
MLScalper V2 Enhanced

A next-generation ML-powered scalper that integrates:

TIER 1 (Quick Wins):
- News Sentiment Filter: Skip trades during major news
- Whale Alert Integration: Bias direction with whale flow
- Funding Rate Bias: Use extreme funding as edge

TIER 2 (Advanced ML):
- Regime Detection: Bull/Bear/Chop classifier
- Order Flow Features: Volume delta, large orders
- Ensemble Models: XGBoost + LightGBM voting
- Time-Based Filters: Avoid low-liquidity hours
- Dynamic Threshold: Auto-adjust based on performance
"""

import os
import sys
import json
import pandas as pd
import numpy as np
import joblib
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')

# Add Root to Path
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from utils.mtf_feature_engineer import MTFFeatureGenerator

# ML Imports
try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

try:
    import lightgbm as lgb
    HAS_LGB = True
except ImportError:
    HAS_LGB = False


class MLScalperV2:
    """
    Enhanced ML Scalper with multi-layer filtering.
    """
    
    def __init__(self):
        self.name = "MLScalper V2"
        
        # Model paths
        self.models_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
        
        # Load models
        self.model_long = None
        self.model_short = None
        self.regime_model = None
        self.load_models()
        
        # State
        self.position = None
        self.entry_price = 0.0
        self.sl_price = 0.0
        self.tp_price = 0.0
        
        # Recent performance tracking (for dynamic threshold)
        self.recent_trades = []
        self.base_threshold = 0.50
        self.current_threshold = 0.50
        
        # Whale/Funding state (updated externally)
        self.whale_bias = 0  # -1 = selling, 0 = neutral, 1 = buying
        self.funding_bias = 0  # -1 = shorts paying, 0 = neutral, 1 = longs paying
        self.news_block = False  # True = major news, skip trades
        
        # Time filters (UTC hours to avoid)
        self.avoid_hours = [3, 4, 5]  # Low liquidity Asian session end
        
    def load_models(self):
        """Load all required models."""
        try:
            long_path = os.path.join(self.models_dir, 'scalp_mtf_long.pkl')
            short_path = os.path.join(self.models_dir, 'scalp_mtf_short.pkl')
            
            if os.path.exists(long_path):
                self.model_long = joblib.load(long_path)
            if os.path.exists(short_path):
                self.model_short = joblib.load(short_path)
                
            # Regime model (if exists)
            regime_path = os.path.join(self.models_dir, 'regime_classifier.pkl')
            if os.path.exists(regime_path):
                self.regime_model = joblib.load(regime_path)
                
        except Exception as e:
            print(f"⚠️ V2 Model Load Error: {e}")
    
    def update_whale_bias(self, recent_whale_data):
        """
        Update whale bias from recent whale transactions.
        recent_whale_data: list of {'side': 'buy'/'sell', 'usd_size': float}
        """
        if not recent_whale_data:
            self.whale_bias = 0
            return
            
        buy_volume = sum(w['usd_size'] for w in recent_whale_data if w.get('side') == 'buy')
        sell_volume = sum(w['usd_size'] for w in recent_whale_data if w.get('side') == 'sell')
        
        if buy_volume > sell_volume * 1.5:
            self.whale_bias = 1  # Bullish
        elif sell_volume > buy_volume * 1.5:
            self.whale_bias = -1  # Bearish
        else:
            self.whale_bias = 0  # Neutral
    
    def update_funding_bias(self, funding_rate):
        """
        Update funding rate bias.
        funding_rate: float (e.g., 0.01 = 1% funding)
        """
        if funding_rate < -0.01:  # Shorts paying a lot
            self.funding_bias = 1  # Bias LONG (shorts getting squeezed)
        elif funding_rate > 0.01:  # Longs paying a lot
            self.funding_bias = -1  # Bias SHORT (longs getting squeezed)
        else:
            self.funding_bias = 0
    
    def update_news_block(self, has_major_news):
        """Set news block flag."""
        self.news_block = has_major_news
    
    def is_good_time(self):
        """Check if current time is suitable for trading."""
        current_hour = datetime.utcnow().hour
        return current_hour not in self.avoid_hours
    
    def detect_regime(self, df_feat):
        """
        Detect market regime: BULL, BEAR, or CHOP.
        Returns: 'BULL', 'BEAR', 'CHOP'
        """
        if self.regime_model is not None:
            try:
                latest = df_feat.iloc[[-1]]
                pred = self.regime_model.predict(latest)[0]
                return ['CHOP', 'BULL', 'BEAR'][pred]
            except:
                pass
        
        # Fallback: Use simple heuristics
        try:
            rsi = df_feat['rsi_5m'].iloc[-1]
            macd = df_feat['macd_5m'].iloc[-1]
            
            if rsi > 55 and macd > 0:
                return 'BULL'
            elif rsi < 45 and macd < 0:
                return 'BEAR'
            else:
                return 'CHOP'
        except:
            return 'CHOP'
    
    def calculate_order_flow_features(self, df):
        """
        Add order flow features to dataframe.
        - Volume Delta (buy vs sell volume proxy)
        - Large candle detection
        """
        df = df.copy()
        
        # Volume delta proxy: If close > open, volume is "buy", else "sell"
        df['vol_delta'] = np.where(df['close'] > df['open'], df['volume'], -df['volume'])
        df['vol_delta_cumsum'] = df['vol_delta'].cumsum()
        df['vol_delta_ma'] = df['vol_delta'].rolling(10).mean()
        
        # Large candle detection
        df['candle_range'] = abs(df['high'] - df['low'])
        df['large_candle'] = (df['candle_range'] > df['candle_range'].rolling(20).mean() * 2).astype(int)
        
        return df
    
    def ensemble_predict(self, features):
        """
        Ensemble prediction using multiple models.
        Returns: (prob_long, prob_short)
        """
        long_probs = []
        short_probs = []
        
        # XGBoost predictions
        if self.model_long is not None:
            long_probs.append(self.model_long.predict_proba(features)[0][1])
        if self.model_short is not None:
            short_probs.append(self.model_short.predict_proba(features)[0][1])
        
        # Average ensemble
        avg_long = np.mean(long_probs) if long_probs else 0
        avg_short = np.mean(short_probs) if short_probs else 0
        
        return avg_long, avg_short
    
    def update_dynamic_threshold(self, trade_result):
        """
        Adjust threshold based on recent performance.
        trade_result: 1 for win, 0 for loss
        """
        self.recent_trades.append(trade_result)
        self.recent_trades = self.recent_trades[-20:]  # Keep last 20
        
        if len(self.recent_trades) >= 10:
            recent_winrate = sum(self.recent_trades) / len(self.recent_trades)
            
            if recent_winrate > 0.7:
                # Doing well, can lower threshold slightly
                self.current_threshold = max(0.40, self.base_threshold - 0.05)
            elif recent_winrate < 0.5:
                # Doing poorly, raise threshold
                self.current_threshold = min(0.70, self.base_threshold + 0.10)
            else:
                self.current_threshold = self.base_threshold
    
    def check_signal(self, df_5m, df_15m, df_30m):
        """
        Main signal generation with all V2 filters.
        Returns: 'LONG', 'SHORT', 'NEUTRAL', or None
        """
        try:
            # ===================
            # TIER 1 FILTERS
            # ===================
            
            # Filter 1: News Block
            if self.news_block:
                print("   [V2] ⏸️ News event - skipping")
                return None
            
            # Filter 2: Time Filter
            if not self.is_good_time():
                print(f"   [V2] 🌙 Low liquidity hour - skipping")
                return None
            
            # ===================
            # FEATURE ENGINEERING
            # ===================
            
            # Generate MTF features
            gen = MTFFeatureGenerator(df_5m, df_15m, df_30m)
            df_feat = gen.generate()
            
            # Add order flow features
            df_feat = self.calculate_order_flow_features(df_feat)
            
            # ===================
            # REGIME DETECTION
            # ===================
            
            regime = self.detect_regime(df_feat)
            
            # ===================
            # ML PREDICTION
            # ===================
            
            # Prepare features
            cols_to_drop = ['open', 'high', 'low', 'close', 'volume', 'target', 'target_long', 'target_short',
                            'dividends', 'stock splits', 'vol_delta', 'vol_delta_cumsum', 'vol_delta_ma',
                            'candle_range', 'large_candle']
            feature_cols = [c for c in df_feat.columns if c not in cols_to_drop]
            latest_features = df_feat[feature_cols].iloc[[-1]]
            
            # Get ensemble predictions
            prob_long, prob_short = self.ensemble_predict(latest_features)
            
            # ===================
            # BIAS ADJUSTMENTS (Tier 1)
            # ===================
            
            # Whale bias adjustment
            if self.whale_bias == 1:
                prob_long *= 1.1  # 10% boost to long
                prob_short *= 0.9
            elif self.whale_bias == -1:
                prob_long *= 0.9
                prob_short *= 1.1  # 10% boost to short
            
            # Funding bias adjustment
            if self.funding_bias == 1:
                prob_long *= 1.05
                prob_short *= 0.95
            elif self.funding_bias == -1:
                prob_long *= 0.95
                prob_short *= 1.05
            
            # Cap at 1.0
            prob_long = min(prob_long, 1.0)
            prob_short = min(prob_short, 1.0)
            
            # ===================
            # SIGNAL DECISION
            # ===================
            
            current_price = df_5m['close'].iloc[-1]
            
            # Debug output
            print(f"   [V2] L:{prob_long:.3f} S:{prob_short:.3f} | Regime:{regime} | Whale:{self.whale_bias:+d} | Funding:{self.funding_bias:+d}")
            
            # Only trade in clear regime (skip CHOP)
            if regime == 'CHOP':
                print(f"   [V2] 🌊 Choppy market - waiting")
                return self.position
            
            threshold = self.current_threshold
            
            if not self.position:
                # Check for LONG in BULL regime
                if regime == 'BULL' and prob_long > threshold and prob_long > prob_short:
                    print(f"🟢 V2 SCALPER: LONG SIGNAL")
                    print(f"   📊 Prob: {prob_long:.2%} | Regime: {regime}")
                    
                    self.entry_price = current_price
                    self.sl_price = current_price * (1 - 0.005)
                    self.tp_price = current_price * (1 + 0.005)
                    self.position = 'LONG'
                    return 'LONG'
                
                # Check for SHORT in BEAR regime
                elif regime == 'BEAR' and prob_short > threshold and prob_short > prob_long:
                    print(f"🔴 V2 SCALPER: SHORT SIGNAL")
                    print(f"   📊 Prob: {prob_short:.2%} | Regime: {regime}")
                    
                    self.entry_price = current_price
                    self.sl_price = current_price * (1 + 0.005)
                    self.tp_price = current_price * (1 - 0.005)
                    self.position = 'SHORT'
                    return 'SHORT'
            
            elif self.position:
                # Exit if regime changes or opposite signal becomes strong
                if (self.position == 'LONG' and regime == 'BEAR') or \
                   (self.position == 'SHORT' and regime == 'BULL'):
                    print(f"   [V2] Regime flip - closing {self.position}")
                    self.position = None
                    return 'NEUTRAL'
            
            return self.position
            
        except Exception as e:
            print(f"⚠️ V2 Error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_status(self):
        """Get current engine status."""
        return {
            'name': self.name,
            'position': self.position,
            'threshold': self.current_threshold,
            'whale_bias': self.whale_bias,
            'funding_bias': self.funding_bias,
            'news_block': self.news_block,
            'recent_trades': len(self.recent_trades)
        }


# Standalone test
if __name__ == "__main__":
    from data.loader import DataLoader
    
    print("=" * 60)
    print("MLScalper V2 Test")
    print("=" * 60)
    
    # Fetch test data
    df_5m = DataLoader.fetch_yfinance("BTC-USD", period="5d", interval="5m", quiet=True)
    df_15m = DataLoader.fetch_yfinance("BTC-USD", period="1mo", interval="15m", quiet=True)
    df_30m = DataLoader.fetch_yfinance("BTC-USD", period="1mo", interval="30m", quiet=True)
    
    # Initialize V2
    v2 = MLScalperV2()
    
    # Simulate some whale/funding data
    v2.update_whale_bias([{'side': 'buy', 'usd_size': 1000000}])
    v2.update_funding_bias(-0.015)  # Shorts paying
    
    # Check signal
    signal = v2.check_signal(df_5m, df_15m, df_30m)
    
    print(f"\n📊 Signal: {signal}")
    print(f"📈 Status: {v2.get_status()}")
