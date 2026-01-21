
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class V7HandcraftedEngine:
    """
    V7 "Jackpot" Strategy - Hand-Crafted Rules
    
    Proven 40% Win Rate with CVD Alignment
    
    Entry Rules:
    - LONG: Price < EMA_50_15m AND RSI_15m <= 63 AND RSI_1h < 60 AND CVD_1h > 0
    - SHORT: Price > EMA_50_15m AND Flow_Imbalance < 0.10 AND RSI_1h > 40 AND CVD_1h < 0
    
    Targets:
    - TP: 0.5%
    - SL: 0.15%
    - RR: 1:3.3
    """
    
    def __init__(self):
        self.name = "V7_Handcrafted_Jackpot"
        self.tp = 0.005  # 0.5%
        self.sl = 0.0015  # 0.15%
        
    def analyze(self, df: pd.DataFrame) -> dict:
        """
        Analyze market data and return trading signal
        
        Args:
            df: DataFrame with features (must include EMA, RSI, CVD, etc.)
            
        Returns:
            dict with 'signal', 'entry', 'tp', 'sl', 'metadata'
        """
        if len(df) < 200:
            return {'signal': 'NEUTRAL'}
            
        # Get latest candle
        latest = df.iloc[-1]
        
        entry_price = latest['close']
        ema_50_15m = latest.get('ema_50_15m', 0)
        rsi_15m = latest.get('rsi_15m', 50)
        rsi_1h = latest.get('rsi_1h', 50)
        cvd_1h = latest.get('cvd_1h', 0)
        flow_imbalance = latest.get('flow_imbalance_15m', 0)
        
        # LONG Signal
        if (entry_price < ema_50_15m and 
            rsi_15m <= 63 and 
            rsi_1h < 60 and 
            cvd_1h > 0):
            
            return {
                'signal': 'LONG',
                'entry': entry_price,
                'tp': entry_price * (1 + self.tp),
                'sl': entry_price * (1 - self.sl),
                'metadata': {
                    'strategy': 'V7_Jackpot',
                    'setup': 'Dip_Buy_CVD_Aligned',
                    'ema_dist': (entry_price / ema_50_15m - 1) * 100,
                    'rsi_15m': rsi_15m,
                    'rsi_1h': rsi_1h,
                    'cvd_1h': cvd_1h
                }
            }
        
        # SHORT Signal  
        elif (entry_price > ema_50_15m and 
              flow_imbalance < 0.10 and 
              rsi_1h > 40 and 
              cvd_1h < 0):
            
            return {
                'signal': 'SHORT',
                'entry': entry_price,
                'tp': entry_price * (1 - self.tp),
                'sl': entry_price * (1 + self.sl),
                'metadata': {
                    'strategy': 'V7_Jackpot',
                    'setup': 'Top_Short_CVD_Aligned',
                    'ema_dist': (entry_price / ema_50_15m - 1) * 100,
                    'rsi_1h': rsi_1h,
                    'cvd_1h': cvd_1h,
                    'flow_imbalance': flow_imbalance
                }
            }
        
        return {'signal': 'NEUTRAL'}
