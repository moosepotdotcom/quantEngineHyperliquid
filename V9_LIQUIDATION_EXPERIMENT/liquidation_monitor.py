#!/usr/bin/env python3
"""
Liquidation Monitor - Continuous Background Service
Monitors liquidations 24/7 and builds real-time heatmap
"""

import websocket
import json
import pandas as pd
from datetime import datetime, timedelta
import threading
import time
import os
from collections import deque

class LiquidationMonitor:
    """24/7 Liquidation monitoring service"""
    
    def __init__(self, data_dir='liquidation_data'):
        self.ws_url = "wss://api.hyperliquid.xyz/ws"
        self.data_dir = data_dir
        self.ws = None
        self.running = False
        
        # In-memory buffer (last 1000 liquidations)
        self.recent_liquidations = deque(maxlen=1000)
        
        # Statistics
        self.stats = {
            'total_liquidations': 0,
            'long_liquidations': 0,
            'short_liquidations': 0,
            'total_volume': 0,
            'last_liquidation': None,
            'start_time': datetime.now()
        }
        
        # Create data directory
        os.makedirs(data_dir, exist_ok=True)
        
        # Load existing data
        self.load_historical_data()
    
    def load_historical_data(self):
        """Load previously collected liquidation data"""
        today_file = os.path.join(self.data_dir, f"liquidations_{datetime.now().strftime('%Y%m%d')}.csv")
        
        if os.path.exists(today_file):
            df = pd.read_csv(today_file)
            print(f"📂 Loaded {len(df)} existing liquidations from today")
            
            for _, row in df.iterrows():
                self.recent_liquidations.append(row.to_dict())
    
    def save_liquidation(self, liq_data):
        """Save liquidation to daily file"""
        today_file = os.path.join(self.data_dir, f"liquidations_{datetime.now().strftime('%Y%m%d')}.csv")
        
        df = pd.DataFrame([liq_data])
        
        if os.path.exists(today_file):
            df.to_csv(today_file, mode='a', header=False, index=False)
        else:
            df.to_csv(today_file, index=False)
    
    def on_message(self, ws, message):
        """Handle incoming liquidation events"""
        try:
            data = json.loads(message)
            
            if 'channel' in data and data['channel'] == 'liquidations':
                liq_event = data['data']
                
                # Parse liquidation
                liquidation = {
                    'timestamp': datetime.now().isoformat(),
                    'coin': liq_event.get('coin', 'BTC'),
                    'side': liq_event.get('side'),
                    'price': float(liq_event.get('px', 0)),
                    'size': float(liq_event.get('sz', 0)),
                    'liquidator': liq_event.get('liquidator', ''),
                    'liquidated': liq_event.get('liquidated', '')
                }
                
                # Update stats
                self.stats['total_liquidations'] += 1
                self.stats['total_volume'] += liquidation['size']
                self.stats['last_liquidation'] = liquidation
                
                if liquidation['side'] == 'A':
                    self.stats['long_liquidations'] += 1
                else:
                    self.stats['short_liquidations'] += 1
                
                # Add to buffer
                self.recent_liquidations.append(liquidation)
                
                # Save to disk
                self.save_liquidation(liquidation)
                
                # Log
                side_name = "LONG" if liquidation['side'] == 'A' else "SHORT"
                print(f"🔥 {datetime.now().strftime('%H:%M:%S')} | "
                      f"{side_name} Liquidation | "
                      f"${liquidation['price']:.2f} | "
                      f"Size: {liquidation['size']:.4f} BTC")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def on_error(self, ws, error):
        print(f"❌ WebSocket Error: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        print(f"🔌 Connection closed. Reconnecting in 5s...")
        self.running = False
        time.sleep(5)
        if self.should_run:
            self.start()
    
    def on_open(self, ws):
        print(f"✅ Connected to Hyperliquid at {datetime.now().strftime('%H:%M:%S')}")
        
        # Subscribe to liquidations
        subscribe_msg = {
            "method": "subscribe",
            "subscription": {
                "type": "liquidations",
                "coin": "BTC"
            }
        }
        
        ws.send(json.dumps(subscribe_msg))
        print("📡 Subscribed to BTC liquidations")
        self.running = True
    
    def start(self):
        """Start monitoring (runs forever)"""
        self.should_run = True
        
        print("🚀 Starting Liquidation Monitor")
        print("="*70)
        print(f"   Data directory: {self.data_dir}")
        print(f"   Monitoring: BTC liquidations")
        print(f"   Press Ctrl+C to stop")
        print("="*70)
        
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )
        
        # Run forever
        self.ws.run_forever()
    
    def stop(self):
        """Stop monitoring"""
        self.should_run = False
        if self.ws:
            self.ws.close()
        
        print("\n📊 Final Statistics:")
        print(f"   Total liquidations: {self.stats['total_liquidations']}")
        print(f"   Long liquidations: {self.stats['long_liquidations']}")
        print(f"   Short liquidations: {self.stats['short_liquidations']}")
        print(f"   Total volume: {self.stats['total_volume']:.2f} BTC")
        print(f"   Runtime: {datetime.now() - self.stats['start_time']}")
    
    def get_recent_liquidations(self, minutes=60):
        """Get liquidations from last N minutes"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        
        recent = [
            liq for liq in self.recent_liquidations
            if datetime.fromisoformat(liq['timestamp']) > cutoff
        ]
        
        return pd.DataFrame(recent)
    
    def get_liquidation_rate(self, minutes=10):
        """Get liquidations per minute in last N minutes"""
        df = self.get_recent_liquidations(minutes)
        
        if len(df) == 0:
            return 0
        
        return len(df) / minutes

if __name__ == "__main__":
    # Install websocket-client if needed
    try:
        import websocket
    except ImportError:
        print("Installing websocket-client...")
        import subprocess
        subprocess.check_call(["pip3", "install", "websocket-client"])
        import websocket
    
    monitor = LiquidationMonitor()
    
    try:
        monitor.start()
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping monitor...")
        monitor.stop()
