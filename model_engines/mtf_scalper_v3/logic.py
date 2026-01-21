
"""
MTF Scalper V3 (Retrained Jan 2026) - Isolated Logic
"""
import os
import sys
import joblib
import pandas as pd
import numpy as np
from datetime import datetime

# Import Utils
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from utils.mtf_feature_engineer import MTFFeatureGenerator

class MTFScalperV3Logic:
    """
    Logic for the Retrained V3 Model.
    - Uses MTFFeatureGenerator (231 features)
    - Loads 'mtf_scalper_v3.pkl' (XGBoost)
    """
    def __init__(self):
        self.name = "MTF Scalper V3"
        self.models_dir = os.path.join(os.path.dirname(__file__), 'weights')
        self.model = None
        self.load_model()
        
        # Config (Hardcoded optimization results)
        self.threshold = 0.80 # Conservative default
        self.avoid_hours = [] # No time filter for now
        
    def load_model(self):
        # Priority: V4 (2025 Retrain) -> V3 -> V2
        path_v4 = os.path.join(self.models_dir, 'mtf_scalper_v4.pkl')
        path_v3 = os.path.join(self.models_dir, 'mtf_scalper_v3.pkl')
        
        try:
            if os.path.exists(path_v4):
                self.model = joblib.load(path_v4)
                print(f"   ✅ [V3 Logic] Loaded V4 MODEL (2025 Retrain): {os.path.basename(path_v4)}")
            elif os.path.exists(path_v3):
                self.model = joblib.load(path_v3)
                print(f"   ✅ [V3 Logic] Loaded V3 MODEL: {os.path.basename(path_v3)}")
            else:
                print(f"   ❌ [V3 Logic] No Model Found (Checked V4/V3)")
        except Exception as e:
            print(f"   ❌ [V3 Logic] Load Error: {e}")
            
    def analyze(self, df_5m, df_15m, df_30m):
        """
        Main analysis function called by Engine.
        Returns signal dict or None.
        """
        try:
            if self.model is None: return None
            
            # 1. Feature Engineering
            # Important: Use same generator as training
            gen = MTFFeatureGenerator(df_5m, df_15m, df_30m)
            X_feat, price_df = gen.generate()
            
            # 2. Sanitization (Crucial for XGBoost)
            X_feat = X_feat.replace([np.inf, -np.inf], np.nan).fillna(0)
            
            # 3. Predict
            # Model is XGBClassifier, returns [prob_neutral, prob_long, prob_short]
            probs = self.model.predict_proba(X_feat.values)[0]
            prob_long = float(probs[1])
            prob_short = float(probs[2])
            
            current_price = price_df['close'].iloc[-1]
            
            # 4. Signal Generation
            direction = None
            conf = 0.0
            
            # 🛡️ REGIME SHIELD (Discovered via Analysis)
            # 1. High Confidence (Sniper): > 0.80 (Any ATR)
            # 2. Medium Confidence (Calm): > 0.50 IF ATR < 70 (Regime Filter)
            
            atr_val = price_df['atr_14'].iloc[-1]
            
            # Long Logic
            if prob_long > prob_short:
                if prob_long > 0.80:
                    direction = "LONG"
                    conf = prob_long
                elif prob_long > 0.50 and atr_val < 70:
                    print(f"   🛡️ Regime Shield: Rescued LONG (Conf {prob_long:.2f}, ATR {atr_val:.1f})")
                    direction = "LONG"
                    conf = prob_long
                    
            # Short Logic
            elif prob_short > prob_long:
                 if prob_short > 0.80:
                    direction = "SHORT"
                    conf = prob_short
                 elif prob_short > 0.50 and atr_val < 70:
                    print(f"   🛡️ Regime Shield: Rescued SHORT (Conf {prob_short:.2f}, ATR {atr_val:.1f})")
                    direction = "SHORT"
                    conf = prob_short
                
                
            if direction:
                return {
                    'model': self.name,
                    'timestamp': datetime.utcnow(),
                    'price': current_price,
                    'direction': direction,
                    'confidence': conf,
                    'meta': {
                        'raw_probs': (prob_long, prob_short),
                        'concurrent_allowed': True # Flag for MainConnector
                    }
                }
                
            return None
            
        except Exception as e:
            print(f"   ⚠️ [V3 Logic] Error: {e}")
            import traceback
            traceback.print_exc()
            return None
