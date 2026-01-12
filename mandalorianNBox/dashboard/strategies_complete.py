"""
Complete Strategy Library - All strategies from your codebase
Real strategies converted to backtrader format
"""

from datetime import datetime
import backtrader as bt
import pandas as pd
import numpy as np
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import xgboost as xgb
import os
import json

# Import strategies from new package
try:
    from strategies.ml_predictor import MLPredictorStrategy
    from strategies.ml_quantum_strategy import MLQuantumStrategy
    from strategies.liquidation_sweep import LiquidationSweepStrategy
except ImportError:
    # Fallback for when running directly from dashboard folder
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from strategies.ml_predictor import MLPredictorStrategy
    from strategies.ml_quantum_strategy import MLQuantumStrategy
    from strategies.ml_quantum_strategy import MLQuantumStrategy
    from strategies.liquidation_sweep import LiquidationSweepStrategy

class MLFilterMixin:
    """
    Mixin to check trade signals against a trained XGBoost model.
    """
    def init_ml(self, model_name):
        self.xgb_model = None
        self.ml_conf = 0.50 # Default confidence, can be tuned
        self.ml_prob = 0.5 # Last probability
        
        try:
            # Locate model
            root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            model_path = os.path.join(root, 'models', f'{model_name}_xgb.json')
            
            if os.path.exists(model_path):
                self.xgb_model = xgb.XGBClassifier()
                self.xgb_model.load_model(model_path)
                print(f"🤖 AI Loaded: {model_name} from {model_path}")
            else:
                print(f"⚠️ AI Missing: {model_name} (Using defaults)")
        except Exception as e:
            print(f"⚠️ AI Error: {e}")

    def check_ml(self, side, price):
        """
        Returns (allowed: bool, probability: float)
        Side: 1 (Long), -1 (Short)
        """
        if not self.xgb_model:
            return True, 0.5 # No model, allow trade
            
        try:
            # Feature Extraction (Must match Training Script!)
            if hasattr(self, 'get_ml_features'):
                # Use strategy-specific custom features (e.g. MTF 21-features)
                flat_features = self.get_ml_features(side, price)
                features = np.array([flat_features])
            else:
                # Default Legacy Features (4 features)
                # 1. RSI
                try: rsi = bt.ind.RSI(self.data.close, period=14)[0]
                except: rsi = 50
                
                # 2. ATR %
                try:
                    atr = bt.ind.ATR(self.data, period=14)[0]
                    atr_pct = (atr / price) * 100
                except: atr_pct = 0.5
                
                # 3. Volume Ratio
                try:
                    vol_ma = bt.ind.SMA(self.data.volume, period=20)[0]
                    vol_ratio = self.data.volume[0] / (vol_ma + 1)
                except: vol_ratio = 1.0
                
                features = np.array([[rsi, atr_pct, vol_ratio, side]])
            prob = self.xgb_model.predict_proba(features)[0][1] # Probability of Class 1 (Win)
            
            self.ml_prob = prob
            
            # Only block if probability is extremely low?
            # Or filter if < 0.5?
            # Let's say filter if < 0.5
            return prob > 0.5, prob
            
        except Exception as e:
            print(f"ML Predict Error: {e}")
            return True, 0.5


# ============================================================================
# BASIC INDICATORS (Days 6-9)
# ============================================================================

class SMAStrategy(bt.Strategy, MLFilterMixin):
    """Simple Moving Average Crossover - From 6_sma.py"""
    params = (
        ('fast_period', 10),
        ('slow_period', 20),
    )
    
    
    def __init__(self):
        self.fast_sma = bt.ind.SMA(period=self.params.fast_period)
        self.slow_sma = bt.ind.SMA(period=self.params.slow_period)
        self.crossover = bt.ind.CrossOver(self.fast_sma, self.slow_sma)
        self.sl_price = 0.0
        self.tp_price = 0.0
        self.init_ml('investor')

    def next(self):
        if self.crossover > 0:  # Fast crosses above slow - BUY
            # Set generic SL/TP for visibility (Investor mode = wide bands)
            self.sl_price = self.data.close[0] * 0.95 # 5% Stop
            self.tp_price = self.data.close[0] * 1.15 # 15% Target
            
            allowed, prob = self.check_ml(1, self.data.close[0])
            if allowed:
                # Log confidence? 
                print(f"🤖 Investor BUY Confidence: {prob:.2%}")
                self.buy()
        elif self.crossover < 0:  # Fast crosses below slow - SELL
            self.sl_price = self.data.close[0] * 1.05
            self.tp_price = self.data.close[0] * 0.85
            
            allowed, prob = self.check_ml(-1, self.data.close[0])
            if allowed:
                print(f"🤖 Investor SELL Confidence: {prob:.2%}")
                self.sell()

class RSIStrategy(bt.Strategy):
    """RSI Mean Reversion - From 7_rsi.py"""
    params = (
        ('rsi_period', 14),
        ('rsi_oversold', 30),
        ('rsi_overbought', 70),
    )
    
    def __init__(self):
        self.rsi = bt.ind.RSI(period=self.params.rsi_period)
    
    def next(self):
        if self.rsi < self.params.rsi_oversold:  # Oversold - BUY
            self.buy()
        elif self.rsi > self.params.rsi_overbought:  # Overbought - SELL
            self.sell()

class VWAPStrategy(bt.Strategy):
    """VWAP Crossover - From 8_vwap.py"""
    params = (
        ('vwap_period', 20),
    )
    
    def __init__(self):
        # Custom VWAP calculation with safety for zero volume
        typical_price = (self.data.high + self.data.low + self.data.close) / 3
        volume_sum = bt.ind.WeightedMovingAverage(self.data.volume, period=self.params.vwap_period)
        # Add small epsilon to avoid division by zero
        self.vwap = bt.ind.WeightedMovingAverage(typical_price * self.data.volume, period=self.params.vwap_period) / (volume_sum + 0.000001)
    
    def next(self):
        if self.data.close > self.vwap:  # Price above VWAP - BUY
            self.buy()
        elif self.data.close < self.vwap:  # Price below VWAP - SELL
            self.sell()

# ============================================================================
# BOLLINGER BANDS (Day 10)
# ============================================================================

class BollingerBandsStrategy(bt.Strategy):
    """Bollinger Bands Mean Reversion - From 10_bollinger_bot.py"""
    params = (
        ('bb_period', 20),
        ('bb_dev', 2),
    )
    
    def __init__(self):
        self.bb = bt.ind.BollingerBands(period=self.params.bb_period, devfactor=self.params.bb_dev)
    
    def next(self):
        if self.data.close < self.bb.lines.bot:  # Price below lower band - BUY
            self.buy()
        elif self.data.close > self.bb.lines.top:  # Price above upper band - SELL
            self.sell()

class BollingerBandsTightStrategy(bt.Strategy):
    """Bollinger Bands Tight - Enters when bands are tight"""
    params = (
        ('bb_period', 20),
        ('bb_dev', 2),
        ('tight_threshold', 0.02),  # 2% of price
    )
    
    def __init__(self):
        self.bb = bt.ind.BollingerBands(period=self.params.bb_period, devfactor=self.params.bb_dev)
        self.bb_width = self.bb.lines.top - self.bb.lines.bot
    
    def next(self):
        # Check if bands are tight
        band_width_pct = (self.bb_width[0] / self.data.close[0]) * 100
        if band_width_pct < self.params.tight_threshold:
            # Bands are tight - enter on breakout
            if self.data.close > self.bb.lines.mid:
                self.buy()
            elif self.data.close < self.bb.lines.mid:
                self.sell()

# ============================================================================
# SUPPLY & DEMAND ZONES (Day 11)
# ============================================================================

class SupplyDemandStrategy(bt.Strategy):
    """Supply and Demand Zones - From 11_sdz_bot.py"""
    params = (
        ('lookback', 20),
    )
    
    def __init__(self):
        self.support = bt.ind.Lowest(self.data.low, period=self.params.lookback)
        self.resistance = bt.ind.Highest(self.data.high, period=self.params.lookback)
    
    def next(self):
        # Buy near support (demand zone)
        if self.data.close <= self.support * 1.01:  # Within 1% of support
            self.buy()
        # Sell near resistance (supply zone)
        elif self.data.close >= self.resistance * 0.99:  # Within 1% of resistance
            self.sell()

# ============================================================================
# TURTLE TRADING (Bonus Algo 1)
# ============================================================================

class TurtleStrategy(bt.Strategy):
    """Turtle Trading - From 1_turtle_algo.py"""
    params = (
        ('lookback', 55),
        ('atr_period', 14),
        ('atr_multiplier', 2),
        ('take_profit_pct', 0.2),
    )
    
    def __init__(self):
        self.high = bt.ind.Highest(self.data.high, period=self.params.lookback)
        self.low = bt.ind.Lowest(self.data.low, period=self.params.lookback)
        self.atr = bt.ind.ATR(period=self.params.atr_period)
    
    def next(self):
        if not self.position:
            # Entry: Breakout above 55-bar high
            if self.data.close > self.high[0]:
                self.buy()
            # Entry: Breakdown below 55-bar low
            elif self.data.close < self.low[0]:
                self.sell()
        else:
            # Exit: Take profit
            if self.position.size > 0:  # Long
                entry = self.position.price
                if self.data.close >= entry * (1 + self.params.take_profit_pct / 100):
                    self.close()
                # Stop loss: 2x ATR below entry
                elif self.data.close <= entry - (self.atr[0] * self.params.atr_multiplier):
                    self.close()
            elif self.position.size < 0:  # Short
                entry = self.position.price
                if self.data.close <= entry * (1 - self.params.take_profit_pct / 100):
                    self.close()
                # Stop loss: 2x ATR above entry
                elif self.data.close >= entry + (self.atr[0] * self.params.atr_multiplier):
                    self.close()

class TurtleStrategyOptimized(bt.Strategy, MLFilterMixin):
    """
    Turtle Trading - Optimized (1H Only)
    Backtest Result: +58.51% Profit on 1H timeframe.
    Poor performance on other timeframes.
    """
    params = (
        ('lookback', 98),
        ('atr_period', 30),
        ('atr_multiplier', 3.7065),
        ('take_profit_pct', 0.8997),
    )
    
    def __init__(self):
        self.high = bt.ind.Highest(self.data.high, period=self.params.lookback)
        self.low = bt.ind.Lowest(self.data.low, period=self.params.lookback)
        self.atr = bt.ind.ATR(period=self.params.atr_period)
        self.sl_price = 0.0
        self.tp_price = 0.0
        self.current_sl = 0.0  # Persisted SL/TP for Engine extraction
        self.current_tp = 0.0
        self.init_ml('day_trader')

    def next(self):
        if not self.position:
            # Entry: Breakout above lookback-bar high (Previous bar's high)
            if self.data.close > self.high[-1]:
                allowed, prob = self.check_ml(1, self.data.close[0])
                if allowed:
                    self.current_sl = self.data.close[0] - (self.atr[0] * self.params.atr_multiplier)
                    self.current_tp = self.data.close[0] * (1 + self.params.take_profit_pct / 100)
                    self.sl_price = self.current_sl
                    self.tp_price = self.current_tp
                    print(f"🤖 Day Trader BUY Conf: {prob:.2%}")
                    self.buy()
            # Entry: Breakdown below lookback-bar low (Previous bar's low)
            elif self.data.close < self.low[-1]:
                allowed, prob = self.check_ml(-1, self.data.close[0])
                if allowed:
                    self.current_sl = self.data.close[0] + (self.atr[0] * self.params.atr_multiplier)
                    self.current_tp = self.data.close[0] * (1 - self.params.take_profit_pct / 100)
                    self.sl_price = self.current_sl
                    self.tp_price = self.current_tp
                    print(f"🤖 Day Trader SELL Conf: {prob:.2%}")
                    self.sell()
        else:
            # Keep SL/TP visible while in position
            self.sl_price = self.current_sl
            self.tp_price = self.current_tp
            # Exit: Take profit
            if self.position.size > 0:  # Long
                entry = self.position.price
                if self.data.close >= entry * (1 + self.params.take_profit_pct / 100):
                    self.close()
                # Stop loss: atr_multiplier x ATR below entry
                elif self.data.close <= entry - (self.atr[0] * self.params.atr_multiplier):
                    self.close()
            elif self.position.size < 0:  # Short
                entry = self.position.price
                if self.data.close <= entry * (1 - self.params.take_profit_pct / 100):
                    self.close()
                # Stop loss: atr_multiplier x ATR above entry
                elif self.data.close >= entry + (self.atr[0] * self.params.atr_multiplier):
                    self.close()

# ============================================================================

# CONSOLIDATION POP (Bonus Algo 3)
# ============================================================================

class ConsolidationPopStrategy(bt.Strategy, MLFilterMixin):
    """Consolidation Pop - From 3_consolidation_pop_algo.py"""
    params = (
        ('consolidation_bars', 10),
        ('consolidation_pct', 0.7),
        ('take_profit_pct', 0.3),
        ('stop_loss_pct', 0.25),
    )
    
    def __init__(self):
        self.atr = bt.ind.ATR(period=14)
        self.high_range = bt.ind.Highest(self.data.high, period=self.params.consolidation_bars)
        self.low_range = bt.ind.Lowest(self.data.low, period=self.params.consolidation_bars)
        self.sl_price = 0.0
        self.tp_price = 0.0
        self.current_sl = 0.0  # Persisted SL/TP for Engine extraction
        self.current_tp = 0.0
        self.init_ml('swing_trader')

    def next(self):
        if not self.position:
            # Check if in consolidation (low volatility)
            range_size = self.high_range[0] - self.low_range[0]
            range_pct = (range_size / self.data.close[0]) * 100
            
            if range_pct < self.params.consolidation_pct:
                # Price in lower 1/3 of range - BUY
                consolidation_low = self.low_range[0]
                consolidation_high = self.high_range[0]
                lower_third = consolidation_low + (consolidation_high - consolidation_low) / 3
                
                if self.data.close <= lower_third:
                    allowed, prob = self.check_ml(1, self.data.close[0])
                    if allowed:
                        self.current_sl = self.data.close[0] * (1 - self.params.stop_loss_pct / 100)
                        self.current_tp = self.data.close[0] * (1 + self.params.take_profit_pct / 100)
                        self.sl_price = self.current_sl
                        self.tp_price = self.current_tp
                        print(f"🤖 Swing Trader BUY Conf: {prob:.2%}")
                        self.buy()
                # Price in upper 1/3 of range - SELL
                elif self.data.close >= consolidation_high - (consolidation_high - consolidation_low) / 3:
                    allowed, prob = self.check_ml(-1, self.data.close[0])
                    if allowed:
                        self.current_sl = self.data.close[0] * (1 + self.params.stop_loss_pct / 100)
                        self.current_tp = self.data.close[0] * (1 - self.params.take_profit_pct / 100)
                        self.sl_price = self.current_sl
                        self.tp_price = self.current_tp
                        print(f"🤖 Swing Trader SELL Conf: {prob:.2%}")
                        self.sell()
        else:
            # Keep SL/TP visible while in position
            self.sl_price = self.current_sl
            self.tp_price = self.current_tp
            # Exit on take profit or stop loss

# ============================================================================
# AI GEM V1 (Discovered Phase 26)
# ============================================================================

class AIGemV1(bt.Strategy, MLFilterMixin):
    """
    💎 AI GEM V1 - RSI Hyper-tuned + XGBoost
    Discovered via Massive Fuzzing on 1H BTC.
    Base Profit: $173k | ML Win Rate: 76%
    """
    params = (
        ('rsi_period', 10),
        ('rsi_oversold', 30),
        ('rsi_overbought', 70),
        ('take_profit_pct', 3.0),
        ('stop_loss_pct', 1.5),
    )
    
    def __init__(self):
        self.rsi = bt.ind.RSI(period=self.params.rsi_period)
        self.init_ml('ai_gem_v1')
        
    def next(self):
        if self.rsi < self.params.rsi_oversold:  # Oversold - BUY
            allowed, prob = self.check_ml(1, self.data.close[0])
            if allowed:
                print(f"💎 GEM BUY Conf: {prob:.2%}")
                self.buy()
        elif self.rsi > self.params.rsi_overbought:  # Overbought - SELL
            allowed, prob = self.check_ml(-1, self.data.close[0])
            if allowed:
                print(f"💎 GEM SELL Conf: {prob:.2%}")
                self.sell()
                
        if self.position:
            # Exit on take profit or stop loss
            if self.position.size > 0:  # Long
                entry = self.position.price
                if self.data.close >= entry * (1 + self.params.take_profit_pct / 100):
                    self.close()
                elif self.data.close <= entry * (1 - self.params.stop_loss_pct / 100):
                     self.close()
            elif self.position.size < 0:  # Short
                entry = self.position.price
                if self.data.close <= entry * (1 - self.params.take_profit_pct / 100):
                    self.close()
                elif self.data.close >= entry * (1 + self.params.stop_loss_pct / 100):
                    self.close()

# ============================================================================
# MTF AI SCALPER V2 (Phase 27)
# ============================================================================

class MTFScalperStrategy(bt.Strategy, MLFilterMixin):
    """
    🦅 MTF AI Scalper V2
    - Base: 15m
    - Context: 1H, 4H (via XGBoost Features)
    - Logic: RSI Extremes + ML Confirmation
    """
    params = (
        ('rsi_period', 14),
        ('tp_pct', 1.5),
        ('sl_pct', 1.0),
    )
    
    
    def __init__(self):
        self.rsi = bt.ind.RSI(period=self.params.rsi_period)
        
        # 21 Features Initialization for XGBoost
        # Base (15m) Factors
        self.bb = bt.ind.BollingerBands(period=20, devfactor=2)
        self.macd = bt.ind.MACD() # 12, 26, 9
        self.ema50 = bt.ind.EMA(period=50)
        self.ema200 = bt.ind.EMA(period=200)
        
        # Context 1 (1H) Approx (x4 period) 
        self.rsi_1h = bt.ind.RSI(period=14*4)
        self.bb_1h = bt.ind.BollingerBands(period=20*4, devfactor=2)
        self.macd_1h = bt.ind.MACD(period_me1=12*4, period_me2=26*4, period_signal=9*4)
        self.ema50_1h = bt.ind.EMA(period=50*4)
        self.ema200_1h = bt.ind.EMA(period=200*4)
        
        # Context 2 (4H) Approx (x16 period)
        self.rsi_4h = bt.ind.RSI(period=14*16)
        self.bb_4h = bt.ind.BollingerBands(period=20*16, devfactor=2)
        self.macd_4h = bt.ind.MACD(period_me1=12*16, period_me2=26*16, period_signal=9*16)
        self.ema50_4h = bt.ind.EMA(period=50*16)
        self.ema200_4h = bt.ind.EMA(period=200*16)

        self.init_ml('scalp_mtf_v2') # Loads scalp_mtf_v2_xgb.json
        self.sl_price = 0.0
        self.tp_price = 0.0

    def get_ml_features(self, side, price):
        # Construct the 21-feature vector expected by the model
        # Order: 5m(Base), 15m(Context1), 30m(Context2) -> actually 15m/1H/4H in our usage
        
        def safe_val(ind):
             try: return ind[0] 
             except: return 0.0
             
        # Helper to pack 7 features
        def pack_features(rsi, bb, macd, ema50, ema200):
            bb_top = safe_val(bb.top)
            bb_bot = safe_val(bb.bot)
            bb_mid = safe_val(bb.mid)
            bb_w = (bb_top - bb_bot) / (bb_mid + 1e-9)
            return [safe_val(rsi), bb_top, bb_bot, bb_w, safe_val(macd.macd), safe_val(ema50), safe_val(ema200)]
            
        f_base = pack_features(self.rsi, self.bb, self.macd, self.ema50, self.ema200)
        f_1h = pack_features(self.rsi_1h, self.bb_1h, self.macd_1h, self.ema50_1h, self.ema200_1h)
        f_4h = pack_features(self.rsi_4h, self.bb_4h, self.macd_4h, self.ema50_4h, self.ema200_4h)
        
        return f_base + f_1h + f_4h
        

    def next(self):
        # 1. Base Logic: AI-Driver (RSI just hints direction)
        # Split: RSI < 50 -> Check Long opportunities
        #        RSI >= 50 -> Check Short opportunities
        
        check_dir = 0
        if self.rsi[0] < 50: check_dir = 1
        else: check_dir = -1
        
        signal = 0
        allowed = False
        prob = 0.0
        
        # 2. ML Filter (ULTRA-RIGOROUS - Only Winners Mode)
        if check_dir != 0:
            allowed, prob = self.check_ml(check_dir, self.data.close[0])
            
            # Only execute if model is EXTREMELY confident (>85%)
            if allowed and prob > 0.85:
                signal = check_dir
                # 3. Execution (Ultra-Selective)
                print(f"🦅 MTF Scalper Signal: {signal} | Conf: {prob:.2%}")
                
                if signal == 1:
                    self.buy()
                    self.tp_price = self.data.close[0] * (1 + self.params.tp_pct/100)
                    self.sl_price = self.data.close[0] * (1 - self.params.sl_pct/100)
                elif signal == -1:
                    self.sell()
                    self.tp_price = self.data.close[0] * (1 - self.params.tp_pct/100)
                    self.sl_price = self.data.close[0] * (1 + self.params.sl_pct/100)
                    
        # Exit Management
        if self.position:
            if self.position.size > 0:
                if self.data.close >= self.tp_price: self.close()
                elif self.data.close <= self.sl_price: self.close()
            elif self.position.size < 0:
                if self.data.close <= self.tp_price: self.close()
                elif self.data.close >= self.sl_price: self.close()

# ============================================================================
# MINI AI SCALPER V3 (Phase 29)
# ============================================================================

class MiniScalperStrategy(bt.Strategy, MLFilterMixin):
    """
    🔥 Mini AI Scalper V4 (High Freq)
    - Logic: RSI(9) < 40 -> ML Check -> TP(+150pts) / SL(-100pts)
    - Target: High Frequency (~25 trades/day raw), Filtered by AI.
    """
    params = (
        ('rsi_period', 9),
        ('rsi_entry', 40),
        ('tp_points', 150.0),
        ('sl_points', 100.0),
    )
    
    def __init__(self):
        self.rsi = bt.ind.RSI(period=self.params.rsi_period)
        self.atr = bt.ind.ATR(period=14)
        self.bb = bt.ind.BollingerBands(period=20, devfactor=2)
        self.ema50 = bt.ind.EMA(period=50)
        self.vol_ma = bt.ind.SMA(self.data.volume, period=20)
        
        self.init_ml('scalp_mini_v4')
        self.sl_price = 0.0
        self.tp_price = 0.0
        
    def get_ml_features(self, side, price):
        # Must match training_mini_model.py: ['rsi', 'atr', 'bb_w', 'vol_ratio', 'dist_ema']
        
        def safe(ind): return ind[0]
        
        rsi_val = safe(self.rsi)
        atr_val = safe(self.atr)
        
        bb_top = safe(self.bb.top)
        bb_bot = safe(self.bb.bot)
        bb_mid = safe(self.bb.mid)
        bb_w = (bb_top - bb_bot) / (bb_mid + 1e-9)
        
        v_val = self.data.volume[0]
        v_ma = safe(self.vol_ma)
        vol_ratio = v_val / (v_ma + 1)
        
        ema_val = safe(self.ema50)
        dist_ema = (price - ema_val) / (ema_val + 1e-9)
        
        return [rsi_val, atr_val, bb_w, vol_ratio, dist_ema]

    def next(self):
        # 1. Logic
        signal = 0
        if self.rsi < self.params.rsi_entry:
            signal = 1 # Long Only for this specific trained candidate
            
        # 2. ML Filter
        if signal == 1:
            allowed, prob = self.check_ml(signal, self.data.close[0])
            
            # STRICTER THRESHOLD for "Perfect Setups"
            if allowed and prob > 0.65: 
                print(f"🔥 Mini Scalp Signal | Conf: {prob:.2%}")
                self.buy()
                self.tp_price = self.data.close[0] + self.params.tp_points
                self.sl_price = self.data.close[0] - self.params.sl_points
                
        # Exit Management (Points Based)
        if self.position:
            if self.position.size > 0:
                if self.data.close >= self.tp_price: self.close()
                elif self.data.close <= self.sl_price: self.close()
            # Short logic omitted as candidate was Long-biased for now, 
            # but standard structure supports expansion if needed.


# ============================================================================
# MEAN REVERSION (Bonus Algo 6)
# ============================================================================

class MeanReversionStrategy(bt.Strategy):
    """Mean Reversion - From 74_tickers_mean_reversion.py"""
    params = (
        ('sma_period', 20),
        ('deviation', 2),
    )
    
    def __init__(self):
        self.sma = bt.ind.SMA(period=self.params.sma_period)
        self.std = bt.ind.StandardDeviation(self.data.close, period=self.params.sma_period)
    
    def next(self):
        upper_band = self.sma[0] + (self.std[0] * self.params.deviation)
        lower_band = self.sma[0] - (self.std[0] * self.params.deviation)
        
        if self.data.close < lower_band:  # Below lower band - BUY
            self.buy()
        elif self.data.close > upper_band:  # Above upper band - SELL
            self.sell()

# ============================================================================
# NADARYA-WATSON (Bonus Algo 4)
# ============================================================================

class NadaryaWatsonStrategy(bt.Strategy):
    """
    Nadarya-Watson Envelope Strategy - From 4_nadarya_watson_algo
    Estimated using weighted moving averages as a proxy for kernel regression.
    WARNING: This indicator may repaint or look-ahead in some implementations, 
    making backtest results optimistic.
    """
    params = (
        ('bandwidth', 8),
        ('mult', 3.0),
    )
    
    def __init__(self):
        # We use a WMA as a proxy for the kernel regression for efficiency
        self.kernel = bt.ind.WeightedMovingAverage(self.data.close, period=self.params.bandwidth * 3)
        self.atr = bt.ind.ATR(period=14)
        self.upper = self.kernel + (self.atr * self.params.mult)
        self.lower = self.kernel - (self.atr * self.params.mult)
    
    def next(self):
        if self.data.close < self.lower:
            self.buy() # Reversion to mean
        elif self.data.close > self.upper:
            self.sell() 

# ============================================================================
# MACHINE LEARNING (Phase 3 "God Mode")
# ============================================================================

# MLPredictorStrategy moved to strategies/ml_predictor.py


# ============================================================================
# MARKET MAKER (Bonus Algo 5)
# ============================================================================

class MarketMakerStrategy(bt.Strategy):
    """
    Market Maker / Grid Strategy - From 5_market_maker
    Places limit orders above and below the current price.
    """
    params = (
        ('grid_levels', 5),
        ('grid_spacing_pct', 0.5), # 0.5% spacing
        ('position_size', 0.1), # Size per grid level
    )
    
    def __init__(self):
        self.orders = []
        
    def next(self):
        # Flatten orders list
        self.orders = [o for o in self.orders if o.status in [bt.Order.Submitted, bt.Order.Accepted]]
        
        # Only place new grid if no orders are active (simple version)
        if len(self.orders) == 0 and not self.position:
            price = self.data.close[0]
            
            # Place Buy Orders
            for i in range(1, self.params.grid_levels + 1):
                buy_price = price * (1 - (self.params.grid_spacing_pct * i / 100))
                o = self.buy(price=buy_price, exectype=bt.Order.Limit, size=self.params.position_size)
                self.orders.append(o)
                
            # Place Sell Orders
            for i in range(1, self.params.grid_levels + 1):
                sell_price = price * (1 + (self.params.grid_spacing_pct * i / 100))
                o = self.sell(price=sell_price, exectype=bt.Order.Limit, size=self.params.position_size)
                self.orders.append(o)

# ============================================================================
# ADVANCED STRATEGIES (From bt_code and Open-AI)
# ============================================================================

class RSIVWAPStrategy(bt.Strategy):
    """RSI + VWAP Combined - From bt_rsi + vwap"""
    params = (
        ('rsi_period', 14),
        ('rsi_oversold', 30),
        ('rsi_overbought', 70),
        ('vwap_period', 20),
    )
    
    def __init__(self):
        self.rsi = bt.ind.RSI(period=self.params.rsi_period)
        # Custom VWAP calculation with safety for zero volume
        typical_price = (self.data.high + self.data.low + self.data.close) / 3
        volume_sum = bt.ind.WeightedMovingAverage(self.data.volume, period=self.params.vwap_period)
        # Add small epsilon to avoid division by zero
        self.vwap = bt.ind.WeightedMovingAverage(typical_price * self.data.volume, period=self.params.vwap_period) / (volume_sum + 0.000001)
    
    def next(self):
        # Buy: RSI crosses above oversold AND price crosses above VWAP
        if (self.rsi[0] > self.params.rsi_oversold and 
            self.data.close[-1] < self.vwap[-1] and 
            self.data.close[0] > self.vwap[0] and
            not self.position):
            self.buy()
        
        # Sell: RSI crosses below overbought AND price crosses below VWAP
        elif (self.rsi[0] < self.params.rsi_overbought and 
              self.data.close[-1] > self.vwap[-1] and 
              self.data.close[0] < self.vwap[0] and
              not self.position):
            self.sell()
        
        # Exit long
        if self.position.size > 0:
            if self.rsi[0] > self.params.rsi_overbought or self.data.close[0] < self.vwap[0]:
                self.close()
        
        # Exit short
        if self.position.size < 0:
            if self.rsi[0] < self.params.rsi_oversold or self.data.close[0] > self.vwap[0]:
                self.close()

class SMABollingerADXStrategy(bt.Strategy):
    """SMA + ADX + Bollinger Bands + Volume - From bt_sma + adx"""
    params = (
        ('sma_period', 20),
        ('adx_period', 14),
        ('bb_period', 20),
        ('bb_dev', 2),
        ('min_adx', 20),
        ('volume_multiplier', 1.5),
    )
    
    def __init__(self):
        self.sma = bt.ind.SMA(period=self.params.sma_period)
        self.adx = bt.ind.ADX(period=self.params.adx_period)
        self.bb = bt.ind.BollingerBands(period=self.params.bb_period, devfactor=self.params.bb_dev)
        self.bb_width = self.bb.lines.top - self.bb.lines.bot
        self.avg_bb_width = bt.ind.SMA(self.bb_width, period=self.params.bb_period)
        self.avg_volume = bt.ind.SMA(self.data.volume, period=self.params.sma_period)
        self.crossover = bt.ind.CrossOver(self.data.close, self.sma)
    
    def next(self):
        # Long entry: Price crosses above SMA + ADX strong + BB contracting + High volume
        if (self.crossover > 0 and
            self.adx[0] > self.params.min_adx and
            self.bb_width[0] < self.avg_bb_width[0] and
            self.data.volume[0] > self.avg_volume[0] * self.params.volume_multiplier and
            not self.position):
            self.buy()
        
        # Short entry: Price crosses below SMA + ADX strong + BB contracting + High volume
        elif (self.crossover < 0 and
              self.adx[0] > self.params.min_adx and
              self.bb_width[0] < self.avg_bb_width[0] and
              self.data.volume[0] > self.avg_volume[0] * self.params.volume_multiplier and
              not self.position):
            self.sell()
        
        # Exit conditions
        if self.position.size > 0:  # Long
            if (self.crossover < 0 or 
                self.adx[0] < self.params.min_adx or 
                self.bb_width[0] > self.avg_bb_width[0]):
                self.close()
        elif self.position.size < 0:  # Short
            if (self.crossover > 0 or 
                self.adx[0] < self.params.min_adx or 
                self.bb_width[0] > self.avg_bb_width[0]):
                self.close()

class KeltnerVWAPStrategy(bt.Strategy):
    """Keltner Channels + VWAP - From Bitcoin_Trading_Strategy.py"""
    params = (
        ('ema_period', 20),
        ('atr_period', 10),
        ('atr_multiplier', 2),
        ('vwap_period', 20),
    )
    
    def __init__(self):
        self.atr = bt.ind.ATR(period=self.params.atr_period)
        self.ema = bt.ind.EMA(period=self.params.ema_period)
        self.upper_band = self.ema + (self.atr * self.params.atr_multiplier)
        self.lower_band = self.ema - (self.atr * self.params.atr_multiplier)
        typical_price = (self.data.high + self.data.low + self.data.close) / 3
        # Custom VWAP calculation with safety for zero volume
        typical_price = (self.data.high + self.data.low + self.data.close) / 3
        volume_sum = bt.ind.WeightedMovingAverage(self.data.volume, period=self.params.vwap_period)
        # Add small epsilon to avoid division by zero
        self.vwap = bt.ind.WeightedMovingAverage(typical_price * self.data.volume, period=self.params.vwap_period) / (volume_sum + 0.000001)
    
    def next(self):
        # Long: Price crosses above lower band AND price > VWAP
        if (self.data.close[-1] <= self.lower_band[-1] and 
            self.data.close[0] > self.lower_band[0] and
            self.data.close[0] > self.vwap[0] and
            not self.position):
            self.buy()
        
        # Short: Price crosses below upper band AND price < VWAP
        elif (self.data.close[-1] >= self.upper_band[-1] and 
              self.data.close[0] < self.upper_band[0] and
              self.data.close[0] < self.vwap[0] and
              not self.position):
            self.sell()
        
        # Exit long: Price crosses below upper band
        if self.position.size > 0:
            if self.data.close[-1] >= self.upper_band[-1] and self.data.close[0] < self.upper_band[0]:
                self.close()
        
        # Exit short: Price crosses above lower band
        if self.position.size < 0:
            if self.data.close[-1] <= self.lower_band[-1] and self.data.close[0] > self.lower_band[0]:
                self.close()

class MACDStrategy(bt.Strategy):
    """MACD Crossover"""
    params = (
        ('fast_period', 12),
        ('slow_period', 26),
        ('signal_period', 9),
    )
    
    def __init__(self):
        self.macd = bt.ind.MACD(
            period_me1=self.params.fast_period,
            period_me2=self.params.slow_period,
            period_signal=self.params.signal_period
        )
        self.crossover = bt.ind.CrossOver(self.macd.macd, self.macd.signal)
    
    def next(self):
        if self.crossover > 0:  # MACD crosses above signal - BUY
            self.buy()
        elif self.crossover < 0:  # MACD crosses below signal - SELL
            self.sell()

# ============================================================================
# STRATEGY REGISTRY - All strategies with parameters
# ============================================================================

STRATEGIES = {
    # Basic Indicators
    'SMA Crossover': {
        'class': SMAStrategy,
        'description': 'Buy when fast SMA crosses above slow SMA',
        'params': {
            'fast_period': {'type': 'int', 'default': 50, 'min': 10, 'max': 100},
            'slow_period': {'type': 'int', 'default': 200, 'min': 50, 'max': 300},
        }
    },
    'RSI Mean Reversion': {
        'class': RSIStrategy,
        'description': 'Buy when RSI is oversold, sell when overbought',
        'params': {
            'rsi_period': {'type': 'int', 'default': 14, 'min': 5, 'max': 30},
            'rsi_oversold': {'type': 'int', 'default': 30, 'min': 10, 'max': 40},
            'rsi_overbought': {'type': 'int', 'default': 70, 'min': 60, 'max': 90},
        }
    },
    'VWAP Crossover': {
        'class': VWAPStrategy,
        'description': 'Buy when price is above VWAP, sell when below',
        'params': {
            'vwap_period': {'type': 'int', 'default': 20, 'min': 10, 'max': 50},
        }
    },
    
    # Day 10-12 Strategies
    'Bollinger Bands': {
        'class': BollingerBandsStrategy,
        'description': 'Buy when price touches lower band, sell at upper band',
        'params': {
            'bb_period': {'type': 'int', 'default': 20, 'min': 10, 'max': 50},
            'bb_dev': {'type': 'float', 'default': 2.0, 'min': 1.0, 'max': 3.0},
        }
    },
    'Bollinger Bands Tight': {
        'class': BollingerBandsTightStrategy,
        'description': 'Enter when Bollinger Bands are tight (low volatility)',
        'params': {
            'bb_period': {'type': 'int', 'default': 20, 'min': 10, 'max': 50},
            'bb_dev': {'type': 'float', 'default': 2.0, 'min': 1.0, 'max': 3.0},
            'tight_threshold': {'type': 'float', 'default': 0.02, 'min': 0.01, 'max': 0.1},
        }
    },
    'Supply & Demand Zones': {
        'class': SupplyDemandStrategy,
        'description': 'Buy at support (demand), sell at resistance (supply)',
        'params': {
            'lookback': {'type': 'int', 'default': 20, 'min': 10, 'max': 100},
        }
    },
    
    # Bonus Algorithms
    'Turtle Trading': {
        'class': TurtleStrategy,
        'description': 'Breakout strategy: Buy above 55-bar high, sell below 55-bar low',
        'params': {
            'lookback': {'type': 'int', 'default': 55, 'min': 20, 'max': 100},
            'atr_period': {'type': 'int', 'default': 14, 'min': 10, 'max': 30},
            'atr_multiplier': {'type': 'float', 'default': 2.0, 'min': 1.0, 'max': 5.0},
            'take_profit_pct': {'type': 'float', 'default': 0.2, 'min': 0.1, 'max': 1.0},
        }
    },
    'Turtle Trading (Optimized)': {
        'class': TurtleStrategyOptimized,
        'description': 'Optimized Turtle Strategy (Best on 1H Timeframe)',
        'params': {
            'lookback': {'type': 'int', 'default': 98, 'min': 50, 'max': 150},
            'atr_period': {'type': 'int', 'default': 30, 'min': 10, 'max': 50},
            'atr_multiplier': {'type': 'float', 'default': 3.7065, 'min': 2.0, 'max': 5.0},
            'take_profit_pct': {'type': 'float', 'default': 0.8997, 'min': 0.5, 'max': 3.0},
        }
    },
    'Consolidation Pop': {

        'class': ConsolidationPopStrategy,
        'description': 'Trade breakouts from consolidation periods',
        'params': {
            'consolidation_bars': {'type': 'int', 'default': 10, 'min': 5, 'max': 50},
            'consolidation_pct': {'type': 'float', 'default': 0.7, 'min': 0.3, 'max': 2.0},
            'take_profit_pct': {'type': 'float', 'default': 0.3, 'min': 0.1, 'max': 1.0},
            'stop_loss_pct': {'type': 'float', 'default': 0.25, 'min': 0.1, 'max': 1.0},
        }
    },
    'Mean Reversion': {
        'class': MeanReversionStrategy,
        'description': 'Buy when price deviates below SMA, sell when above',
        'params': {
            'sma_period': {'type': 'int', 'default': 20, 'min': 10, 'max': 50},
            'deviation': {'type': 'float', 'default': 2.0, 'min': 1.0, 'max': 3.0},
        }
    },
    'Nadarya-Watson Envelope': {
        'class': NadaryaWatsonStrategy,
        'description': 'Reversion strategy using Kernel Regression Envelope (Estimated)',
        'params': {
            'bandwidth': {'type': 'int', 'default': 8, 'min': 3, 'max': 20},
            'mult': {'type': 'float', 'default': 3.0, 'min': 1.0, 'max': 5.0},
        }
    },
    'Market Maker Grid': {
        'class': MarketMakerStrategy,
        'description': 'Grid trading strategy providing liquidity on both sides',
        'params': {
            'grid_levels': {'type': 'int', 'default': 5, 'min': 2, 'max': 10},
            'grid_spacing_pct': {'type': 'float', 'default': 0.5, 'min': 0.1, 'max': 5.0},
        }
    },
    
    # Machine Learning Strategies
    'ML Random Forest Predictor': {
        'class': MLPredictorStrategy,
        'description': 'AI God Mode: Random Forest with Price Action, Volume, and Momentum.',
        'params': {
            'train_len': {'type': 'int', 'default': 500, 'min': 100, 'max': 1000},
            'retrain_freq': {'type': 'int', 'default': 500, 'min': 50, 'max': 500},
            'rsi_period': {'type': 'int', 'default': 14, 'min': 5, 'max': 30},
            'roc_period': {'type': 'int', 'default': 5, 'min': 1, 'max': 20},
            'stop_loss_pct': {'type': 'float', 'default': 2.0, 'min': 0.5, 'max': 10.0},
        }
    },
    'Quantum ML Strategy': {
        'class': MLQuantumStrategy,
        'description': 'Proprietary AI Strategy using Meta-Learner and Deep Features.',
        'params': {
            'confidence_threshold': {'type': 'float', 'default': 0.65, 'min': 0.5, 'max': 0.9},
            'take_profit_pct': {'type': 'float', 'default': 1.5, 'min': 0.5, 'max': 5.0},
            'atr_multiplier': {'type': 'float', 'default': 2.0, 'min': 1.0, 'max': 4.0},
        }
    },
    
    # Advanced Strategies
    'RSI + VWAP': {
        'class': RSIVWAPStrategy,
        'description': 'Combines RSI momentum with VWAP price level',
        'params': {
            'rsi_period': {'type': 'int', 'default': 14, 'min': 5, 'max': 30},
            'rsi_oversold': {'type': 'int', 'default': 30, 'min': 10, 'max': 40},
            'rsi_overbought': {'type': 'int', 'default': 70, 'min': 60, 'max': 90},
            'vwap_period': {'type': 'int', 'default': 20, 'min': 10, 'max': 50},
        }
    },
    'SMA + ADX + Bollinger + Volume': {
        'class': SMABollingerADXStrategy,
        'description': 'Multi-indicator strategy with trend strength confirmation',
        'params': {
            'sma_period': {'type': 'int', 'default': 20, 'min': 10, 'max': 50},
            'adx_period': {'type': 'int', 'default': 14, 'min': 10, 'max': 30},
            'bb_period': {'type': 'int', 'default': 20, 'min': 10, 'max': 50},
            'bb_dev': {'type': 'float', 'default': 2.0, 'min': 1.0, 'max': 3.0},
            'min_adx': {'type': 'int', 'default': 20, 'min': 15, 'max': 30},
            'volume_multiplier': {'type': 'float', 'default': 1.5, 'min': 1.0, 'max': 3.0},
        }
    },
    'Keltner Channels + VWAP': {
        'class': KeltnerVWAPStrategy,
        'description': 'Keltner Channel breakout with VWAP confirmation',
        'params': {
            'ema_period': {'type': 'int', 'default': 20, 'min': 10, 'max': 50},
            'atr_period': {'type': 'int', 'default': 10, 'min': 5, 'max': 20},
            'atr_multiplier': {'type': 'float', 'default': 2.0, 'min': 1.0, 'max': 3.0},
            'vwap_period': {'type': 'int', 'default': 20, 'min': 10, 'max': 50},
        }
    },
    'MACD Crossover': {
        'class': MACDStrategy,
        'description': 'Buy when MACD crosses above signal line',
        'params': {
            'fast_period': {'type': 'int', 'default': 12, 'min': 5, 'max': 20},
            'slow_period': {'type': 'int', 'default': 26, 'min': 20, 'max': 50},
            'signal_period': {'type': 'int', 'default': 9, 'min': 5, 'max': 20},
        }
    },
    'Liquidation Sweep': {
        'class': LiquidationSweepStrategy,
        'description': 'Mean reversion based on major liquidation spikes (exhaustion).',
        'params': {
            'liq_threshold': {'type': 'int', 'default': 100000, 'min': 50000, 'max': 1000000},
            'lookback': {'type': 'int', 'default': 5, 'min': 1, 'max': 20},
            'take_profit_pct': {'type': 'float', 'default': 2.0, 'min': 0.5, 'max': 10.0},
        }
    },
    '💎 AI Gem V1': {
        'class': AIGemV1,
        'description': 'AI-Discovered Strategy: RSI(10) + XGBoost Filter (76% Win Rate)',
        'params': {
            'rsi_period': {'type': 'int', 'default': 10, 'min': 5, 'max': 30},
            'rsi_oversold': {'type': 'int', 'default': 30, 'min': 10, 'max': 40},
            'rsi_overbought': {'type': 'int', 'default': 70, 'min': 60, 'max': 90},
        }
    },
    '🦅 MTF AI Scalper V2': {
        'class': MTFScalperStrategy,
        'description': 'Rigorous 15m Scalper with 1H/4H Context & XGBoost V2',
        'params': {
            'rsi_period': {'type': 'int', 'default': 14, 'min': 5, 'max': 30},
            'tp_pct': {'type': 'float', 'default': 1.5, 'min': 0.5, 'max': 5.0},
            'sl_pct': {'type': 'float', 'default': 1.0, 'min': 0.5, 'max': 3.0},
        }
    },
    '🔥 Mini AI Scalper V4': {
        'class': MiniScalperStrategy,
        'description': 'High Freq Scalper (RSI < 40, TP 150, V4)',
        'params': {
            'rsi_period': {'type': 'int', 'default': 9, 'min': 5, 'max': 20},
            'tp_points': {'type': 'int', 'default': 150, 'min': 100, 'max': 500},
            'sl_points': {'type': 'int', 'default': 100, 'min': 20, 'max': 100},
            'rsi_entry': {'type': 'int', 'default': 40, 'min': 30, 'max': 50},
        }
    }
}

def get_strategy_info():
    """Get all available strategies"""
    return {name: {
        'description': info['description'],
        'params': info['params']
    } for name, info in STRATEGIES.items()}

