#!/usr/bin/env python3
"""
Hyperliquid Liquidation Collector - Using WebSocket
Based on research: Hyperliquid provides liquidation data via WebSocket feeds
"""

import websocket
import json
import threading
import time
from datetime import datetime
import pandas as pd

class HyperliquidLiquidationCollector:
    """
    Collects real liquidation data from Hyperliquid WebSocket
    """
    
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
            # Liquidations typically come through the "fills" channel
            if 'channel' in data and data['channel'] == 'fills':
                fill_data = data.get('data', {})
                
                # Check if this is a liquidation (usually marked in the fill)
                if fill_data.get('liquidation', False) or fill_data.get('dir') == 'Liquidation':
                    liquidation = {
                        'timestamp': datetime.now(),
                        'coin': fill_data.get('coin', 'BTC'),
                        'price': float(fill_data.get('px', 0)),
                        'size': float(fill_data.get('sz', 0)),
                        'side': fill_data.get('side', 'unknown'),
                        'value_usd': float(fill_data.get('px', 0)) * float(fill_data.get('sz', 0))
                    }
                    
                    self.liquidations.append(liquidation)
                    print(f"🔥 Liquidation: {liquidation['side']} {liquidation['size']} {liquidation['coin']} @ ${liquidation['price']:,.2f}")
                    
        except Exception as e:
            print(f"Error processing message: {e}")
    
    def on_error(self, ws, error):
        """Handle WebSocket errors"""
        print(f"WebSocket error: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close"""
        print(f"WebSocket closed: {close_status_code} - {close_msg}")
        self.running = False
    
    def on_open(self, ws):
        """Handle WebSocket open - subscribe to liquidation feed"""
        print("WebSocket connected!")
        
        # Subscribe to all fills (which includes liquidations)
        subscribe_msg = {
            "method": "subscribe",
            "subscription": {
                "type": "allMids"  # Start with allMids to test connection
            }
        }
        
        ws.send(json.dumps(subscribe_msg))
        print("Subscribed to market data")
        
        # Try to subscribe to fills/trades
        fills_msg = {
            "method": "subscribe",
            "subscription": {
                "type": "trades",
                "coin": "BTC"
            }
        }
        ws.send(json.dumps(fills_msg))
        print("Subscribed to BTC trades")
    
    def start_collection(self, duration_seconds=60):
        """
        Start collecting liquidation data
        
        Args:
            duration_seconds: How long to collect data
        """
        
        print("="*60)
        print("🔥 Hyperliquid Liquidation Collector (WebSocket)")
        print("="*60)
        print(f"Duration: {duration_seconds}s")
        print("Connecting to WebSocket...")
        print("="*60)
        
        self.running = True
        
        # Create WebSocket connection
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )
        
        # Run WebSocket in a thread
        ws_thread = threading.Thread(target=self.ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()
        
        # Wait for specified duration
        time.sleep(duration_seconds)
        
        # Close connection
        self.ws.close()
        
        print("\n" + "="*60)
        print(f"✅ Collection complete! Found {len(self.liquidations)} liquidations")
        print("="*60)
        
        return self.liquidations
    
    def get_liquidation_heatmap(self, liquidations, current_price):
        """
        Create liquidation heatmap from collected data
        """
        
        if not liquidations:
            return pd.DataFrame()
        
        df = pd.DataFrame(liquidations)
        
        # Group by price levels (round to nearest $100)
        df['price_level'] = (df['price'] / 100).round() * 100
        
        # Aggregate by price level
        heatmap = df.groupby('price_level').agg({
            'value_usd': 'sum',
            'size': 'sum',
            'timestamp': 'count'
        }).rename(columns={'timestamp': 'count'})
        
        # Calculate density score
        heatmap['density_score'] = heatmap['value_usd'] / heatmap['value_usd'].max()
        
        # Add distance from current price
        heatmap['distance_pct'] = ((heatmap.index - current_price) / current_price) * 100
        
        return heatmap.sort_values('density_score', ascending=False)

# Test
if __name__ == "__main__":
    collector = HyperliquidLiquidationCollector()
    
    # Collect for 30 seconds
    liquidations = collector.start_collection(duration_seconds=30)
    
    if liquidations:
        print(f"\n📊 Liquidation Summary:")
        df = pd.DataFrame(liquidations)
        print(f"   Total liquidations: {len(df)}")
        print(f"   Total value: ${df['value_usd'].sum():,.2f}")
        print(f"   Avg size: {df['size'].mean():.2f} BTC")
        
        # Show heatmap
        from working_collectors import WorkingCollectors
        wc = WorkingCollectors()
        current_price = wc.get_current_price()
        
        heatmap = collector.get_liquidation_heatmap(liquidations, current_price)
        if not heatmap.empty:
            print(f"\n🗺️  Liquidation Heatmap (Top 5):")
            for price_level, row in heatmap.head().iterrows():
                print(f"   ${price_level:,.0f}: {row['count']} liqs, ${row['value_usd']:,.0f} ({row['distance_pct']:+.2f}%)")
    else:
        print("\n⚠️  No liquidations detected in this period")
        print("Note: Liquidations may be rare or WebSocket subscription needs adjustment")
