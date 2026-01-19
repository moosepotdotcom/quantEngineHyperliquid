#!/usr/bin/env python3
"""
Multi-Asset Continuous Monitoring
Collects data for ALL 5 coins simultaneously
"""

import requests
import csv
import time
from datetime import datetime
import sys

class MultiAssetMonitor:
    def __init__(self, coins=None, interval=300):
        self.coins = coins or ['BTC', 'ETH', 'SOL', 'AVAX', 'ARB']
        self.interval = interval
        self.api_url = "https://api.hyperliquid.xyz/info"
        
    def collect_coin_data(self, coin):
        """Collect all features for one coin"""
        try:
            # Get price
            r = requests.post(self.api_url, json={'type': 'allMids'}, timeout=10)
            prices = r.json()
            price = float(prices.get(coin, 0))
            
            if price == 0:
                return None
            
            # Get order book
            r = requests.post(self.api_url, json={'type': 'l2Book', 'coin': coin}, timeout=10)
            ob = r.json()
            
            # Response is a dict with 'levels' key, not a list
            if not ob or not isinstance(ob, dict) or 'levels' not in ob:
                return None
            
            bids = ob['levels'][0]
            asks = ob['levels'][1]
            
            # Bids/asks are lists of dicts with 'px' and 'sz' keys
            bid_depth = sum([float(b['sz']) for b in bids])
            ask_depth = sum([float(a['sz']) for a in asks])
            imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth) if (bid_depth + ask_depth) > 0 else 0
            
            whale_threshold = {'BTC': 10, 'ETH': 100, 'SOL': 1000, 'AVAX': 500, 'ARB': 5000}.get(coin, 100)
            large_bids = len([b for b in bids if float(b['sz']) > whale_threshold])
            large_asks = len([a for a in asks if float(a['sz']) > whale_threshold])
            
            # Get funding
            r = requests.post(self.api_url, json={'type': 'metaAndAssetCtxs'}, timeout=10)
            data = r.json()
            
            funding_pct = 0
            oi = 0
            for i, meta in enumerate(data[0]['universe']):
                if meta['name'] == coin:
                    funding_pct = float(data[1][i].get('funding', 0)) * 100
                    oi = float(data[1][i].get('openInterest', 0))
                    break
            
            return {
                'timestamp': datetime.now(),
                'coin': coin,
                'price': price,
                'imbalance': imbalance,
                'bid_depth': bid_depth,
                'ask_depth': ask_depth,
                'whale_bids': large_bids,
                'whale_asks': large_asks,
                'funding_pct': funding_pct,
                'oi_millions': oi / 1_000_000,
            }
            
        except Exception as e:
            print(f"   ❌ {coin} error: {e}")
            return None
    
    def run(self):
        """Run continuous monitoring"""
        print("="*80)
        print("🚀 Multi-Asset Continuous Monitoring")
        print("="*80)
        print(f"Coins: {', '.join(self.coins)}")
        print(f"Interval: {self.interval}s ({self.interval/60:.1f} min)")
        print(f"Output: multi_asset_data.csv")
        print("="*80)
        print()
        
        # Create CSV
        with open('multi_asset_data.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'timestamp', 'coin', 'price', 'imbalance', 'bid_depth', 'ask_depth',
                'whale_bids', 'whale_asks', 'funding_pct', 'oi_millions'
            ])
            writer.writeheader()
        
        sample = 1
        try:
            while True:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Sample {sample}...")
                
                for coin in self.coins:
                    print(f"   📊 {coin}...", end=" ", flush=True)
                    data = self.collect_coin_data(coin)
                    
                    if data:
                        # Save to CSV
                        with open('multi_asset_data.csv', 'a', newline='') as f:
                            writer = csv.DictWriter(f, fieldnames=data.keys())
                            writer.writerow(data)
                        
                        print(f"✅ ${data['price']:,.2f} | Imb: {data['imbalance']:+.3f} | Whales: {data['whale_bids']}↑ {data['whale_asks']}↓")
                    else:
                        print(f"❌ Failed")
                
                print(f"   ✅ Sample {sample} complete")
                print(f"   ⏳ Next sample in {self.interval}s...")
                print()
                
                sample += 1
                time.sleep(self.interval)
                
        except KeyboardInterrupt:
            print("\n✅ Monitoring stopped")

if __name__ == "__main__":
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    monitor = MultiAssetMonitor(interval=interval)
    monitor.run()
