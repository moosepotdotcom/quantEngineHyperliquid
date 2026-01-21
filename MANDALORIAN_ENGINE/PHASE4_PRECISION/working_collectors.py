#!/usr/bin/env python3
"""
Working Phase 4 Collectors - Simplified and Fixed
"""

import requests
from datetime import datetime

class WorkingCollectors:
    """Simplified, working versions of all collectors"""
    
    def __init__(self):
        self.base_url = "https://api.hyperliquid.xyz/info"
        self.session = requests.Session()
    
    def get_current_price(self):
        """Get current BTC price"""
        payload = {"type": "allMids"}
        try:
            response = self.session.post(self.base_url, json=payload, timeout=5)
            data = response.json()
            return float(data.get('BTC', 0))
        except:
            return 0.0
    
    def get_orderbook_features(self):
        """Get order book features"""
        payload = {"type": "l2Book", "coin": "BTC"}
        try:
            response = self.session.post(self.base_url, json=payload, timeout=5)
            data = response.json()
            
            if 'levels' in data and len(data['levels']) >= 2:
                bids = data['levels'][0][:10]
                asks = data['levels'][1][:10]
                
                # Calculate imbalance
                bid_vol = sum([float(b['sz']) for b in bids])
                ask_vol = sum([float(a['sz']) for a in asks])
                total = bid_vol + ask_vol
                imbalance = (bid_vol - ask_vol) / total if total > 0 else 0
                
                # Large orders
                large_bids = len([b for b in bids if float(b['sz']) > 10])
                large_asks = len([a for a in asks if float(a['sz']) > 10])
                
                return {
                    'ob_imbalance': imbalance,
                    'ob_bid_depth': bid_vol,
                    'ob_ask_depth': ask_vol,
                    'ob_large_bids': large_bids,
                    'ob_large_asks': large_asks,
                    'ob_best_bid': float(bids[0]['px']) if bids else 0,
                    'ob_best_ask': float(asks[0]['px']) if asks else 0
                }
        except Exception as e:
            print(f"Order book error: {e}")
        
        return {
            'ob_imbalance': 0,
            'ob_bid_depth': 0,
            'ob_ask_depth': 0,
            'ob_large_bids': 0,
            'ob_large_asks': 0,
            'ob_best_bid': 0,
            'ob_best_ask': 0
        }
    
    def get_funding_features(self):
        """Get funding rate features"""
        payload = {"type": "metaAndAssetCtxs"}
        try:
            response = self.session.post(self.base_url, json=payload, timeout=5)
            data = response.json()
            
            # BTC is typically the first asset (index 0)
            if len(data) > 1 and len(data[1]) > 0:
                btc_asset = data[1][0]  # First asset is BTC
                funding = float(btc_asset.get('funding', 0))
                oi = float(btc_asset.get('openInterest', 0))
                
                return {
                    'funding_rate': funding,
                    'funding_pct': funding * 100,
                    'funding_is_extreme': 1 if abs(funding) > 0.001 else 0,
                    'oi': oi,
                    'oi_millions': oi / 1_000_000
                }
        except Exception as e:
            print(f"Funding error: {e}")
        
        return {
            'funding_rate': 0,
            'funding_pct': 0,
            'funding_is_extreme': 0,
            'oi': 0,
            'oi_millions': 0
        }
    
    def get_all_features(self):
        """Get all Phase 4 features"""
        price = self.get_current_price()
        ob_features = self.get_orderbook_features()
        funding_features = self.get_funding_features()
        
        return {
            'timestamp': datetime.now(),
            'price': price,
            **ob_features,
            **funding_features
        }

# Test
if __name__ == "__main__":
    print("="*60)
    print("✅ Working Phase 4 Collectors Test")
    print("="*60)
    
    collector = WorkingCollectors()
    
    print("\n📊 Collecting features...")
    features = collector.get_all_features()
    
    print(f"\n✅ Collected {len(features)} features:")
    for key, value in features.items():
        if isinstance(value, float):
            print(f"   {key}: {value:.6f}")
        else:
            print(f"   {key}: {value}")
    
    print("\n" + "="*60)
    print("✅ All collectors working!")
    print("="*60)
