
import pandas as pd
import joblib
import os
from typing import Optional, Dict

# Engine Interface
# We should preferably inherit from a BaseEngine if available, 
# but for now we follow the standalone pattern or implicit interface.

class V7JackpotEngine:
    def __init__(self, config_path: str = "config.json"):
        self.config = {
            "tp": 0.03,
            "sl": 0.005,
            "conf_threshold": 0.70,
            "ema_window": 50,
            "rsi_window": 15,
            "imbalance_threshold": 0.10
        }
        
        # Load Model
        self.model_path = os.path.join(os.path.dirname(__file__), "../v6_grid/weights/vol_model.pkl")
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            print("   ✅ V7: Loaded Volatility Model")
        else:
            print(f"   ❌ V7: Model not found at {self.model_path}")
            self.model = None
            
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Analyzes the latest market data to generate a 'JACKPOT' signal.
        """
        if self.model is None or len(df) < 200:
            return {"signal": "NEUTRAL", "confidence": 0.0}
            
        # 1. Feature Engineering (On the fly)
        # We need to replicate the exact features used by the model
        # For efficiency, we assume 'df' already has basic candles.
        # Ideally, we should reuse 'generate_v5_features', but we need to import it.
        # For this implementation, we will assume the input DF is growing and we calculate last row.
        
        # Import Helper (Assuming it's in path)
        try:
            from utils.v5_feature_engineer import generate_v5_features
            df_enriched = generate_v5_features(df)
        except ImportError:
            print("   ❌ V7: Could not import feature engineer")
            return {"signal": "NEUTRAL"}
            
        latest = df_enriched.iloc[[-1]].copy()
        
        # 2. Predict Volatility
        drop_cols_engine = ['timestamp', 'target', 'open', 'high', 'low', 'close', 
                 'taker_buy_base', 'taker_sell_base', 'future_high', 'future_low', 'future_range_pct',
                 'prob_low', 'prob_high', 'jackpot_label', 'volume_delta', 'cvd_1h', 'cvd_4h']
        
        # Note: Model expects specific columns. We rely on the fact that 
        # generate_v5_features produces the superset. We need to filter exactly.
        
        # Safe Prediction Wrapper
        try:
            # Get feature names from model if possible, else guess
            # The model is an XGBClassifier.
            req_features = self.model.get_booster().feature_names
            X = latest[req_features]
            probs = self.model.predict_proba(X)[0]
            prob_high_vol = probs[2] # Class 2
        except Exception as e:
            # Fallback if feature names mismatch
            print(f"   ⚠️ V7 Predict Error: {e}")
            return {"signal": "NEUTRAL"}
            
        # 3. Apply Decision Tree Rules
        signal_type = "NEUTRAL"
        confidence = prob_high_vol
        entry_price = float(latest['close'].iloc[0])
        trade_metadata = {}
        
        if prob_high_vol > self.config['conf_threshold']:
            # High Volatility Detected - Check Direction
            
            ema_50 = float(latest['ema_50_15m'].iloc[0])
            rsi_15m = float(latest['rsi_15m'].iloc[0])
            imbalance = float(latest['flow_imbalance_15m'].iloc[0])
            
            # LONG Rule: Price < EMA50 And RSI <= 63
            if entry_price < ema_50 and rsi_15m <= 63:
                signal_type = "LONG_JACKPOT"
                tp_price = entry_price * (1 + self.config['tp'])
                sl_price = entry_price * (1 - self.config['sl'])
                
                trade_metadata = {
                    "strategy": "V7_Jackpot_Sniper",
                    "setup": "Reversion_Pump",
                    "prob_vol": prob_high_vol,
                    "metrics": f"RSI={rsi_15m:.1f}, EMA_Dist={(entry_price/ema_50)-1:.2%}"
                }
                
                return {
                    "signal": signal_type,
                    "confidence": confidence,
                    "entry": entry_price,
                    "tp": tp_price,
                    "sl": sl_price,
                    "metadata": trade_metadata
                }
                
            # SHORT Rule: Price > EMA50 And Weak Flow
            elif entry_price > ema_50 and imbalance < self.config['imbalance_threshold']:
                signal_type = "SHORT_JACKPOT"
                tp_price = entry_price * (1 - self.config['tp'])
                sl_price = entry_price * (1 + self.config['sl'])
                
                trade_metadata = {
                    "strategy": "V7_Jackpot_Sniper",
                    "setup": "Rejection_Dump",
                    "prob_vol": prob_high_vol,
                    "metrics": f"Imbalance={imbalance:.2f}, EMA_Dist={(entry_price/ema_50)-1:.2%}"
                }
                
                return {
                    "signal": signal_type,
                    "confidence": confidence,
                    "entry": entry_price,
                    "tp": tp_price,
                    "sl": sl_price,
                    "metadata": trade_metadata
                }
                
        return {"signal": "NEUTRAL", "confidence": confidence}

