#!/usr/bin/env python3
"""
🌊 LIVE LIQUIDATION SCALPER (V1)
Predicts BTC price moves based on real-time liquidation cascades.
Strategy: Momentum Scalping (Ride the Liquidation Wave)
"""

import websocket
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import threading
import sys

# Configuration
SYMBOL = "BTC"
MOMENTUM_THRESHOLD_USD = 50000  # $50k cumulative liquidations to trigger signal
WINDOW_SECONDS = 60             # Lookback window for accumulation
COOLDOWN_SECONDS = 300          # Wait time after signal

class LiquidationScalper:
    def __init__(self):
        self.ws_url = "wss://api.hyperliquid.xyz/ws"
        self.liquidations = []
        self.running = False
        self.last_signal_time = datetime.min
        
        # Accumulators
        self.short_liq_accum = 0.0  # Buying pressure (Side A)
        self.long_liq_accum = 0.0   # Selling pressure (Side B)
        self.last_cleanup = datetime.now()

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            if 'channel' in data and data['channel'] == 'liquidations':
                liq_data = data['data']
                self.process_liquidation(liq_data)
        except Exception as e:
            pass # Silent error handling for speed

    def on_error(self, ws, error):
        print(f"❌ WebSocket Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print("🔌 Connection closed. Reconnecting...")
        time.sleep(1)
        self.start()

    def on_open(self, ws):
        print(f"✅ Connected! Listening for {SYMBOL} liquidations...")
        subscribe_msg = {
            "method": "subscribe",
            "subscription": {"type": "liquidations", "coin": SYMBOL}
        }
        ws.send(json.dumps(subscribe_msg))

    def process_liquidation(self, data):
        """
        Analyze liquidation event and trigger signals.
        Side 'A' = Ask (Buy) = Short Liquidation -> Bullish
        Side 'B' = Bid (Sell) = Long Liquidation -> Bearish
        """
        try:
            timestamp = datetime.now()
            side = data.get('side') # 'A' or 'B'
            size_usd = float(data.get('px', 0)) * float(data.get('sz', 0))
            price = float(data.get('px', 0))
            
            # Store event
            event = {
                'time': timestamp,
                'side': side,
                'usd': size_usd,
                'price': price
            }
            self.liquidations.append(event)
            
            # Update accumulations
            if side == 'A': # Short Liq (Buy Pressure)
                self.short_liq_accum += size_usd
                print(f"🟢 SHORT LIQ (Buy): ${size_usd:,.0f} @ {price}")
            elif side == 'B': # Long Liq (Sell Pressure)
                self.long_liq_accum += size_usd
                print(f"🔴 LONG LIQ (Sell): ${size_usd:,.0f} @ {price}")
            
            # Clean old data (sliding window)
            self.cleanup_old_events()
            
            # Check for Signals
            self.check_signals(price)
            
        except Exception as e:
            print(f"Error processing: {e}")

    def cleanup_old_events(self):
        """Remove liquidations older than WINDOW_SECONDS"""
        now = datetime.now()
        # Only cleanup every 5 seconds to save CPU
        if (now - self.last_cleanup).total_seconds() < 5:
            return
            
        cutoff = now - timedelta(seconds=WINDOW_SECONDS)
        new_liqs = [x for x in self.liquidations if x['time'] > cutoff]
        self.liquidations = new_liqs
        self.last_cleanup = now
        
        # Re-calculate accumulators from window
        self.short_liq_accum = sum(x['usd'] for x in self.liquidations if x['side'] == 'A')
        self.long_liq_accum = sum(x['usd'] for x in self.liquidations if x['side'] == 'B')

    def check_signals(self, current_price):
        """Generate Buy/Sell signals based on pressure"""
        now = datetime.now()
        
        # Cooldown check
        if (now - self.last_signal_time).total_seconds() < COOLDOWN_SECONDS:
            return

        # LOGIC: Momentum Reversal?
        # Actually, let's try REVERSAL logic.
        # If huge Long Liqs (Sell Pressure), price dips. We BUY the dip (Scalp).
        # If huge Short Liqs (Buy Pressure), price spikes. We SELL the top.
        
        # Let's pivot to REVERSAL (Contrarian Scalping) as it's common in high-freq liq strats.
        # "Liquidation Exhaustion"
        
        if self.long_liq_accum > MOMENTUM_THRESHOLD_USD:
            print(f"\n🚀 SIGNAL: BUY (LONG) | Price: {current_price}")
            print(f"   Reason: Massive Long Liquidations (${self.long_liq_accum:,.0f}) -> Oversold")
            self.last_signal_time = now
            self.reset_accum()
            
        elif self.short_liq_accum > MOMENTUM_THRESHOLD_USD:
            print(f"\n📉 SIGNAL: SELL (SHORT) | Price: {current_price}")
            print(f"   Reason: Massive Short Liquidations (${self.short_liq_accum:,.0f}) -> Overbought")
            self.last_signal_time = now
            self.reset_accum()

    def reset_accum(self):
        self.short_liq_accum = 0
        self.long_liq_accum = 0
        self.liquidations = [] # Clear memory for next burst

    def start(self):
        print(f"🌊 Started Liquidation Scalper for {SYMBOL}")
        print(f"   Threshold: ${MOMENTUM_THRESHOLD_USD:,.0f} in {WINDOW_SECONDS}s")
        ws = websocket.WebSocketApp(
            self.ws_url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )
        ws.run_forever()

if __name__ == "__main__":
    try:
        bot = LiquidationScalper()
        bot.start()
    except KeyboardInterrupt:
        print("\n👋 Stopping scalper...")
