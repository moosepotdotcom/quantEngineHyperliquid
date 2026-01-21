
import os
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
import sys

# Import project root utils (assuming this file is in EXPORT/V4_75WR_BACKUP/)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from utils.mtf_feature_engineer import MTFFeatureGenerator

class MTFScalperV4Logic:
    """
    Independent Logic for V4 Model (75% Win Rate Backup).
    """
    def __init__(self):
        self.name = "MTF Scalper V4 (Backup)"
        self.models_dir = os.path.join(os.path.dirname(__file__), 'weights')
        self.model_path = os.path.join(self.models_dir, 'mtf_scalper_v4.pkl')
        self.model = None
        
        self.load_model()
        
        # Confirmed V4 settings
        self.threshold = 0.80 
        
    def load_model(self):
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            print(f"   ✅ [V4 Backup] Loaded Model: {os.path.basename(self.model_path)}")
        else:
            print(f"   ❌ [V4 Backup] Model NOT FOUND at {self.model_path}")
            raise FileNotFoundError("V4 Model missing in backup folder")
            
    def analyze(self, df_5m, df_15m, df_30m):
        try:
            if self.model is None: return None
            
            # 1. Feature Engineering
            gen = MTFFeatureGenerator(df_5m, df_15m, df_30m)
            X_feat, price_df = gen.generate()
            
            # 2. Sanitization
            X_feat = X_feat.replace([np.inf, -np.inf], np.nan).fillna(0)
            
            # 3. Predict
            probs = self.model.predict_proba(X_feat.values)[0]
            prob_long = float(probs[1])
            prob_short = float(probs[2])
            
            current_price = price_df['close'].iloc[-1]
            
            direction = None
            conf = 0.0
            
            if prob_long > self.threshold and prob_long > prob_short:
                direction = "LONG"
                conf = prob_long
            elif prob_short > self.threshold and prob_short > prob_long:
                direction = "SHORT"
                conf = prob_short
                
            if direction:
                return {
                    'model': self.name,
                    'timestamp': datetime.utcnow(),
                    'price': current_price,
                    'direction': direction,
                    'confidence': conf,
                    'meta': {'backup_version': 'V4_75WR'}
                }
                
            return None
            
        except Exception as e:
            print(f"   ⚠️ [V4 Backup] Error: {e}")
            return None
