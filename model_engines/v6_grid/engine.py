
import os
import joblib
import pandas as pd
import numpy as np
from core.base_engine import BaseEngine, Signal
from utils.v5_feature_engineer import generate_v5_features

class V6GridEngine(BaseEngine):
    """
    The 'Jackpot' Engine (V6).
    
    Strategy: "Dynamic Volatility Grid"
    1. Input: V5 Features (Volume Delta, CVD, Regime Squeeze).
    2. Model: Predicts Volatility Regime (Low vs High).
    3. Execution: 
       - Low Vol (Safe) -> Place Tight Grid (+/- 0.1%).
       - High Vol (Danger) -> Neutral / Hedge.
    """
    
    def __init__(self):
        self.model = None
        self.conf_threshold = 0.50 # Optimized
        self.grid_spacing = 0.001  # 0.1% Optimized
        
    def initialize(self):
        """Loads the 84% Accuracy Volatility Model"""
        model_path = os.path.join(os.path.dirname(__file__), 'weights/vol_model.pkl')
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"V6 Model not found at {model_path}")
            
        print(f"   🎰 Loading V6 Grid Engine (Conf={self.conf_threshold}, Spacing={self.grid_spacing:.1%})...")
        self.model = joblib.load(model_path)
        
    def analyze(self, df) -> Signal:
        """
        Analyzes the latest market data to determine Grid Mode.
        """
        # 1. Feature Engineering (The "Jackpot" Features)
        # Volume Delta, CVD, Squeeze, etc.
        # We need a decent chunk of history to generate valid rolling features (e.g. 50-200 bars)
        if len(df) < 200:
             return Signal(signal_type='NEUTRAL', confidence=0.0, metadata={"reason": "Not enough data"})
             
        df_enriched = generate_v5_features(df)
        
        # 2. Prepare for Inference
        # Get latest row features
        latest_row = df_enriched.iloc[[-1]].copy()
        
        # Drop non-feature columns
        drop_cols = ['timestamp', 'target', 'open', 'high', 'low', 'close', 
                     'taker_buy_base', 'taker_sell_base', 'future_high', 'future_low', 'future_range_pct',
                     'prob_low', 'prob_high'] # Ensure these are dropped if present
                     
        features = [c for c in df_enriched.columns if c not in drop_cols]
        
        # 3. Predict Volatility
        # Class 0 = Low Volatility (Safe)
        # Class 2 = High Volatility (Danger)
        probs = self.model.predict_proba(latest_row[features])[0]
        prob_low_vol = probs[0]
        prob_high_vol = probs[2]
        
        current_price = latest_row['close'].values[0]
        
        # 4. Logic: The optimized 0.50 Threshold
        if prob_low_vol > self.conf_threshold:
            # SIGNAL: DEPLOY GRID
            # We want to place a Buy Limit below and Sell Limit above
            return Signal(
                signal_type='GRID',
                confidence=prob_low_vol,
                grid_buy_level = current_price * (1 - self.grid_spacing),
                grid_sell_level = current_price * (1 + self.grid_spacing),
                metadata={
                    "strategy": "V6_Jackpot_Grid",
                    "regime": "LOW_VOLATILITY",
                    "prob_safe": prob_low_vol,
                    "avg_vol_delta": float(latest_row['volume_delta'].iloc[0]) if 'volume_delta' in latest_row else 0.0
                }
            )
            
        elif prob_high_vol > self.conf_threshold:
            # SIGNAL: DANGER / STOP
            return Signal(
                signal_type='NEUTRAL',
                confidence=prob_high_vol,
                metadata={
                    "strategy": "V6_Jackpot_Grid",
                    "regime": "HIGH_VOLATILITY_DANGER",
                    "prob_danger": prob_high_vol
                }
            )
            
        else:
            # Indeterminate
            return Signal(
                signal_type='NEUTRAL',
                confidence=0.0,
                metadata={"reason": "Low Confidence"}
            )
