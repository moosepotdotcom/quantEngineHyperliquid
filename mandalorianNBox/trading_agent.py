
import time
import pandas as pd
import sys
import os
import numpy as np
from datetime import datetime
import backtrader as bt
import json
import ta
import threading
from research.feature_generator import AdvancedFeatureGenerator
from research.mtf_feature_engineer import MTFFeatureGenerator
from research.genetic_genome import Genome
import joblib
try:
    import xgboost as xgb
    USE_XGB = True
except ImportError:
    USE_XGB = False
except Exception:
    USE_XGB = False
from sklearn.ensemble import RandomForestClassifier


class Engine:
    """
    Represents a single trading engine (Scalper, Day, Swing, Investor).
    Manages its own strategy logic, parameters, and timeframe.
    """
    def __init__(self, name, strategy_class, params, timeframe_key, allocation_pct):
        self.name = name
        self.strategy_class = strategy_class
        self.params = params
        self.timeframe_key = timeframe_key # '1m', '1h', '6h', '1d'
        self.allocation_pct = allocation_pct
        self.allocation_pct = allocation_pct
        self.position = None # Current position state
        self.entry_price = 0.0
        self.sl_price = 0.0
        self.tp_price = 0.0

    def check_signal(self, df, capital):
        """
        Runs a micro-backtest OR Darwinian eval to get current signal.
        Returns: 'LONG', 'SHORT', 'NEUTRAL' (and potentially size/price info)
        """
        # Skip Darwin Engine in Cloud Mode (resource intensive)
        CLOUD_MODE = os.environ.get('PORT', None) is not None  # Cloud Run sets PORT
        
        # Special Case: Darwinian AI Engine
        if self.strategy_class == "Darwin":
            if CLOUD_MODE:
                return "WAIT"  # Skip in cloud to save resources
            try:
                # 1. Feature Engineering (Darwin needs advanced features)
                gen = AdvancedFeatureGenerator(df)
                df_feat = gen.generate_all()
                
                # 2. Load Genome
                with open('darwin_winner.json', 'r') as f:
                    dna = json.load(f)
                    
                genome = Genome(list(df_feat.columns))
                genome.buy_conditions = dna['buy_conditions']
                genome.sell_conditions = dna['sell_conditions']
                genome.stop_loss_pct = dna['stop_loss_pct']
                genome.take_profit_pct = dna['take_profit_pct']
                
                # 3. Evaluate on LATEST Data Point
                buy_series, sell_series = genome.get_signal_series(df_feat)
                latest_buy = buy_series.iloc[-1]
                latest_sell = sell_series.iloc[-1]
                
                # Logic
                if latest_buy and not self.position:
                    # Capture Params for logging
                    self.params['stop_loss_pct'] = dna['stop_loss_pct']
                    self.params['take_profit_pct'] = dna['take_profit_pct']
                    
                    # Calculate Prices for Logging
                    current_price = df['close'].iloc[-1]
                    self.sl_price = current_price * (1 - dna['stop_loss_pct']/100)
                    self.tp_price = current_price * (1 + dna['take_profit_pct']/100)
                    
                    print(f"🧬 DARWIN AI ({self.name}) SIGNAL: {genome.buy_conditions}")
                    print(f"   🎯 Signal Price: Market | SL: {dna['stop_loss_pct']}% | TP: {dna['take_profit_pct']}%")
                    return 'LONG'
                elif latest_sell and self.position:
                    return 'NEUTRAL' # Close
                
                return self.position # Stay 
            except Exception as e:
                print(f"⚠️ Darwin Error: {e}")
                return None

        # Special Case: Darwin Scalper (15m High Freq)
        elif self.strategy_class == "DarwinScalper":
            if CLOUD_MODE:
                return "WAIT"  # Skip in cloud to save resources
            try:
                gen = AdvancedFeatureGenerator(df)
                df_feat = gen.generate_all()
                
                with open('darwin_scalper.json', 'r') as f:
                    dna = json.load(f)
                    
                genome = Genome(list(df_feat.columns))
                genome.buy_conditions = dna['buy_conditions']
                genome.sell_conditions = dna['sell_conditions']
                
                buy_series, sell_series = genome.get_signal_series(df_feat)
                latest_buy = buy_series.iloc[-1]
                latest_sell = sell_series.iloc[-1]
                
                if latest_buy and not self.position:
                    self.params['stop_loss_pct'] = dna['stop_loss_pct']
                    self.params['take_profit_pct'] = dna['take_profit_pct']
                    
                    # Calculate Prices
                    current_price = df['close'].iloc[-1]
                    self.sl_price = current_price * (1 - dna['stop_loss_pct']/100)
                    self.tp_price = current_price * (1 + dna['take_profit_pct']/100)
                    
                    print(f"⚡ AI SCALPER ({self.name}) SIGNAL: {genome.buy_conditions}")
                    print(f"   🎯 Scalp Entry | SL: {dna['stop_loss_pct']}% | TP: {dna['take_profit_pct']}%")
                    return 'LONG'
                elif latest_sell and self.position:
                    return 'NEUTRAL'
            except Exception as e:
                print(f"⚠️ Scalper Error: {e}")
                return None

        # Special Case: ML Scalper (XGBoost MTF Bidirectional)
        elif self.strategy_class == "MLScalper":
            try:
                # 1. Access Context Data
                df_5m = df
                df_15m = getattr(self, 'context_data', {}).get('15m', pd.DataFrame())
                df_30m = getattr(self, 'context_data', {}).get('30m', pd.DataFrame())
                
                if df_5m.empty or df_15m.empty or df_30m.empty: return None

                # 2. Features (MTF)
                gen = MTFFeatureGenerator(df_5m, df_15m, df_30m)
                df_feat = gen.generate()
                
                # 3. Load BOTH Models
                long_model_path = os.path.join("models", "scalp_mtf_long.pkl")
                short_model_path = os.path.join("models", "scalp_mtf_short.pkl")
                
                if not os.path.exists(long_model_path) or not os.path.exists(short_model_path):
                    print("⚠️ Bidirectional ML Models not found!")
                    return None
                    
                model_long = joblib.load(long_model_path)
                model_short = joblib.load(short_model_path)
                
                # 4. Prepare features
                cols_to_drop = ['open', 'high', 'low', 'close', 'volume', 'target', 'target_long', 'target_short',
                                'dividends', 'stock splits', 
                                'open_15m', 'close_15m', 'high_15m', 'low_15m', 'volume_15m', 
                                'open_30m', 'close_30m', 'high_30m', 'low_30m', 'volume_30m']
                latest_features = df_feat.iloc[[-1]]
                latest_features = latest_features.drop(columns=[c for c in cols_to_drop if c in latest_features.columns], errors='ignore')
                
                # 5. Get BOTH probabilities
                prob_long = model_long.predict_proba(latest_features)[0][1]
                prob_short = model_short.predict_proba(latest_features)[0][1]
                
                # Threshold
                THRESHOLD = 0.50
                
                # Debug logging
                print(f"   [MTF] LONG: {prob_long:.4f} | SHORT: {prob_short:.4f} (Threshold: {THRESHOLD})")
                
                # Write status for dashboard
                try:
                    import json
                    status_file = os.path.join("data", "ml_status.json")
                    os.makedirs("data", exist_ok=True)
                    with open(status_file, 'w') as f:
                        json.dump({
                            'long_prob': float(prob_long),
                            'short_prob': float(prob_short),
                            'threshold': THRESHOLD,
                            'regime': 'BEAR' if prob_short > prob_long else 'BULL' if prob_long > 0.4 else 'CHOP',
                            'whale_bias': 0,
                            'funding_bias': 0,
                            'timestamp': datetime.now().isoformat()
                        }, f)
                except:
                    pass
                
                current_price = df_5m['close'].iloc[-1]
                
                # DEBUG: Log position state
                print(f"   [DEBUG] ML Scalper Position State: {self.position}")
                
                # Signal Logic: Take the STRONGER signal if it exceeds threshold
                if not self.position:
                    if prob_long > THRESHOLD and prob_long > prob_short:
                        print(f"🟢 MTF ML SCALPER ({self.name}) SIGNAL: LONG")
                        print(f"   📊 Confidence: {prob_long:.2%} > {THRESHOLD:.0%}")
                        
                        self.params['stop_loss_pct'] = 0.5
                        self.params['take_profit_pct'] = 0.5
                        self.entry_price = current_price
                        self.sl_price = current_price * (1 - 0.005)
                        self.tp_price = current_price * (1 + 0.005)
                        
                        print(f"   [DEBUG] Set SL: {self.sl_price:.2f}, TP: {self.tp_price:.2f}")
                        
                        return 'LONG'
                        
                    elif prob_short > THRESHOLD and prob_short > prob_long:
                        print(f"🔴 MTF ML SCALPER ({self.name}) SIGNAL: SHORT")
                        print(f"   📊 Confidence: {prob_short:.2%} > {THRESHOLD:.0%}")
                        
                        self.params['stop_loss_pct'] = 0.5
                        self.params['take_profit_pct'] = 0.5
                        self.entry_price = current_price
                        self.sl_price = current_price * (1 + 0.005)  # Inverted for SHORT
                        self.tp_price = current_price * (1 - 0.005)  # Inverted for SHORT
                        
                        print(f"   [DEBUG] Set SL: {self.sl_price:.2f}, TP: {self.tp_price:.2f}")
                        
                        return 'SHORT'
                    else:
                        return 'NEUTRAL'
                else:
                    print(f"   [DEBUG] ML Scalper holding {self.position}, SL: {self.sl_price:.2f}, TP: {self.tp_price:.2f}")
                    # Exit logic: Check if opposite signal becomes strong
                    return 'NEUTRAL'

                return self.position or 'NEUTRAL'

            except Exception as e:
                print(f"⚠️ ML Scalper Error: {e}")
                import traceback
                traceback.print_exc()
                return 'NEUTRAL'

        # Special Case: ML Scalper V2 (Enhanced with Filters)
        elif self.strategy_class == "MLScalperV2":
            try:
                from agents.ml_scalper_v2 import MLScalperV2
                
                # Get or create V2 instance
                if not hasattr(self, 'v2_instance'):
                    self.v2_instance = MLScalperV2()
                
                # Access Context Data
                df_5m = df
                df_15m = getattr(self, 'context_data', {}).get('15m', pd.DataFrame())
                df_30m = getattr(self, 'context_data', {}).get('30m', pd.DataFrame())
                
                if df_5m.empty or df_15m.empty or df_30m.empty: 
                    return 'NEUTRAL'
                
                # Get signal from V2
                signal = self.v2_instance.check_signal(df_5m, df_15m, df_30m)
                
                # Copy SL/TP from V2 instance
                if signal in ['LONG', 'SHORT']:
                    self.entry_price = self.v2_instance.entry_price
                    self.sl_price = self.v2_instance.sl_price
                    self.tp_price = self.v2_instance.tp_price
                
                return signal or 'NEUTRAL'
                
            except Exception as e:
                print(f"⚠️ ML Scalper V2 Error: {e}")
                import traceback
                traceback.print_exc()
                return 'NEUTRAL'

        # Standard Backtrader Engine
        # Micro-Backtest Implementation
        # We run Cerebro on the last 500 bars to see what the strategy would do NOW.
        try:
            if df.empty: return None

            cerebro = bt.Cerebro()
            # Fast/Quiet mode
            cerebro.broker.setcash(capital)
            cerebro.broker.setcommission(commission=0.001)
            
            # Add data
            data = bt.feeds.PandasData(dataname=df)
            cerebro.adddata(data)
            
            # Add strategy
            cerebro.addstrategy(self.strategy_class, **self.params)
            
            # Run
            strats = cerebro.run()
            strat = strats[0]
            
            # Check Position status in the simulation
            # Ideally, we want to know if the strategy generated a signal THIS BAR.
            # But Backtrader runs through history.
            # If the strategy has a position at the end, it implies a HOLD.
            # If it just bought on the last bar, it's a BUY.
            
            # To detect a FRESH signal, we can check orders created in the last timestamp?
            # Or simplified: We just check if the strategy WANTS to be in a position vs our current real position.
            
            # For now, let's return the simplified intent:
            # Wrapper for Backtrader strategies
            if strat.position.size > 0:
                # Extract SL/TP from strategy instance if available
                self.sl_price = getattr(strat, 'sl_price', 0.0)
                self.tp_price = getattr(strat, 'tp_price', 0.0)
                return 'LONG'
            elif strat.position.size < 0:
                self.sl_price = getattr(strat, 'sl_price', 0.0)
                self.tp_price = getattr(strat, 'tp_price', 0.0)
                return 'SHORT'
            else:
                return 'NEUTRAL'
                
        except Exception as e:
            print(f"⚠️ Engine {self.name} Error: {e}")
            return None

from sklearn.ensemble import RandomForestClassifier

import warnings
# Suppress sklearn feature name warnings
warnings.filterwarnings("ignore", category=UserWarning, module='sklearn')

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from features.engineering import FeatureEngineer
from data.loader import DataLoader
from utils.logger import log_trade
from agents.liquidation_agent import LiquidationMonitor
from agents.whale_agent import WhaleWatcher
from agents.sentiment_agent import NewsEngine
from agents.copy_agent import HyperLiquidSpy
from agents.funding_agent import FundingMonitor
from agents.swarm_agent import SwarmAgent
from agents.adaptive_ml_engine import AdaptiveMLEngine
from strategies.risk_manager import RiskManager
from strategies.risk_manager import RiskManager
from research.feature_generator import AdvancedFeatureGenerator

class SandboxMLBot:
    """
    Standalone ML Bot upgraded to Quantum AI logic.
    """
    def __init__(self):
        # self.meta_learner = MetaLearner() # Disabled for now (Removing Complexity)
        self.is_trained = False
        
        # Portfolio State
        self.balance = 100000
        self.positions = {} # { 'Day Trader': {'size': 0, 'entry': 0}, ... }
        self.engines = []
        
        self.setup_engines()
        
        # Position State
        self.position = None # None, 'LONG'
        self.entry_price = 0.0
        self.sl_price = 0.0
        self.tp_price = 0.0
        self.atr_multiplier = 2.5
        self.quantity = 0.01 # Set to 0.01 as per user preference (was 0.1)
        
        # Liquidation Sweep State
        self.long_liq_volume = 0
        self.short_liq_volume = 0
        self.liq_threshold = 100000 # $100k for a 'sweep'
        
    def setup_engines(self):
        """Initialize the Four Pillars of the Hedge Fund"""
        from dashboard.strategies_complete import ConsolidationPopStrategy, SMAStrategy, TurtleStrategyOptimized
        
        # 1. Day Trader (Turtle Optimized - 1H) - The Workhorse
        self.engines.append(Engine(
            name="Day Trader",
            strategy_class=TurtleStrategyOptimized,
            params={'lookback': 98, 'atr_period': 30, 'atr_multiplier': 3.7065, 'take_profit_pct': 0.8997},
            timeframe_key='1h',
            allocation_pct=0.25
        ))
        
        # 2. Swing Trader (Consolidation Pop - 6H) - The Sniper
        self.engines.append(Engine(
            name="Swing Trader",
            strategy_class=ConsolidationPopStrategy,
            params={'consolidation_bars': 12, 'consolidation_pct': 0.8, 'take_profit_pct': 6.0, 'stop_loss_pct': 2.5},
            timeframe_key='6h', # Will use Resampled 6H data
            allocation_pct=0.25
        ))
        
        # 3. Investor (Golden Cross - 1D) - The Vault
        self.engines.append(Engine(
            name="Investor",
            strategy_class=SMAStrategy,
            params={'fast_period': 50, 'slow_period': 200},
            timeframe_key='1d',
            allocation_pct=0.25
        ))
        
        # 4. Darwin Engine (Auto-Evolutionary AI)
        # SKIP IN CLOUD to save resources
        CLOUD_MODE = os.environ.get('PORT') is not None
        if not CLOUD_MODE:
            self.engines.append(Engine(
                name="Darwin Evo",
                strategy_class="Darwin", # Special Flag
                params={}, # Loaded from JSON
                timeframe_key='1h',
                allocation_pct=0.25
            ))
        
        # 5. AI Scalper (15m High Freq) - Powered by XGBoost
        self.engines.append(Engine(
            name="AI Scalper",
            strategy_class="MLScalper",
            params={},
            timeframe_key='15m',
            allocation_pct=0.10
        ))
        
        # 6. AI Scalper V2 (Enhanced) - Tier 1 + Tier 2 Features
        self.engines.append(Engine(
            name="AI Scalper V2",
            strategy_class="MLScalperV2",
            params={},
            timeframe_key='15m',
            allocation_pct=0.10
        ))
        
    # Old Quantum Methods (Kept for compatibility but unused)
    def train_quantum(self, df): return 0
    def predict_quantum(self, df): return None, 0
        
    def prepare_data(self, df):
        """Prepare features and labels for training/prediction"""
        df = df.copy() # Avoid SettingWithCopyWarning
        # Features are already added by loop in main, but safe to assume passed df has them or we verify
        
        # Create Target (Next Close > Current Close)
        df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
        
        # Features
        feature_cols = ['rsi', 'macd', 'bb_width', 'atr', 'log_return'] 
        
        # Drop NaN
        df = df.dropna()
        return df, feature_cols

        
    # Old Quantum Methods (Kept for compatibility but unused)
    def train_quantum(self, df): return 0
    def predict_quantum(self, df): return None, 0
        
    def prepare_data(self, df):
        """Prepare features and labels for training/prediction"""
        df = df.copy() # Avoid SettingWithCopyWarning
        # Create Target (Next Close > Current Close)
        df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
        # Features
        feature_cols = ['rsi', 'macd', 'bb_width', 'atr', 'log_return'] 
        # Drop NaN
        df = df.dropna()
        return df, feature_cols
        
    def log_status(self, price, prob, rec_name, timestamp):
        """Log status with Quantum AI regime data"""
        log_trade(
             symbol="BTC-USD",
             action="STATUS CHECK",
             price=price,
             size=0.0,
             status=f"Quantum Pred: {'BUY' if prob > 0.5 else 'SELL'} (Conf: {prob:.2f}) | Rec: {rec_name} - Waiting for Setup..."
        )
        
    def check_exit(self, current_price, timestamp):
        """Check Stop Loss or Take Profit"""
        if self.position == 'LONG':
            pnl_pct = ((current_price - self.entry_price) / self.entry_price) * 100
            exit_reason = None
            
            if current_price <= self.sl_price:
                exit_reason = "❌ STOP LOSS HIT"
            elif current_price >= self.tp_price:
                exit_reason = "✅ TAKE PROFIT HIT"
                
            if exit_reason:
                self.close_position(current_price, exit_reason, pnl_pct, timestamp)
                return True
        return False
        
    def close_position(self, price, reason, pnl_pct, timestamp):
        msg = f"   >>> {reason} @ {price:.2f} | PnL: {pnl_pct:.2f}%"
        print(msg)
        log_trade(
            symbol="BTC-USD", 
            action="SELL (Exit)", 
            price=price, 
            size=self.quantity,
            reason=reason, 
            pnl=pnl_pct,
            status="Closed"
        )
        self.position = None
        
    def open_position(self, price, sl, tp, timestamp):
        self.position = 'LONG'
        self.entry_price = price
        self.sl_price = sl
        self.tp_price = tp
        
        msg = f"   >>> 🚀 ENTRY LONG @ {price:.2f} | SL: {sl:.2f} | TP: {tp:.2f}"
        print(msg)
        log_trade(
            symbol="BTC-USD", 
            action="BUY (Entry)", 
            price=price, 
            size=self.quantity,
            reason=f"Target: {tp:.2f}, Stop: {sl:.2f}",
            status="Open"
        )
        
    def check_sma_scalp(self, df, current_price, latest_atr, timestamp):
        """
        Optimized SMA Scalper (Fast 45, Slow 50)
        Returns True if trade triggered
        """
        if len(df) < 55: return False
        
        # Calculate SMA
        fast_sma = df['close'].rolling(window=45).mean().iloc[-1]
        slow_sma = df['close'].rolling(window=50).mean().iloc[-1]
        prev_fast = df['close'].rolling(window=45).mean().iloc[-2]
        prev_slow = df['close'].rolling(window=50).mean().iloc[-2]
        
        # Check Crossover (Bullish Only for now as backtest was Long only)
        # Actually backtest was standard cross, so let's do Long only for safety/trend
        if prev_fast <= prev_slow and fast_sma > slow_sma:
            print(f"⚡ SMA SCALP SIGNAL: Fast(45) crossed above Slow(50)!")
            
            # Scalp Targets (Tighter than Quantum)
            sl = current_price - (latest_atr * 1.0) # Tight stop
            tp = current_price + (latest_atr * 1.2) # Quick profit
            
            self.open_position(current_price, sl, tp, timestamp)
            print(f"   >>> SMA Scalp Triggered: ENTRY ${current_price:.2f}")
            return True
            
        return False

    def check_turtle_optimized(self, df, current_price, latest_atr, timestamp):
        """
        Optimized Turtle Strategy (Lookback 98, ATR 30, Multiplier 3.7)
        Verified: +58% on 1H timeframe.
        """
        lookback = 98
        if len(df) < lookback + 1: return False
        
        # Calculate Logic
        # We need the highest high of the *previous* 98 bars (not including current)
        # Shifted by 1 to avoid lookahead if using 'close' directly, but easier to use standard window
        
        # High of the last 98 closed bars (excluding current forming candle if live, but df usually has closed)
        # Assuming df has latest closed candle at -1
        
        recent_window = df['high'].iloc[-lookback-1:-1] # Previous 98 bars
        if len(recent_window) < lookback: return False
        
        donchian_high = recent_window.max()
        donchian_low = recent_window.min()
        
        # Entry Condition: Breakout
        if current_price > donchian_high:
            print(f"🐢 TURTLE OPTIMIZED SIGNAl: Price ${current_price:.2f} broke 98-bar High ${donchian_high:.2f}!")
            
            atr_period = 30
            atr_mult = 3.7065
            tp_pct = 0.8997
            
            # Recalculate ATR if needed for specific period, or use latest_atr (usually 14) 
            # ideally we compute ATR(30) here for accuracy
            try:
                tr = np.maximum(df['high'] - df['low'], 
                               np.maximum(abs(df['high'] - df['close'].shift(1)), 
                                          abs(df['low'] - df['close'].shift(1))))
                custom_atr = tr.rolling(window=atr_period).mean().iloc[-1]
            except:
                custom_atr = latest_atr # Fallback
            
            sl = current_price - (custom_atr * atr_mult)
            tp = current_price * (1 + tp_pct / 100) # Percentage based TP
            
            self.open_position(current_price, sl, tp, timestamp)
            print(f"   >>> Turtle Entry: ENTRY ${current_price:.2f} | SL ${sl:.2f} | TP ${tp:.2f}")
            return True
            
        return False

    def check_liquidation_sweep(self, current_price, latest_atr, timestamp):
        """Check for exhaustion spikes to trigger contrarian entries"""
        if self.position:
            return False
            
        action = None
        reason = ""
        
        if self.long_liq_volume >= self.liq_threshold:
            action = "BUY"
            reason = f"Liquidation Sweep (Longs Rekt: ${self.long_liq_volume:,.0f})"
        elif self.short_liq_volume >= self.liq_threshold:
            action = "SELL"
            reason = f"Short Squeeze Sweep (Shorts Rekt: ${self.short_liq_volume:,.0f})"
            
        if action == "BUY":
            sl = current_price - (latest_atr * self.atr_multiplier)
            tp = current_price + (latest_atr * self.atr_multiplier * 1.5)
            print(f"🔥 {reason} - Triggering Entry!")
            self.open_position(current_price, sl, tp, timestamp)
            # Reset volume after entry
            self.long_liq_volume = 0
            return True
        elif action == "SELL":
            # We currently only support 'LONG' in the mock bot, but we could add SHORT
            # For now, let's just log it or implement a SHORT exit if we were long
            print(f"🚀 {reason} - Potential Top Detected.")
            self.short_liq_volume = 0
            
        # Decay volume slowly
        self.long_liq_volume *= 0.8
        self.short_liq_volume *= 0.8
        return False

    def log_journal(self, message):
         with open('PROJECT_DEV_LOG.md', 'a') as f:
            f.write(message)


def run_sandbox_mode():
    print("🚀 STARTING MULTI-ENGINE HEDGE FUND BOT (Paper Trading)...")
    
    # Initialize The "Hedge Fund"
    bot = SandboxMLBot()
    risk_manager = RiskManager()
    
    # -----------------------------------------------------------
    # Initialize Event Monitors (Background Threads)
    # -----------------------------------------------------------
    print("📡 Initializing Event Monitors...")
    liq_monitor = LiquidationMonitor(threshold_usd=50000)
    whale_watcher = WhaleWatcher(threshold_usd=500000)
    funding_monitor = FundingMonitor(refresh_rate=300) # Check Arbs every 5 mins
    
    liq_monitor.start()
    whale_watcher.start()
    funding_monitor.start()
    
    # Start News Engine (Fetches from RSS feeds)
    news_engine = NewsEngine(refresh_rate=300)  # Check every 5 mins
    news_engine.start()
    
    # Start Adaptive ML Engine (Retrains every 6 hours on rolling 5-day window)
    adaptive_engine = AdaptiveMLEngine(retrain_interval_hours=6, lookback_days=5)
    adaptive_engine.start()
    
    # State tracking for logging
    last_log_time = 0
    
    symbol = "BTC-USD"
    
    try:
        while True:
            # -----------------------------------------------------------
            # 1. Fetch Datafeeds (The "Bloomberg Terminal")
            # -----------------------------------------------------------
            print(f"📥 Fetching Multi-Timeframe Data...", end='\r')
            try:
                # 1H Data (For Day Trader)
                df_1h = DataLoader.fetch_yfinance(symbol, period="3mo", interval="1h", quiet=True)
                
                # 5m Data (For MTF Scalper Base)
                df_5m = DataLoader.fetch_yfinance(symbol, period="5d", interval="5m", quiet=True)
                
                # 15m Data (For MTF Scalper Context)
                df_15m = DataLoader.fetch_yfinance(symbol, period="1mo", interval="15m", quiet=True)
                
                # 30m Data (For MTF Scalper Context)
                df_30m = DataLoader.fetch_yfinance(symbol, period="1mo", interval="30m", quiet=True)
                
                # 6H Data (For Swing Trader) - Resampled from 1H
                # Logic: Resample 1H data to 6H
                df_6h = df_1h.resample('6h').agg({
                    'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
                }).dropna()
                
                # 1D Data (For Investor)
                df_1d = DataLoader.fetch_yfinance(symbol, period="2y", interval="1d", quiet=True)
                
            except Exception as e:
                print(f"\n❌ DATA FETCH FAILED: {e}")
                time.sleep(10)
                continue

            # -----------------------------------------------------------
            # 2. Execute Engines
            # -----------------------------------------------------------
            timestamp = datetime.now().strftime("%H:%M:%S")
            price = df_1h.iloc[-1]['close']
            
            engine_statuses = []
            
            for engine in bot.engines:
                # Select correct data
                if engine.timeframe_key == '1h':
                    df = df_1h
                elif engine.timeframe_key == '6h':
                    df = df_6h
                elif engine.timeframe_key == '1d':
                    df = df_1d
                elif engine.timeframe_key == '15m':
                    # Special Case: MTF Engine needs tuple or we just pass 5m and it handles rest?
                    # Current Architecture passes single DF.
                    # Hack: Pass tuple (df_5m, df_15m, df_30m) or handle inside check_signal via global/arg stuff
                    # Cleaner: Modify check_signal to accept context.
                    # For now, let's pass df_5m as primary, but attach others to the engine instance temporarily
                    df = df_5m
                    engine.context_data = {'15m': df_15m, '30m': df_30m}
                else:
                    df = pd.DataFrame() # Empty
                
                # Check Signal (Micro-Backtest)
                signal = engine.check_signal(df, capital=bot.balance * engine.allocation_pct)
                
                # Update "Virtual" Position State (Simplified)
                # In a real system, we'd sync this with exchange orders.
                if signal is not None and signal != engine.position:
                    # Construct detailed trade reason with SL/TP if available
                    trade_reason = f"Strategy Signal"
                    if signal == 'LONG' and engine.sl_price > 0:
                        trade_reason += f" | SL: ${engine.sl_price:.2f} | TP: ${engine.tp_price:.2f}"
                        
                    # Log State Change
                    log_trade(
                        symbol=symbol,
                        action=f"ENGINE SIGNAL ({engine.name})",
                        price=price,
                        size=0.0, # Virtual
                        reason=trade_reason,
                        status=f"{engine.position} -> {signal}",
                        sl=engine.sl_price,
                        tp=engine.tp_price,
                        engine=engine.name
                    )
                    engine.position = signal
                
                # Just for display, map internal state
                status_str = f"{engine.name}: {signal if signal else 'WAIT'}"
                engine_statuses.append(status_str)
            
            # -----------------------------------------------------------
            # 2a. Event-Driven Logic (The "Vulture" & "Whale Follower")
            # -----------------------------------------------------------
            # Check Liquidation Reversal
            if liq_monitor.latest_liquidation:
                # Only act if event is fresh ( < 60 seconds old )
                liq_event = liq_monitor.latest_liquidation
                if time.time() - liq_event['time'] < 60:
                    # Calculate BB for confirmation
                    bb = ta.volatility.BollingerBands(close=df_1h['close'], window=20, window_dev=2)
                    lower_band = bb.bollinger_lband().iloc[-1]
                    
                    if liq_event['side'] == 'LONG' and price <= lower_band:
                        # Massive Long Liq + Price at Low Band = Reversal Buy
                        if bot.position != 'LONG':
                            print(f"🔥 LIQUIDATION SNIPE! Amt: ${liq_event['amount']:,.0f}")
                            bot.open_position(price, price*0.98, price*1.05, timestamp) # 2% SL, 5% TP
                            log_trade(symbol, "BUY (Liq Snipe)", price, 0.1, f"Liq: ${liq_event['amount']:,.0f}", "Open")
                            
            # Check Whale Follower
            if whale_watcher.latest_whale:
                whale = whale_watcher.latest_whale
                if time.time() - whale['time'] < 60:
                   # VWAP Check (Approximation using TA usually requires volume, we have it)
                   # ta vwap requires High, Low, Close, Volume
                   vwap = ta.volume.VolumeWeightedAveragePrice(
                       high=df_1h['high'], low=df_1h['low'], close=df_1h['close'], volume=df_1h['volume'], window=14
                   )
                   curr_vwap = vwap.volume_weighted_average_price().iloc[-1]
                   
                   if whale['side'] == 'BUY' and price > curr_vwap:
                       # Whale Buy + Price Bullish = Ride
                       if bot.position != 'LONG':
                           print(f"🐋 WHALE RIDE! Amt: ${whale['amount']:,.0f}")
                           bot.open_position(price, price*0.98, price*1.05, timestamp)
                           log_trade(symbol, "BUY (Whale Ride)", price, 0.1, f"Whale: ${whale['amount']:,.0f}", "Open")

            # -----------------------------------------------------------
            
            # -----------------------------------------------------------
            # 3. Log Status (Quiet Professional)
            # -----------------------------------------------------------
            # Log to console every loop? No, that's spammy.
            # Only log if something changed? Or every 1 minute?
            # For now, print status update every loop but overwrite line?
            
            status_line = f"[{timestamp}] ${price:,.0f} | " + " | ".join(engine_statuses)
            print(f"\r{status_line}          ", end='') # Overwrite line
            sys.stdout.flush()
            
            # If any engine signaled a trade, log it to file (Implementation TODO)
            # For now, we trust check_signal covers the logic.
            
            # -----------------------------------------------------------
            # 4. Risk Checks
            # -----------------------------------------------------------
            # (Global Risk Manager checks would go here)
            
            time.sleep(60) # High timeframe bot, 1 min sleep is fine
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping Hedge Fund.")
    except Exception as e:
        print(f"\n⚠️ Error: {e}")


if __name__ == "__main__":
    run_sandbox_mode()
