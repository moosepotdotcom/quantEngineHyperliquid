
"""
MLScalper V2 Enhanced - Isolated Logic
"""

import os
import sys
import json
import pandas as pd
import numpy as np
import joblib
from datetime import datetime

# Add root to path for utils
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'utils')))

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


class MLScalperV2Logic:
    """
    Enhanced ML Scalper with multi-layer filtering (Isolated for Connector).
    """
    
    def __init__(self):
        self.name = "MLScalper V2"
        
        # Model paths (Local to this engine)
        self.models_dir = os.path.join(os.path.dirname(__file__), 'weights')
        
        # Load models
        self.model_v2 = None
        self.regime_model = None
        self.load_models()
        
        # State
        self.position = None
        self.entry_price = 0.0
        self.sl_price = 0.0
        self.tp_price = 0.0
        
        # Recent performance tracking
        self.recent_trades = []
        self.base_threshold = 0.50
        self.current_threshold = 0.50
        
        # External Bias State
        self.whale_bias = 0
        self.funding_bias = 0
        self.news_block = False
        self.last_probs = (0.0, 0.0)
        
        # Time filters
        self.avoid_hours = [3, 4, 5]
        
    def load_models(self):
        """Load all required models from local weights dir."""
        try:
            # V2 Model
            v3_pkl_path = os.path.join(self.models_dir, 'mtf_scalper_v3.pkl')
            v2_json_path = os.path.join(self.models_dir, 'mtf_scalper_5m_v2.json')
            v2_pkl_path = os.path.join(self.models_dir, 'mtf_scalper_5m_v2_calibrated.pkl')
            
            if os.path.exists(v3_pkl_path):
                self.model_v2 = joblib.load(v3_pkl_path)
                print(f"   ✅ [V2 Logic] Loaded V3 MODEL: {os.path.basename(v3_pkl_path)}")
            elif os.path.exists(v2_pkl_path):
                self.model_v2 = joblib.load(v2_pkl_path)
                print(f"   ✅ [V2 Logic] Loaded PKL: {os.path.basename(v2_pkl_path)}")
            elif os.path.exists(v2_json_path):
                self.model_v2 = xgb.Booster()
                self.model_v2.load_model(v2_json_path)
                print(f"   ✅ [V2 Logic] Loaded JSON: {os.path.basename(v2_json_path)}")
            else:
                print(f"   ⚠️ [V2 Logic] Model Files not found in {self.models_dir}")
                
            # Regime model
            regime_path = os.path.join(self.models_dir, 'regime_classifier.pkl')
            if os.path.exists(regime_path):
                self.regime_model = joblib.load(regime_path)
                
        except Exception as e:
            print(f"⚠️ [V2 Logic] Model Load Error: {e}")
    
    def update_whale_bias(self, bias):
        self.whale_bias = bias

    def update_funding_bias(self, bias):
        self.funding_bias = bias

    def is_good_time(self):
        current_hour = datetime.utcnow().hour
        return current_hour not in self.avoid_hours
    
    def detect_regime(self, df_feat):
        if self.regime_model is not None:
            try:
                latest = df_feat.iloc[[-1]]
                pred = self.regime_model.predict(latest)[0]
                return ['CHOP', 'BULL', 'BEAR'][pred]
            except:
                pass
        
        # Fallback Heuristics
        try:
            rsi = df_feat['rsi_5m'].iloc[-1]
            macd = df_feat['macd_5m'].iloc[-1]
            if rsi > 55 and macd > 0: return 'BULL'
            elif rsi < 45 and macd < 0: return 'BEAR'
            else: return 'CHOP'
        except:
            return 'CHOP'
    
    def ensemble_predict(self, features):
        if hasattr(self, 'model_v2') and self.model_v2:
            if hasattr(self.model_v2, 'predict_proba'):
                probs = self.model_v2.predict_proba(features)[0]
                return probs[1], probs[0] # Long, Short
            elif hasattr(self.model_v2, 'predict'):
                dmat = xgb.DMatrix(features)
                prob_long = self.model_v2.predict(dmat)[0]
                return prob_long, 1.0 - prob_long
        return 0.0, 0.0

    def analyze(self, df_5m, df_15m, df_30m):
        """
        Analyze DataFrames and return Dict signal equivalent to BaseEngine expectation
        """
        try:
            if self.news_block: return None
            # if not self.is_good_time(): return None
            
            # Feature Engineering
            gen = MTFFeatureGenerator(df_5m, df_15m, df_30m)
            latest_features, price_df = gen.generate()
            latest_features = latest_features.iloc[[-1]]
            
            # Regime
            regime = self.detect_regime(latest_features)
            
            # Predict
            prob_long, prob_short = self.ensemble_predict(latest_features)
            self.last_probs = (prob_long, prob_short)
            
            # Tier 1 Bias Adjustments
            if self.whale_bias == 1:
                prob_long *= 1.1
                prob_short *= 0.9
            elif self.whale_bias == -1:
                prob_long *= 0.9
                prob_short *= 1.1
                
            if self.funding_bias == 1:
                prob_long *= 1.05
                prob_short *= 0.95
            elif self.funding_bias == -1:
                prob_long *= 0.95
                prob_short *= 1.05
                
            prob_long = min(prob_long, 1.0)
            prob_short = min(prob_short, 1.0)
            
            current_price = price_df['close'].iloc[-1]
            
            # Logic Decision
            signal_direction = None
            confidence = 0.0
            
            if regime == 'CHOP':
                return None
                
            threshold = self.current_threshold
            
            if regime == 'BULL' and prob_long > threshold and prob_long > prob_short:
                signal_direction = 'LONG'
                confidence = prob_long
            elif regime == 'BEAR' and prob_short > threshold and prob_short > prob_long:
                signal_direction = 'SHORT'
                confidence = prob_short
            
            if signal_direction:
                return {
                    'model': self.name,
                    'timestamp': datetime.now(),
                    'price': current_price,
                    'direction': signal_direction,
                    'confidence': confidence,
                    'meta': {
                        'regime': regime,
                        'whale_bias': self.whale_bias,
                        'funding_bias': self.funding_bias,
                        'raw_probs': (prob_long, prob_short)
                    }
                }
            
            return None
            
        except Exception as e:
            print(f"   ⚠️ [V2 Logic] Error: {e}")
            import traceback
            traceback.print_exc()
            return None
