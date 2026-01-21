#!/usr/bin/env python3
"""
🌊 HYPERLIQUID SCALPER V2 (Live Implementation)
Strategy: Reversal after Liquidation Exhaustion
"""

import websocket
import json
import time
import threading
from datetime import datetime, timedelta
from collections import deque
import numpy as np

# Import Execution Engine
try:
    from hyperliquid_live_trader import HyperliquidTrader
except ImportError:
    print("⚠️ Execution Engine not found. Running in Inference Mode.")
    HyperliquidTrader = None

# Configuration
SYMBOL = "BTC"
WS_URL = "wss://api.hyperliquid.xyz/ws"

# Strategy Parameters
LIQ_WINDOW_SECONDS = 60       # Time window to accumulate liquidations
LIQ_THRESHOLD_USD = 50000     # $50k cumulative liquidations to trigger signal
COOLDOWN_SECONDS = 300        # 5 minutes between trades
CONFIDENCE_THRESHOLD = 0.6    # Base confidence

class LiquidationEngine:
    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        self.ws = None
        
        # Data Structures
        self.short_liqs = deque() # Stores (timestamp, usd_value)
        self.long_liqs = deque()  # Stores (timestamp, usd_value)
        self.last_signal_time = datetime.min
        
        # Execution
        self.trader = None
        if not dry_run and HyperliquidTrader:
            try:
                self.trader = HyperliquidTrader(testnet=False) # Use Mainnet for real liquidations
                print("✅ Execution connection established (Mainnet)")
            except Exception as e:
                print(f"❌ Execution connection failed: {e}")
                
    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            channel = data.get('channel')
            
            if channel == 'trades':
                trades = data.get('data', [])
                for trade in trades:
                    # Check for liquidation
                    if 'liquidation' in trade:
                        self.process_liquidation(trade)
                        
        except Exception as e:
            print(f"Error: {e}")

    def process_liquidation(self, trade):
        try:
            now = datetime.now()
            price = float(trade['px'])
            size = float(trade['sz'])
            usd_value = price * size
            side = trade['side'] # 'B' = Short Liq, 'A' = Long Liq
            
            # Log
            type_str = "🟢 SHORT (Buy)" if side == 'B' else "🔴 LONG (Sell)"
            print(f"💦 {type_str} Liq: ${usd_value:,.0f} @ {price}")
            
            # Store in deque
            if side == 'B':
                self.short_liqs.append((now, usd_value))
            else:
                self.long_liqs.append((now, usd_value))
                
            # Clean old
            self.cleanup(now)
            
            # Check Signal
            self.check_signal(price)
            
        except Exception as e:
            print(f"Processing error: {e}")

    def cleanup(self, now):
        cutoff = now - timedelta(seconds=LIQ_WINDOW_SECONDS)
        
        while self.short_liqs and self.short_liqs[0][0] < cutoff:
            self.short_liqs.popleft()
            
        while self.long_liqs and self.long_liqs[0][0] < cutoff:
            self.long_liqs.popleft()

    def check_signal(self, current_price):
        now = datetime.now()
        
        # Cooldown check
        if (now - self.last_signal_time).total_seconds() < COOLDOWN_SECONDS:
            return

        # Sum values
        total_short_liq = sum(x[1] for x in self.short_liqs)
        total_long_liq = sum(x[1] for x in self.long_liqs)
        
        signal = None
        
        # STRATEGY LOGIC: REVERSAL
        # If massive Long Liqs (Selling) -> Oversold -> BUY
        if total_long_liq > LIQ_THRESHOLD_USD:
            confidence = min(0.9, 0.6 + (total_long_liq / LIQ_THRESHOLD_USD) * 0.1)
            signal = {
                'model': 'LIQ_REVERSAL',
                'direction': 'LONG',
                'price': current_price,
                'confidence': confidence,
                'reason': f"Long Liqs ${total_long_liq:,.0f} > ${LIQ_THRESHOLD_USD:,.0f}"
            }
            
        # If massive Short Liqs (Buying) -> Overbought -> SELL
        elif total_short_liq > LIQ_THRESHOLD_USD:
            confidence = min(0.9, 0.6 + (total_short_liq / LIQ_THRESHOLD_USD) * 0.1)
            signal = {
                'model': 'LIQ_REVERSAL',
                'direction': 'SHORT',
                'price': current_price,
                'confidence': confidence,
                'reason': f"Short Liqs ${total_short_liq:,.0f} > ${LIQ_THRESHOLD_USD:,.0f}"
            }
            
        if signal:
            print(f"\n🚨 SIGNAL GENERATED: {signal['direction']} @ {signal['price']}")
            print(f"   Reason: {signal['reason']}")
            
            self.last_signal_time = now
            self.execute(signal)
            
            # Clear accumulators to prevent double triggering
            self.short_liqs.clear()
            self.long_liqs.clear()

    def execute(self, signal):
        if self.dry_run:
            print(f"   [DRY RUN] Would execute {signal['direction']}")
        else:
            if self.trader:
                print(f"   [LIVE] Forwarding to Execution Engine...")
                self.trader.execute_signal(signal)
                
    def start(self):
        print(f"🌊 Starting Hyperliquid Scalper V2")
        print(f"   Mode: {'DRY RUN' if self.dry_run else 'LIVE TRADING'}")
        print(f"   Threshold: ${LIQ_THRESHOLD_USD:,.0f} / {LIQ_WINDOW_SECONDS}s")
        
        websocket.enableTrace(False)
        self.ws = websocket.WebSocketApp(WS_URL,
                                    on_message=self.on_message,
                                    on_error=lambda ws, e: print(f"Error: {e}"),
                                    on_close=lambda ws, c, m: print("Closed"),
                                    on_open=lambda ws: self.on_open(ws))
        self.ws.run_forever()

    def on_open(self, ws):
        print("🔗 Connected to Data Feed")
        msg = {"method": "subscribe", "subscription": {"type": "trades", "coin": SYMBOL}}
        ws.send(json.dumps(msg))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true', help='Enable LIVE execution (Real Money)')
    args = parser.parse_args()
    
    # Dry run by default unless --live is passed
    dry_run = not args.live
    
    engine = LiquidationEngine(dry_run=dry_run)
    try:
        engine.start()
    except KeyboardInterrupt:
        print("\n👋 Stopping...")
