#!/usr/bin/env python3
"""
Multi-Asset Phase 4 Collector
Supports BTC, ETH, SOL, and any Hyperliquid asset
"""

import requests
import sys

class MultiAssetCollector:
    """
    Collect Phase 4 data for any Hyperliquid asset
    """
    
    def __init__(self, coin="BTC"):
        self.coin = coin
        self.api_url = "https://api.hyperliquid.xyz/info"
        
    def get_current_price(self):
        """Get current price for any coin"""
        try:
            payload = {"type": "allMids"}
            response = requests.post(self.api_url, json=payload, timeout=5)
            data = response.json()
            
            # Find the coin in the response
            if self.coin in data:
                return float(data[self.coin])
            else:
                print(f"⚠️  {self.coin} not found in API response")
                print(f"Available coins: {list(data.keys())[:10]}...")
                return 0
                
        except Exception as e:
            print(f"❌ Error getting price for {self.coin}: {e}")
            return 0
    
    def get_orderbook_features(self):
        """Get order book features for any coin"""
        try:
            payload = {"type": "l2Book", "coin": self.coin}
            response = requests.post(self.api_url, json=payload, timeout=5)
            data = response.json()
            
            if not data or 'levels' not in data[0]:
                return self._empty_orderbook()
            
            levels = data[0]['levels']
            bids = levels[0]  # [[price, size], ...]
            asks = levels[1]
            
            # Calculate features
            bid_depth = sum([float(b[1]) for b in bids])
            ask_depth = sum([float(a[1]) for a in asks])
            
            if bid_depth + ask_depth == 0:
                imbalance = 0
            else:
                imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth)
            
            # Whale detection (>10 coins for BTC/ETH, >100 for SOL)
            whale_threshold = 10 if self.coin in ["BTC", "ETH"] else 100
            large_bids = len([b for b in bids if float(b[1]) > whale_threshold])
            large_asks = len([a for a in asks if float(a[1]) > whale_threshold])
            
            return {
                'ob_imbalance': imbalance,
                'ob_bid_depth': bid_depth,
                'ob_ask_depth': ask_depth,
                'ob_large_bids': large_bids,
                'ob_large_asks': large_asks,
                'ob_best_bid': float(bids[0][0]) if bids else 0,
                'ob_best_ask': float(asks[0][0]) if asks else 0,
            }
            
        except Exception as e:
            print(f"❌ Error getting orderbook for {self.coin}: {e}")
            return self._empty_orderbook()
    
    def get_funding_features(self):
        """Get funding features for any coin"""
        try:
            payload = {"type": "metaAndAssetCtxs"}
            response = requests.post(self.api_url, json=payload, timeout=5)
            data = response.json()
            
            # Find the coin's index
            coin_index = None
            for i, meta in enumerate(data[0]['universe']):
                if meta['name'] == self.coin:
                    coin_index = i
                    break
            
            if coin_index is None:
                return self._empty_funding()
            
            # Get funding data
            ctx = data[1][coin_index]
            funding_rate = float(ctx.get('funding', 0))
            funding_pct = funding_rate * 100
            oi = float(ctx.get('openInterest', 0))
            
            return {
                'funding_rate': funding_rate,
                'funding_pct': funding_pct,
                'funding_is_extreme': 1 if abs(funding_pct) > 0.08 else 0,
                'oi': oi,
                'oi_millions': oi / 1_000_000,
            }
            
        except Exception as e:
            print(f"❌ Error getting funding for {self.coin}: {e}")
            return self._empty_funding()
    
    def _empty_orderbook(self):
        return {
            'ob_imbalance': 0, 'ob_bid_depth': 0, 'ob_ask_depth': 0,
            'ob_large_bids': 0, 'ob_large_asks': 0,
            'ob_best_bid': 0, 'ob_best_ask': 0,
        }
    
    def _empty_funding(self):
        return {
            'funding_rate': 0, 'funding_pct': 0,
            'funding_is_extreme': 0, 'oi': 0, 'oi_millions': 0,
        }

# Test multiple assets
if __name__ == "__main__":
    assets = ["BTC", "ETH", "SOL"]
    
    print("="*60)
    print("🌐 Multi-Asset Phase 4 Collector")
    print("="*60)
    
    for asset in assets:
        print(f"\n{'='*60}")
        print(f"📊 {asset}")
        print(f"{'='*60}")
        
        collector = MultiAssetCollector(coin=asset)
        
        # Get data
        price = collector.get_current_price()
        ob = collector.get_orderbook_features()
        funding = collector.get_funding_features()
        
        if price > 0:
            print(f"\n💰 Price: ${price:,.2f}")
            print(f"\n📊 Order Book:")
            print(f"   Imbalance: {ob['ob_imbalance']:+.3f}")
            print(f"   Bid Depth: {ob['ob_bid_depth']:.2f}")
            print(f"   Ask Depth: {ob['ob_ask_depth']:.2f}")
            if ob['ob_large_bids'] > 0:
                print(f"   🐋 {ob['ob_large_bids']} whale bid(s)")
            if ob['ob_large_asks'] > 0:
                print(f"   🐋 {ob['ob_large_asks']} whale ask(s)")
            
            print(f"\n💸 Funding:")
            print(f"   Rate: {funding['funding_pct']:.4f}%")
            print(f"   OI: {funding['oi_millions']:.2f}M")
            if funding['funding_is_extreme']:
                print(f"   ⚠️  EXTREME FUNDING!")
        else:
            print(f"❌ Failed to get data for {asset}")
    
    print(f"\n{'='*60}")
    print("✅ Multi-asset test complete!")
    print("="*60)
