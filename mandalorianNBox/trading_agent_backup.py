
import time
import pandas as pd
import sys
import os
import numpy as np
from datetime import datetime
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
from strategies.risk_manager import RiskManager
from research.feature_generator import AdvancedFeatureGenerator
from research.meta_learner import MetaLearner

class SandboxMLBot:
    """
    Standalone ML Bot upgraded to Quantum AI logic.
    """
    def __init__(self):
        self.meta_learner = MetaLearner()
        self.is_trained = False
        
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

    def train_quantum(self, df):
        """Train the MetaLearner on provided dataframe"""
        gen = AdvancedFeatureGenerator(df)
        df_feats = gen.generate_all()
        
        score = self.meta_learner.train(df_feats)
        self.is_trained = True
        return score

    def predict_quantum(self, df):
        """Predict regime and confidence using the MetaLearner"""
        if not self.is_trained:
            return None, 0.0
            
        gen = AdvancedFeatureGenerator(df)
        df_feats = gen.generate_all()
        
        # Get latest numeric features for recommendation
        df_numeric = df_feats.select_dtypes(include=[np.number])
        cols_to_drop = ['open', 'high', 'low', 'close', 'volume', 'target', 'returns', 'log_returns', 'log_ret']
        latest_features = df_numeric.drop(columns=[c for c in cols_to_drop if c in df_numeric.columns]).iloc[-1]
        
        # Get recommendation from MetaLearner
        rec = self.meta_learner.recommend_strategy(latest_features)
        
        # We also want the raw probability for the status check
        scaled_features = self.meta_learner.scaler.transform([latest_features])
        prob_up = self.meta_learner.model.predict_proba(scaled_features)[0][1]
        
        return rec, prob_up
        
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

def run_sandbox_mode(symbol="BTC-USD", interval="1m", use_swarm=True):
    print(f"\n🎮 STARTING SANDBOX MODE: {symbol} ({interval}) | Swarm: {use_swarm}")
    print("------------------------------------------------")
    
    bot = SandboxMLBot()
    swarm = SwarmAgent() if use_swarm else None
    
    # Start Liquidation Monitor (Background Thread)
    liq_mon = LiquidationMonitor(threshold_usd=25000) # $25k+ Liquidations
    liq_mon.start()

    # Start Whale Watcher (Background Thread)
    whale_watch = WhaleWatcher(threshold_usd=500000) # $500k+ Trades
    whale_watch.start()
    
    # Start News Engine (Background Thread)
    news_eng = NewsEngine(refresh_rate=60) # Check news every 60s
    news_eng.start()
    
    # Start Wallet Spy (Background Thread)
    spy_bot = HyperLiquidSpy(refresh_rate=60) # Spy every 60s
    spy_bot.start()
    
    # Start Funding Monitor (Background Thread)
    fund_mon = FundingMonitor(refresh_rate=300) # Check every 5m
    fund_mon.start()
    
    # Initialize Risk Manager
    risk_manager = RiskManager(max_daily_loss_pct=5.0, use_ai_override=True)
    
    last_heartbeat = time.time()
    
    try:
        while True:
            # 1. Fetch History
            print(f"📥 Fetching latest data for {symbol}...", end='\r')
            try:
                df = DataLoader.fetch_yfinance(symbol, period="5d", interval=interval)
            except Exception as e:
                print(f"\n❌ DATA FETCH FAILED: {e}")
                print(f"♻️ Retrying in 5 seconds...")
                time.sleep(5)
                continue
            
            # 2. Add Basic Features for Display/Logic if needed
            # (Note: AdvancedFeatureGenerator handles its own features, but we might want ATR here for SL)
            df_temp = FeatureEngineer.add_atr(df)
            latest_atr = df_temp.iloc[-1]['atr']
            
            # 3. Train Quantum Engine
            score = bot.train_quantum(df)
            
            # 4. Market Data
            latest = df.iloc[-1]
            price = latest['close']
            rsi = latest['rsi_14'] if 'rsi_14' in latest else 50.0 # Default/Fallback
            
            # 5. Predict Quantum Signal
            rec, prob = bot.predict_quantum(df)
            pred = 1 if prob > 0.5 else 0
            strategy_name = rec['strategy'] if rec else "N/A"
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # 5. Check Exits FIRST
            # Check Liquidations
            liq_context = ""
            if liq_mon.latest_liquidation:
                 l = liq_mon.latest_liquidation
                 print(f"\n🚨 REKT ALERT: {l['side']} Liq on {l['symbol']} (${l['amount']:,.0f}) @ ${l['price']:.2f}!")
                 liq_context = f"RECENT LIQUIDATION: {l['side']} ${l['amount']} on {l['symbol']}"
                 
                 # Feed to bot
                 if l['side'] == 'LONG':
                     bot.long_liq_volume += l['amount']
                 else:
                     bot.short_liq_volume += l['amount']
                     
                 liq_mon.latest_liquidation = None # Reset
            
            # Check Whales
            whale_context = ""
            if whale_watch.latest_whale:
                 w = whale_watch.latest_whale
                 print(f"\n🐋 WHALE DETECTED: {w['side']} ${w['amount']:,.0f} @ ${w['price']:.2f}!")
                 whale_context = f"WHALE ACTIVITY: {w['side']} ${w['amount']} @ ${w['price']}"
                 whale_watch.latest_whale = None
                 
            # Check News
            news_context = ""
            if news_eng.latest_news:
                 n = news_eng.latest_news
                 print(f"\n📰 NEWS: {n['title']} ({n['source']})")
                 news_context = f"NEWS: {n['title']}"
                 news_eng.latest_news = None
                 
            # Check Spy Bot
            spy_context = ""
            if spy_bot.latest_spy_data:
                 print(f"\n🕵️‍♂️ SPY REPORT: {spy_bot.latest_spy_data}")
                 spy_context = f"SMART MONEY: {spy_bot.latest_spy_data}"
                 spy_bot.latest_spy_data = None
                 
            # Check Funding Monitor
            fund_context = ""
            if fund_mon.latest_opportunity:
                 print(f"\n💰 FUNDING ALERT: {fund_mon.latest_opportunity}")
                 fund_context = f"FUNDING ARB: {fund_mon.latest_opportunity}"
                 fund_mon.latest_opportunity = None
                 
            # Check Risk Manager (Simulated PnL)
            # In live, this would read actual wallet value
            current_sim_balance = 100000 + (bot.quantity * (price - bot.entry_price) if bot.position == 'LONG' else 0)
            if risk_manager.update_pnl(current_sim_balance):
                 print(f"👮‍♂️ RISK MANAGER TRIGGERED: Closing All Positions!")
                 bot.close_position(price, "RISK OVERRIDE", 0, timestamp)
                 
            # 6. Execute Trading Logic
            if not bot.position:
                # A. Check for Liquidation Sweep (High Priority Contrarian)
                if bot.check_liquidation_sweep(price, latest_atr, timestamp):
                    continue 
                    
                # B. Check for Optimized SMA Scalp (Fast 45 / Slow 50)
                if not bot.position:
                    if bot.check_sma_scalp(df, price, latest_atr, timestamp):
                        continue

                # C. Check for Optimized Turtle Strategy (High Performance)
                if not bot.position:
                    if bot.check_turtle_optimized(df, price, latest_atr, timestamp):
                        continue

                # C. Quantum AI Entry (Standard Trend/Regime)
                if not bot.position:
                    if prob > 0.65: # High Confidence
                        sl = price - (latest_atr * bot.atr_multiplier)
                        tp = price + (latest_atr * bot.atr_multiplier * 1.5)
                        bot.open_position(price, sl, tp, timestamp)
                    
                # C. Swarm Override (Optional)
                elif use_swarm and swarm:
                    if time.time() % 60 < 10: 
                        market_context = f"Price: {price} | RSI: {rsi:.2f} | Pred: {pred} ({prob:.2f})"
                        full_context = f"{market_context} {liq_context} {whale_context} {news_context} {spy_context} {fund_context}"
                        prompt = f"Analyze this market context and decide BUY/SELL/HOLD: {full_context}"
                        res = swarm.query(prompt)
                        summary = res['consensus_summary']
                        if "BUY" in summary and "SELL" not in summary:
                            bot.open_position(price, price*0.99, price*1.02, timestamp)

                # Log Status if no trade triggered
                if not bot.position:
                    print(f"[{timestamp}] ${price:.2f} | Acc: {score:.2f} | Pred: {'BUY' if prob > 0.6 else 'SELL'} ({prob:.2f}) | Rec: {strategy_name}    ")

            else:
                # Manage Position
                unrealized_pnl = ((price - bot.entry_price) / bot.entry_price) * 100
                print(f"[{timestamp}] ${price:.2f} | POS: {bot.position} ({unrealized_pnl:.2f}%) | SL: {bot.sl_price:.2f} TP: {bot.tp_price:.2f} | Engine: {strategy_name}   ")

                # 1. Check Technical SL/TP (ATR based)
                if bot.check_exit(price, timestamp):
                    continue 

                # 2. Check Quantum Pull-back (Confidence Drop)
                if prob < 0.40: 
                     bot.close_position(price, "📉 QUANTUM CONFIDENCE EXIT", unrealized_pnl, timestamp)

                # 3. Swarm Exit Override
                elif use_swarm and swarm and time.time() % 60 < 10:
                    res = swarm.query(f"Current Position: LONG @ {bot.entry_price}. Current Price: {price}. Should we EXIT? Context: {liq_context} {news_context}")
                    if "SELL" in res['consensus_summary']:
                        bot.close_position(price, "🤖 SWARM SELL", unrealized_pnl, timestamp)

            # 6. Heartbeat Log (Every 60s)
            if time.time() - last_heartbeat > 60:
                 if not bot.position:
                      bot.log_status(price, prob, strategy_name, timestamp)
                 last_heartbeat = time.time()

            # Wait for next check
            time.sleep(10) 
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping Sandbox Mode.")
    except Exception as e:
        print(f"\n⚠️ Error: {e}")

if __name__ == "__main__":
    run_sandbox_mode()
