#!/usr/bin/env python3
"""
Hyperliquid Order Flow & Order Book Tracker
Tracks real-time order book depth, imbalances, and large orders
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime
import time

class OrderFlowTracker:
    """
    Tracks order book depth and flow for BTC perpetuals
    
    Features:
    - Bid/Ask imbalance
    - Order book depth at key levels
    - Large order detection
    - Aggressive buy/sell ratio
    """
    
    def __init__(self):
        self.base_url = "https://api.hyperliquid.xyz/info"
        self.session = requests.Session()
        
    def get_orderbook(self, symbol="BTC", depth=20):
        """
        Get current order book snapshot
        
        Returns:
            Dict with bids and asks
        """
        
        payload = {
            "type": "l2Book",
            "coin": symbol
        }
        
        try:
            response = self.session.post(self.base_url, json=payload, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            # Parse order book - levels is [bids_array, asks_array]
            if 'levels' in data and len(data['levels']) >= 2:
                bids_raw = data['levels'][0]  # First array is bids
                asks_raw = data['levels'][1]  # Second array is asks
                
                # Convert to [[price, size], ...] format
                bids = [[float(level['px']), float(level['sz'])] for level in bids_raw[:depth]]
                asks = [[float(level['px']), float(level['sz'])] for level in asks_raw[:depth]]
                
                return {
                    'bids': bids,
                    'asks': asks,
                    'timestamp': datetime.now()
                }
            else:
                return {'bids': [], 'asks': [], 'timestamp': datetime.now()}
            
        except Exception as e:
            print(f"Error fetching order book: {e}")
            return {'bids': [], 'asks': [], 'timestamp': datetime.now()}
    
    def calculate_order_imbalance(self, orderbook, levels=10):
        """
        Calculate bid/ask imbalance
        
        Args:
            orderbook: Order book data
            levels: Number of levels to consider
            
        Returns:
            Imbalance ratio (-1 to 1, positive = bullish)
        """
        
        if not orderbook['bids'] or not orderbook['asks']:
            return 0.0
        
        # Sum volume for top N levels
        bid_volume = sum([bid[1] for bid in orderbook['bids'][:levels]])
        ask_volume = sum([ask[1] for ask in orderbook['asks'][:levels]])
        
        total_volume = bid_volume + ask_volume
        if total_volume == 0:
            return 0.0
        
        # Calculate imbalance (-1 to 1)
        imbalance = (bid_volume - ask_volume) / total_volume
        
        return imbalance
    
    def detect_large_orders(self, orderbook, threshold_btc=10):
        """
        Detect large orders in the book
        
        Args:
            orderbook: Order book data
            threshold_btc: Minimum size to be considered "large"
            
        Returns:
            Dict with large bid/ask info
        """
        
        large_bids = [bid for bid in orderbook['bids'] if bid[1] >= threshold_btc]
        large_asks = [ask for ask in orderbook['asks'] if ask[1] >= threshold_btc]
        
        return {
            'large_bid_count': len(large_bids),
            'large_ask_count': len(large_asks),
            'large_bid_total': sum([bid[1] for bid in large_bids]),
            'large_ask_total': sum([ask[1] for ask in large_asks]),
            'largest_bid': max([bid[1] for bid in large_bids]) if large_bids else 0,
            'largest_ask': max([ask[1] for ask in large_asks]) if large_asks else 0,
        }
    
    def calculate_depth_metrics(self, orderbook, current_price, distance_pct=0.01):
        """
        Calculate order book depth within distance from current price
        
        Args:
            orderbook: Order book data
            current_price: Current market price
            distance_pct: Distance from price (e.g., 0.01 = 1%)
            
        Returns:
            Dict with depth metrics
        """
        
        upper_bound = current_price * (1 + distance_pct)
        lower_bound = current_price * (1 - distance_pct)
        
        # Filter orders within range
        nearby_bids = [bid for bid in orderbook['bids'] if bid[0] >= lower_bound]
        nearby_asks = [ask for ask in orderbook['asks'] if ask[0] <= upper_bound]
        
        bid_depth = sum([bid[1] for bid in nearby_bids])
        ask_depth = sum([ask[1] for ask in nearby_asks])
        
        return {
            'bid_depth_1pct': bid_depth,
            'ask_depth_1pct': ask_depth,
            'depth_ratio': bid_depth / ask_depth if ask_depth > 0 else 0,
            'total_depth': bid_depth + ask_depth
        }
    
    def get_orderflow_features(self, current_price):
        """
        Generate order flow features for ML model
        
        Returns:
            Dictionary of features
        """
        
        # Get order book
        orderbook = self.get_orderbook()
        
        if not orderbook['bids'] or not orderbook['asks']:
            return self._empty_features()
        
        # Calculate features
        imbalance_5 = self.calculate_order_imbalance(orderbook, levels=5)
        imbalance_10 = self.calculate_order_imbalance(orderbook, levels=10)
        imbalance_20 = self.calculate_order_imbalance(orderbook, levels=20)
        
        large_orders = self.detect_large_orders(orderbook, threshold_btc=10)
        depth_metrics = self.calculate_depth_metrics(orderbook, current_price, distance_pct=0.01)
        
        # Spread
        best_bid = orderbook['bids'][0][0] if orderbook['bids'] else 0
        best_ask = orderbook['asks'][0][0] if orderbook['asks'] else 0
        spread = (best_ask - best_bid) / current_price if best_bid > 0 and best_ask > 0 else 0
        
        features = {
            # Imbalance metrics
            'ob_imbalance_5': imbalance_5,
            'ob_imbalance_10': imbalance_10,
            'ob_imbalance_20': imbalance_20,
            
            # Large orders
            'ob_large_bid_count': large_orders['large_bid_count'],
            'ob_large_ask_count': large_orders['large_ask_count'],
            'ob_large_bid_total': large_orders['large_bid_total'],
            'ob_large_ask_total': large_orders['large_ask_total'],
            'ob_largest_bid': large_orders['largest_bid'],
            'ob_largest_ask': large_orders['largest_ask'],
            
            # Depth metrics
            'ob_bid_depth': depth_metrics['bid_depth_1pct'],
            'ob_ask_depth': depth_metrics['ask_depth_1pct'],
            'ob_depth_ratio': depth_metrics['depth_ratio'],
            'ob_total_depth': depth_metrics['total_depth'],
            
            # Spread
            'ob_spread_pct': spread * 100,
            
            # Best bid/ask
            'ob_best_bid': best_bid,
            'ob_best_ask': best_ask,
        }
        
        return features
    
    def _empty_features(self):
        """Return empty features when no data available"""
        return {
            'ob_imbalance_5': 0,
            'ob_imbalance_10': 0,
            'ob_imbalance_20': 0,
            'ob_large_bid_count': 0,
            'ob_large_ask_count': 0,
            'ob_large_bid_total': 0,
            'ob_large_ask_total': 0,
            'ob_largest_bid': 0,
            'ob_largest_ask': 0,
            'ob_bid_depth': 0,
            'ob_ask_depth': 0,
            'ob_depth_ratio': 1.0,
            'ob_total_depth': 0,
            'ob_spread_pct': 0,
            'ob_best_bid': 0,
            'ob_best_ask': 0,
        }

# Example usage
if __name__ == "__main__":
    tracker = OrderFlowTracker()
    
    print("="*60)
    print("📊 Order Flow Tracker Test")
    print("="*60)
    
    # Get order book
    print("\n📖 Fetching order book...")
    orderbook = tracker.get_orderbook()
    
    if orderbook['bids'] and orderbook['asks']:
        print(f"✅ Order book retrieved")
        print(f"   Bid levels: {len(orderbook['bids'])}")
        print(f"   Ask levels: {len(orderbook['asks'])}")
        print(f"   Best bid: ${orderbook['bids'][0][0]:,.2f} ({orderbook['bids'][0][1]:.2f} BTC)")
        print(f"   Best ask: ${orderbook['asks'][0][0]:,.2f} ({orderbook['asks'][0][1]:.2f} BTC)")
        
        current_price = (orderbook['bids'][0][0] + orderbook['asks'][0][0]) / 2
        print(f"\n💰 Mid price: ${current_price:,.2f}")
        
        # Calculate imbalance
        print("\n⚖️  Order imbalance:")
        for levels in [5, 10, 20]:
            imbalance = tracker.calculate_order_imbalance(orderbook, levels=levels)
            direction = "BULLISH" if imbalance > 0 else "BEARISH"
            print(f"   {levels} levels: {imbalance:+.3f} ({direction})")
        
        # Detect large orders
        print("\n🐋 Large orders (>10 BTC):")
        large = tracker.detect_large_orders(orderbook, threshold_btc=10)
        print(f"   Large bids: {large['large_bid_count']} ({large['large_bid_total']:.2f} BTC)")
        print(f"   Large asks: {large['large_ask_count']} ({large['large_ask_total']:.2f} BTC)")
        
        # Depth metrics
        print("\n📏 Depth within 1%:")
        depth = tracker.calculate_depth_metrics(orderbook, current_price, distance_pct=0.01)
        print(f"   Bid depth: {depth['bid_depth_1pct']:.2f} BTC")
        print(f"   Ask depth: {depth['ask_depth_1pct']:.2f} BTC")
        print(f"   Ratio: {depth['depth_ratio']:.2f}")
        
        # Get features
        print("\n📈 Generating features...")
        features = tracker.get_orderflow_features(current_price)
        print("✅ Features:")
        for key, value in list(features.items())[:10]:  # Show first 10
            print(f"   {key}: {value}")
    else:
        print("❌ No order book data")
    
    print("\n" + "="*60)
    print("✅ Test Complete!")
    print("="*60)
