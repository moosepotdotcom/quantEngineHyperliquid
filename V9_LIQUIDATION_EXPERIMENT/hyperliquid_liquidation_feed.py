#!/usr/bin/env python3
"""
Hyperliquid Liquidation Feed - Real-Time Data
Access liquidation events via WebSocket
"""

import websocket
import json
import pandas as pd
from datetime import datetime
import threading
import time

class HyperliquidLiquidationFeed:
    """Real-time liquidation data from Hyperliquid WebSocket"""
    
    def __init__(self):
        self.ws_url = "wss://api.hyperliquid.xyz/ws"
        self.liquidations = []
        self.ws = None
        self.running = False
        
    def on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            
            # Check if this is a liquidation event
            if 'channel' in data and data['channel'] == 'liquidations':
                liq_data = data['data']
                
                # Parse liquidation
                liquidation = {
                    'timestamp': datetime.now(),
                    'coin': liq_data.get('coin'),
                    'side': liq_data.get('side'),  # 'A' = ask (long liq), 'B' = bid (short liq)
                    'px': float(liq_data.get('px', 0)),
                    'sz': float(liq_data.get('sz', 0)),
                    'liquidator': liq_data.get('liquidator'),
                    'liquidated': liq_data.get('liquidated')
                }
                
                self.liquidations.append(liquidation)
                
                print(f"🔥 Liquidation: {liquidation['coin']} {liquidation['side']} "
                      f"${liquidation['px']:.2f} Size: {liquidation['sz']:.4f}")
                
        except Exception as e:
            print(f"❌ Error parsing message: {e}")
    
    def on_error(self, ws, error):
        print(f"❌ WebSocket Error: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        print(f"🔌 WebSocket Closed: {close_status_code} - {close_msg}")
        self.running = False
    
    def on_open(self, ws):
        print("✅ WebSocket Connected")
        
        # Subscribe to liquidation feed
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
    
    def start(self, duration_seconds=60):
        """Start listening to liquidation feed"""
        print(f"🚀 Starting Liquidation Feed (listening for {duration_seconds}s)")
        
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )
        
        # Run in thread with timeout
        def run_with_timeout():
            self.ws.run_forever()
        
        ws_thread = threading.Thread(target=run_with_timeout)
        ws_thread.daemon = True
        ws_thread.start()
        
        # Wait for duration
        time.sleep(duration_seconds)
        
        # Close connection
        if self.ws:
            self.ws.close()
        
        # Return collected liquidations
        return pd.DataFrame(self.liquidations)

def test_liquidation_feed():
    """Test the liquidation feed"""
    print("🔍 Testing Hyperliquid Liquidation Feed")
    print("="*70)
    
    feed = HyperliquidLiquidationFeed()
    
    # Listen for 60 seconds
    df_liqs = feed.start(duration_seconds=60)
    
    if len(df_liqs) > 0:
        print(f"\n✅ Captured {len(df_liqs)} liquidations!")
        print(f"\n📊 Sample:")
        print(df_liqs.head(10))
        
        # Save
        df_liqs.to_csv('realtime_liquidations_sample.csv', index=False)
        print(f"\n💾 Saved to realtime_liquidations_sample.csv")
        
        # Statistics
        print(f"\n📈 Statistics:")
        print(f"   Total liquidations: {len(df_liqs)}")
        print(f"   Long liquidations (A): {len(df_liqs[df_liqs['side']=='A'])}")
        print(f"   Short liquidations (B): {len(df_liqs[df_liqs['side']=='B'])}")
        print(f"   Total size: ${df_liqs['sz'].sum():.2f}")
        print(f"   Avg price: ${df_liqs['px'].mean():.2f}")
    else:
        print("\n⚠️  No liquidations captured in 60 seconds")
        print("   This is normal if market is quiet")
        print("   Try running during volatile periods")

if __name__ == "__main__":
    # Install websocket-client if needed
    try:
        import websocket
    except ImportError:
        print("Installing websocket-client...")
        import subprocess
        subprocess.check_call(["pip3", "install", "websocket-client"])
        import websocket
    
    test_liquidation_feed()
