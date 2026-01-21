#!/usr/bin/env python3
"""
MANDALORIAN PHASE 3 ENGINE
- Verified Trio Ensemble Models
- Advanced Alpha Features (Lags, Hurst, Volatility Zones)
- Adaptive Risk Management (ATR Filters)
- State Persistence & Cloud Ready
"""

import os
import sys
import time
import json
import logging
import argparse
import signal
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quant_engine import TradingEngine, add_all_indicators, MTF_FEATURE_LIST
from utils.advanced_features import add_advanced_features

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("mandalorian_phase3.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("MandalorianPhase3")

# Constants
CONFIG = {
    "SYMBOL": "BTC",
    "LEVERAGE": 50,
    "MAX_CONCURRENT_POSITIONS": 12, # Validated Phase 2
    "MAX_TRADE_DURATION_HOURS": 12, # Validated Phase 2
    "INITIAL_BALANCE": 0.0, # Will be set dynamically
    "COMPOUNDING": True,
    "TP_PCT": 0.015, # 1.5%
    "SL_PCT": 0.008, # 0.8% (Hybrid Mode: Tight Safety)
    "STATE_FILE": "phase3_state.json",
    "MODEL_CONF_THRESHOLD": 0.45 
}

class Phase3Trader:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.engine = TradingEngine() # Loads models
        self.positions = {} # id -> pos
        self.state = self.load_state()
        self.running = True
        
        # Risk Management
        self.consecutive_losses = 0
        self.breaker_active = False
        self.breaker_cooldown = None
        
        logger.info(f"🚀 Mandalorian Phase 3 Initialized (Dry Run: {dry_run})")

    def load_state(self):
        if os.path.exists(CONFIG["STATE_FILE"]):
            try:
                with open(CONFIG["STATE_FILE"], 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load state: {e}")
        return {"balance": 100000.0, "positions": {}, "trade_history": []}

    def save_state(self):
        try:
            with open(CONFIG["STATE_FILE"], 'w') as f:
                json.dump(self.state, f, indent=4, default=str)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def fetch_market_data(self):
        """Fetch latest 500 candles (5m) for analysis"""
        # Using self.engine's fetch method
        df = self.engine.fetch_data('5m', 500)
        if df is None or len(df) < 200:
            return None
            
        # 1. Standard Features
        df = add_all_indicators(df)
        
        # 2. Phase 3 Alpha Features
        df = add_advanced_features(df)
        
        # 3. MTF Context (Resampling)
        df.set_index('timestamp', inplace=True)
        
        # 15m
        df15 = df.resample('15T').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
        df15 = add_all_indicators(df15)
        df15 = add_advanced_features(df15)
        
        # 1h
        df1h = df.resample('1H').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
        df1h = add_all_indicators(df1h)
        df1h = add_advanced_features(df1h)
        
        # Merge
        exclude = ['open', 'high', 'low', 'close', 'volume']
        
        ctx15 = [c for c in df15.columns if c not in exclude]
        df15_renamed = df15[ctx15].rename(columns={c: f"{c}_15m" for c in ctx15})
        df = pd.concat([df, df15_renamed.reindex(df.index, method='ffill')], axis=1)
        
        ctx1h = [c for c in df1h.columns if c not in exclude]
        df1h_renamed = df1h[ctx1h].rename(columns={c: f"{c}_1h" for c in ctx1h})
        df = pd.concat([df, df1h_renamed.reindex(df.index, method='ffill')], axis=1)
        
        df.dropna(inplace=True)
        return df

    def check_signals(self, df):
        if len(self.positions) >= CONFIG["MAX_CONCURRENT_POSITIONS"]:
            return

        # Circuit Breaker Check - DISABLED per user request
        # if self.breaker_active:
        #     if datetime.now() > datetime.fromisoformat(self.breaker_cooldown):
        #         logger.info("🟢 Circuit Breaker Cooldown Expired")
        #         self.breaker_active = False
        #     else:
        #         return

        latest = df.iloc[-1]
        
        # Prepare Features
        # Ensure we have all features in MTF_FEATURE_LIST
        try:
            X_dict = {c: latest.get(c, 0.0) for c in MTF_FEATURE_LIST}
            X = np.array([X_dict[c] for c in MTF_FEATURE_LIST]).reshape(1, -1)
            X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
            
            # Inference
            probas = self.engine.get_ensemble_proba('MTF', X)[0]
            prob_long = float(probas[1])
            prob_short = float(probas[2])
            
            # --- PHASE 3 ADAPTIVE LOGIC ---
            
            # 1. Base Threshold
            threshold = CONFIG["MODEL_CONF_THRESHOLD"]
            
            # 2. Adaptive ATR Filter (Phase 3 Optimization)
            # If Volatility is High (ATR > 1% of Price), Increase Threshold
            atr_pct = latest.get('atr_ratio', 0.0) # Calculated in advanced_features
            if atr_pct == 0 and latest['close'] > 0:
                atr_pct = latest['atr_14'] / latest['close']

            if atr_pct > 0.01: # > 1% Volatility
                threshold += 0.05 # Require 50% confidence
                # logger.info(f"🛡️ High Volatility ({atr_pct:.2%}), raised threshold to {threshold}")
            
            # 3. Hurst Filter (Mandalorian Protocol)
            hurst = latest.get('hurst', 0.5)
            # Falling Knife Protection: Don't buy dip if Hurst is High (Trending Down)
            rsi = latest.get('rsi_14', 50)
            
            signal = None
            conf = 0.0
            
            if prob_long > threshold:
                # Filter Longs
                if rsi < 30 and hurst > 0.6:
                    # logger.info("🛑 Blocked Long (Falling Knife)")
                    pass
                else:
                    signal = 'LONG'
                    conf = prob_long
                    
            elif prob_short > threshold:
                # Filter Shorts
                if rsi > 70 and hurst > 0.6:
                     # logger.info("🛑 Blocked Short (Rocket Catching)")
                     pass
                else:
                    signal = 'SHORT'
                    conf = prob_short
            
            if signal:
                self.open_position(signal, latest['close'], conf)
                
        except Exception as e:
            logger.error(f"Inference Error: {e}")

    def open_position(self, direction, price, confidence):
        pos_id = f"trade_{int(time.time())}"
        
        # Dynamic Sizing (Compounding)
        balance = self.state["balance"]
        size_factor = 0.5 # Validated Phase 2
        # Use simple fixed size for now or % of balance
        trade_val = balance * 0.25 # 25% (Pro-Trader Sizing)
        size_btc = trade_val / price
        
        # Check leverage limits
        # Not implementing full margin check in Dry Run
        
        logger.info(f"🚀 OPEN {direction} @ {price} | Conf: {confidence:.2f}")
        
        self.state["positions"][pos_id] = {
            "entry_time": datetime.now().isoformat(),
            "direction": direction,
            "entry_price": price,
            "size": size_btc,
            "tp": price * (1.015 if direction == 'LONG' else 0.985),
            "sl": price * (0.992 if direction == 'LONG' else 1.008), # 0.8% SL
            "max_duration": datetime.now() + timedelta(hours=CONFIG["MAX_TRADE_DURATION_HOURS"])
        }
        self.save_state()

    def manage_positions(self, current_price, current_time):
        to_close = []
        
        for pid, pos in self.state["positions"].items():
            # Check TP/SL
            pnl_pct = 0
            close_reason = None
            
            if pos["direction"] == 'LONG':
                if current_price >= pos["tp"]:
                    close_reason = "TP"
                    pnl_pct = (pos["tp"] - pos["entry_price"]) / pos["entry_price"]
                elif current_price <= pos["sl"]:
                    close_reason = "SL"
                    pnl_pct = (pos["sl"] - pos["entry_price"]) / pos["entry_price"]
            else:
                if current_price <= pos["tp"]:
                    close_reason = "TP"
                    pnl_pct = (pos["entry_price"] - pos["tp"]) / pos["entry_price"]
                elif current_price >= pos["sl"]:
                    close_reason = "SL"
                    pnl_pct = (pos["entry_price"] - pos["sl"]) / pos["entry_price"]
            
            # Check Time Expiry
            if not close_reason:
                expiry = datetime.fromisoformat(str(pos["max_duration"])) if isinstance(pos["max_duration"], str) else pos["max_duration"]
                if current_time > expiry:
                    close_reason = "EXPIRED"
                    # Mark to market
                    if pos["direction"] == 'LONG':
                        pnl_pct = (current_price - pos["entry_price"]) / pos["entry_price"]
                    else:
                        pnl_pct = (pos["entry_price"] - current_price) / pos["entry_price"]

            if close_reason:
                to_close.append((pid, close_reason, pnl_pct))

        for pid, reason, pnl in to_close:
            self.close_position(pid, reason, pnl, current_price)

    def close_position(self, pid, reason, pnl_pct, limit_price):
        pos = self.state["positions"].pop(pid)
        pnl_val = pnl_pct * pos["size"] * pos["entry_price"]
        
        self.state["balance"] += pnl_val
        self.state["trade_history"].append({
            "id": pid,
            "reason": reason,
            "pnl": pnl_val,
            "pnl_pct": pnl_pct,
            "close_time": datetime.now().isoformat()
        })
        
        logger.info(f"✅ CLOSE {pid} ({reason}) | PnL: {pnl_pct*100:.2f}% (${pnl_val:.2f})")
        
        # Risk Management: Circuit Breaker - DISABLED per user request
        # User chose Option B: Full ROI potential (+120-424%) with manual monitoring
        # Buffer trade losses (-$7.5k/month) are acceptable for maximum returns
        
        # if reason == "SL":
        #     self.consecutive_losses += 1
        #     if self.consecutive_losses >= 2:
        #         logger.warning("🛑 Circuit Breaker Triggered (2 Consecutive Losses)")
        #         logger.warning(f"🚨 Closing ALL {len(self.state['positions'])} open positions for capital protection")
        #         
        #         # CRITICAL FIX: Close all open positions immediately
        #         # This prevents buffer trades from bleeding capital during cooldown
        #         positions_to_close = list(self.state["positions"].keys())
        #         for pos_id in positions_to_close:
        #             if pos_id != pid:  # Don't try to close the position we just closed
        #                 pos = self.state["positions"][pos_id]
        #                 # Force close at current market price
        #                 if pos["direction"] == "LONG":
        #                     forced_pnl = (limit_price - pos["entry_price"]) / pos["entry_price"]
        #                 else:
        #                     forced_pnl = (pos["entry_price"] - limit_price) / pos["entry_price"]
        #                 
        #                 self.close_position(pos_id, "BREAKER_FORCED", forced_pnl, limit_price)
        #         
        #         # Activate breaker cooldown
        #         self.breaker_active = True
        #         self.breaker_cooldown = (datetime.now() + timedelta(hours=4)).isoformat()
        #         self.consecutive_losses = 0
        #         logger.info(f"⏸️  Trading paused for 4 hours until {self.breaker_cooldown}")
        # elif reason == "TP":
        #     self.consecutive_losses = 0 # Reset on win
        # elif reason == "BREAKER_FORCED":
        #     # Don't increment consecutive losses for forced closes
        #     pass
            
        self.save_state()

    def run(self):
        logger.info("⏳ Starting Loop...")
        while self.running:
            try:
                # 1. Get Data
                df = self.fetch_market_data()
                if df is not None:
                    current_price = df['close'].iloc[-1]
                    current_time = df.index[-1]
                    
                    # 2. Manage Existing
                    self.manage_positions(current_price, datetime.now()) # Use wall clock for expiry? Or candle time? Wall clock safer for live.
                    
                    # 3. Check New Signals
                    self.check_signals(df)
                    
                    # 4. Heartbeat
                    if int(time.time()) % 60 == 0:
                        logger.info(f"💓 Alive | Price: {current_price} | Positions: {len(self.state['positions'])}")
                
                # Sleep to align with 5m candles or run frequent?
                # For Phase 3, we check every 1 minute to act fast
                time.sleep(60)
                
            except KeyboardInterrupt:
                logger.info("🛑 Stopping...")
                self.running = False
            except Exception as e:
                logger.error(f"Loop Error: {e}")
                time.sleep(10)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Run without executing real trades")
    args = parser.parse_args()
    
    trader = Phase3Trader(dry_run=args.dry_run)
    trader.run()
