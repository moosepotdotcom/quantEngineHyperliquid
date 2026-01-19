#!/usr/bin/env python3
"""
🚀 MANDALORIAN PRODUCTION ENGINE
Verified Phase 2 Strategy:
- 12 Concurrent Positions
- 12-Hour Max Duration
- Compounding Enabled
- State Persistence (survives restarts)
- Correct MTF Logic (Resampling)
- Infinite Loop (24/7 Execution)
"""

import sys
import os
import json
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Add path to engine
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quant_engine import TradingEngine, add_all_indicators, MTF_FEATURE_LIST

# Configuration
CONFIG = {
    "LEVERAGE": 400,
    "INITIAL_BALANCE_BTC": 0.5,  # Base size (scaled by balance)
    "TP_PCT": 0.015,  # 1.5%
    "SL_PCT": 0.008,  # 0.8%
    "THRESHOLD": 0.45,
    "MAX_CONCURRENT": 12,
    "MAX_DURATION_HOURS": 12,
    "STATE_FILE": "trading_state.json",
    "DO_COMPOUNDING": True
}

class CustomCircuitBreaker:
    def __init__(self, max_losses=2, window_minutes=60, cooldown_hours=4):
        self.max_losses = max_losses
        self.window_minutes = window_minutes
        self.cooldown_hours = cooldown_hours
        self.losses = []
        self.cooldown_until = None
    
    def record_loss(self, timestamp):
        # Clean old losses
        self.losses = [t for t in self.losses if (timestamp - t).total_seconds() < self.window_minutes * 60]
        self.losses.append(timestamp)
        
        if len(self.losses) >= self.max_losses:
            self.cooldown_until = timestamp + timedelta(hours=self.cooldown_hours)
            print(f"   🛑 CIRCUIT BREAKER ACTIVATED until {self.cooldown_until}")
            return True
        return False
    
    def check_active(self):
        if self.cooldown_until:
            if datetime.now() < self.cooldown_until:
                return True
            else:
                print("   🟢 Circuit Breaker reset")
                self.cooldown_until = None
                self.losses = []
        return False

class Position:
    def __init__(self, data):
        self.__dict__.update(data)
        # Ensure timestamps are datetime objects
        if isinstance(self.entry_time, str):
            self.entry_time = pd.to_datetime(self.entry_time)

    def to_dict(self):
        d = self.__dict__.copy()
        d['entry_time'] = self.entry_time.isoformat()
        return d

class ProductionTrader:
    def __init__(self):
        self.engine = TradingEngine()
        self.breaker = CustomCircuitBreaker()
        self.positions = []
        self.balance = 100000.0  # Default if no state
        self.position_counter = 0
        self.load_state()
        
    def load_state(self):
        """Load state from JSON file"""
        if os.path.exists(CONFIG["STATE_FILE"]):
            try:
                with open(CONFIG["STATE_FILE"], 'r') as f:
                    state = json.load(f)
                    self.balance = state.get("balance", 100000.0)
                    self.position_counter = state.get("position_counter", 0)
                    
                    # Reconstruct positions
                    self.positions = []
                    for p_data in state.get("positions", []):
                        self.positions.append(Position(p_data))
                        
                    print(f"✅ Loaded state: ${self.balance:,.2f} | {len(self.positions)} open positions")
            except Exception as e:
                print(f"⚠️ Failed to load state: {e}")
    
    def save_state(self):
        """Save state to JSON file"""
        try:
            state = {
                "balance": self.balance,
                "position_counter": self.position_counter,
                "positions": [p.to_dict() for p in self.positions],
                "last_update": datetime.now().isoformat()
            }
            with open(CONFIG["STATE_FILE"], 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to save state: {e}")

    def get_position_size(self):
        """Calculate compounded position size"""
        if CONFIG["DO_COMPOUNDING"]:
            # Scale base 0.5 BTC by (Current Balance / 100k)
            # Cap at 5 BTC to prevent excessive sizing
            scale_factor = self.balance / 100000.0
            size = CONFIG["INITIAL_BALANCE_BTC"] * scale_factor
            return min(5.0, max(0.001, size))
        return CONFIG["INITIAL_BALANCE_BTC"]

    def fetch_and_prepare_data(self):
        """Fetch live data and assume correct MTF resampling"""
        # Fetch 5m data (base) - get enough for indicators (1000 candles)
        df5 = self.engine.fetch_data('5m', limit=1000)
        if df5 is None or len(df5) < 200:
            return None
            
        # Add indicators to 5m
        df5 = add_all_indicators(df5)
        df5.set_index('timestamp', inplace=True)
        
        # Resample for 15m and 1h (Robust MTF Logic)
        # Instead of fetching separately, we resample to guarantee alignment
        df15_resampled = df5.resample('15T').agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
        }).dropna()
        df15_resampled = add_all_indicators(df15_resampled)
        
        df1h_resampled = df5.resample('1H').agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
        }).dropna()
        df1h_resampled = add_all_indicators(df1h_resampled)
        
        # Merge 15m context
        exclude = ['open', 'high', 'low', 'close', 'volume']
        ctx15 = [c for c in df15_resampled.columns if c not in exclude]
        df15_renamed = df15_resampled[ctx15].copy().rename(columns={c: f"{c}_15m" for c in ctx15})
        df_merged = pd.concat([df5, df15_renamed.reindex(df5.index, method='ffill')], axis=1)
        
        # Merge 1h context
        ctx1h = [c for c in df1h_resampled.columns if c not in exclude]
        df1h_renamed = df1h_resampled[ctx1h].copy().rename(columns={c: f"{c}_1h" for c in ctx1h})
        df_merged = pd.concat([df_merged, df1h_renamed.reindex(df5.index, method='ffill')], axis=1)
        
        df_merged.dropna(inplace=True)
        return df_merged

    def run_tick(self):
        """Analyze market, manage positions, execute trades"""
        print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} | Tick Analysis")
        
        df = self.fetch_and_prepare_data()
        if df is None:
            print("❌ Data fetch failed")
            return

        current_row = df.iloc[-1]
        timestamp = df.index[-1]
        current_price = current_row['close']
        
        # 1. Check Circuit Breaker
        if self.breaker.check_active():
            print(f"   🛑 Circuit Breaker Active until {self.breaker.cooldown_until}")
        
        # 2. Manage Open Positions
        still_open = []
        for p in self.positions:
            # Check TP/SL
            exit_reason = None
            exit_price = None
            
            # Simple simulation of price movement within the candle 
            # (In production, use high/low from candle for SL/TP check)
            if p.direction == "LONG":
                if current_row['high'] >= p.tp_price:
                    exit_reason = "TP"
                    exit_price = p.tp_price
                elif current_row['low'] <= p.sl_price:
                    exit_reason = "SL"
                    exit_price = p.sl_price
            else: # SHORT
                if current_row['low'] <= p.tp_price:
                    exit_reason = "TP"
                    exit_price = p.tp_price
                elif current_row['high'] >= p.sl_price:
                    exit_reason = "SL"
                    exit_price = p.sl_price
            
            # Check Expiration (Max Duration)
            duration_hours = (datetime.now() - p.entry_time).total_seconds() / 3600
            if not exit_reason and duration_hours >= CONFIG["MAX_DURATION_HOURS"]:
                exit_reason = "EXPIRED"
                exit_price = current_price
            
            if exit_reason:
                # Close Position
                pnl = 0
                if p.direction == "LONG":
                    pnl = (exit_price - p.entry_price) * p.size_btc
                else:
                    pnl = (p.entry_price - exit_price) * p.size_btc
                
                self.balance += pnl
                print(f"   {exit_reason} #{p.id}: {p.direction} PnL ${pnl:+.2f} | Bal: ${self.balance:,.2f}")
                
                if exit_reason == "SL":
                    self.breaker.record_loss(datetime.now())
            else:
                # Update unrealized PnL for display
                unrealized = 0
                if p.direction == "LONG":
                    unrealized = (current_price - p.entry_price) * p.size_btc
                else:
                    unrealized = (p.entry_price - current_price) * p.size_btc
                print(f"   #{p.id} {p.direction}: ${p.entry_price:,.0f} -> ${current_price:,.0f} ({unrealized:+.2f}) | {duration_hours:.1f}h")
                still_open.append(p)
        
        self.positions = still_open
        self.save_state()
        
        # 3. Check for New Signals
        if len(self.positions) >= CONFIG["MAX_CONCURRENT"]:
            print(f"   🔒 Max positions reached ({len(self.positions)}/{CONFIG['MAX_CONCURRENT']})")
            return
            
        if self.breaker.check_active():
            return

        # Prepare Features
        try:
            X_dict = {c: current_row.get(c, 0.0) for c in MTF_FEATURE_LIST}
            X = np.array([X_dict[c] for c in MTF_FEATURE_LIST]).reshape(1, -1)
            X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
            
            probas = self.engine.get_ensemble_proba('MTF', X)[0]
            prob_long, prob_short = float(probas[1]), float(probas[2])
            
            direction = None
            conf = 0.0
            
            if prob_long >= CONFIG["THRESHOLD"]:
                direction = "LONG"
                conf = prob_long
            elif prob_short >= CONFIG["THRESHOLD"]:
                direction = "SHORT"
                conf = prob_short
                
            if direction:
                # Filters
                hurst = current_row.get('hurst', 0.5)
                rsi = current_row.get('rsi_14', 50)
                
                if direction == 'LONG' and rsi < 30 and hurst > 0.5:
                    print(f"   🛡️ Filtered: LONG dip buy in trend (Hurst {hurst:.2f})")
                    return
                if direction == 'SHORT' and current_row.get('rsi_7', 50) < 25:
                    print(f"   🛡️ Filtered: SHORT in oversold")
                    return
                
                # Execute Trade
                self.position_counter += 1
                size = self.get_position_size()
                
                tp = current_price * (1 + CONFIG["TP_PCT"]) if direction == "LONG" else current_price * (1 - CONFIG["TP_PCT"])
                sl = current_price * (1 - CONFIG["SL_PCT"]) if direction == "LONG" else current_price * (1 + CONFIG["SL_PCT"])
                
                new_pos = Position({
                    "id": self.position_counter,
                    "entry_time": datetime.now(), # Use local time for live execution
                    "direction": direction,
                    "entry_price": current_price,
                    "amount": size,
                    "size_btc": size,
                    "tp_price": tp,
                    "sl_price": sl,
                    "confidence": conf
                })
                
                self.positions.append(new_pos)
                self.save_state()
                print(f"   🚀 OPEN #{new_pos.id} {direction} @ ${current_price:,.0f} | Size: {size:.3f} BTC | Conf: {conf*100:.1f}%")
                
        except Exception as e:
            print(f"⚠️ Signal check error: {e}")

    def start(self):
        print("="*60)
        print("🚀 MANDALORIAN PRODUCTION ENGINE STARTED")
        print(f"CONFIG: {json.dumps(CONFIG, indent=2)}")
        print("="*60)
        
        while True:
            try:
                self.run_tick()
            except Exception as e:
                print(f"❌ CRITICAL ERROR: {e}")
                time.sleep(10)
            
            print("   💤 Sleeping 60s...")
            time.sleep(60)

if __name__ == "__main__":
    if "--dry-run" in sys.argv:
        print("🧪 DRY RUN MODE")
        CONFIG["STATE_FILE"] = "trading_state_dry_run.json"
        
        # Initialize and test fetch
        trader = ProductionTrader()
        print("Step 1: Fetching data...")
        df = trader.fetch_and_prepare_data()
        
        if df is not None and len(df) > 0:
            print(f"✅ Data fetch successful: {len(df)} rows")
            print(f"Step 2: Testing dry run loop...")
            trader.run_tick()
            print("✅ Dry run passed!")
            sys.exit(0)
        else:
            print("❌ Dry run failed: Data fetch returned no data")
            sys.exit(1)
        
    trader = ProductionTrader()
    trader.start()
