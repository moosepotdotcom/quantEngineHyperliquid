#!/usr/bin/env python3
"""
Multi-Asset Phase 4 Scanner
Scans 5 coins simultaneously: BTC, ETH, SOL, AVAX, ARB
"""

import requests
from datetime import datetime
import time

class MultiAssetScanner:
    """
    Scan multiple assets for Phase 4 signals
    """
    
    def __init__(self, coins=None):
        self.coins = coins or ["BTC", "ETH", "SOL", "AVAX", "ARB"]
        self.api_url = "https://api.hyperliquid.xyz/info"
        
    def get_all_prices(self):
        """Get prices for all coins at once"""
        try:
            payload = {"type": "allMids"}
            response = requests.post(self.api_url, json=payload, timeout=5)
            return response.json()
        except Exception as e:
            print(f"❌ Error getting prices: {e}")
            return {}
    
    def get_orderbook(self, coin):
        """Get order book for specific coin"""
        try:
            payload = {"type": "l2Book", "coin": coin}
            response = requests.post(self.api_url, json=payload, timeout=5)
            data = response.json()
            
            if not data or 'levels' not in data[0]:
                return None
            
            levels = data[0]['levels']
            bids = levels[0]
            asks = levels[1]
            
            bid_depth = sum([float(b[1]) for b in bids])
            ask_depth = sum([float(a[1]) for a in asks])
            
            imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth) if (bid_depth + ask_depth) > 0 else 0
            
            # Whale threshold varies by coin
            whale_threshold = {"BTC": 10, "ETH": 100, "SOL": 1000, "AVAX": 500, "ARB": 5000}.get(coin, 100)
            large_bids = len([b for b in bids if float(b[1]) > whale_threshold])
            large_asks = len([a for a in asks if float(a[1]) > whale_threshold])
            
            return {
                'imbalance': imbalance,
                'bid_depth': bid_depth,
                'ask_depth': ask_depth,
                'large_bids': large_bids,
                'large_asks': large_asks,
                'best_bid': float(bids[0][0]) if bids else 0,
                'best_ask': float(asks[0][0]) if asks else 0,
            }
        except Exception as e:
            return None
    
    def get_funding(self, coin):
        """Get funding for specific coin"""
        try:
            payload = {"type": "metaAndAssetCtxs"}
            response = requests.post(self.api_url, json=payload, timeout=5)
            data = response.json()
            
            coin_index = None
            for i, meta in enumerate(data[0]['universe']):
                if meta['name'] == coin:
                    coin_index = i
                    break
            
            if coin_index is None:
                return None
            
            ctx = data[1][coin_index]
            funding_rate = float(ctx.get('funding', 0))
            funding_pct = funding_rate * 100
            oi = float(ctx.get('openInterest', 0))
            
            return {
                'funding_pct': funding_pct,
                'is_extreme': abs(funding_pct) > 0.08,
                'oi_millions': oi / 1_000_000,
            }
        except Exception as e:
            return None
    
    def analyze_coin(self, coin, price):
        """Analyze single coin and generate signal"""
        
        ob = self.get_orderbook(coin)
        funding = self.get_funding(coin)
        
        if not ob or not funding:
            return None
        
        # Calculate signal score (same as BTC strategy)
        score = 0
        reasons = []
        direction = None
        
        # LONG signals
        if ob['imbalance'] > 0.5:
            score += 3
            reasons.append(f"Strong buy pressure ({ob['imbalance']:.3f})")
        
        if ob['large_bids'] > 0:
            score += 2
            reasons.append(f"{ob['large_bids']} whale bid(s)")
        
        if ob['ask_depth'] < ob['bid_depth'] * 0.3:
            score += 2
            reasons.append("Thin asks")
        
        if not funding['is_extreme']:
            score += 1
        
        if score >= 5:
            direction = "LONG"
        
        # SHORT signals
        short_score = 0
        short_reasons = []
        
        if ob['imbalance'] < -0.5:
            short_score += 3
            short_reasons.append(f"Strong sell pressure ({ob['imbalance']:.3f})")
        
        if ob['large_asks'] > 0:
            short_score += 2
            short_reasons.append(f"{ob['large_asks']} whale ask(s)")
        
        if ob['bid_depth'] < ob['ask_depth'] * 0.3:
            short_score += 2
            short_reasons.append("Thin bids")
        
        if not funding['is_extreme']:
            short_score += 1
        
        if short_score >= 5 and short_score > score:
            direction = "SHORT"
            score = short_score
            reasons = short_reasons
        
        return {
            'coin': coin,
            'price': price,
            'imbalance': ob['imbalance'],
            'whale_bids': ob['large_bids'],
            'whale_asks': ob['large_asks'],
            'funding_pct': funding['funding_pct'],
            'oi_millions': funding['oi_millions'],
            'signal': direction,
            'score': score,
            'confidence': score / 9,
            'reasons': reasons,
        }
    
    def scan_all(self):
        """Scan all coins and return results"""
        
        print(f"\n{'='*80}")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🌐 Multi-Asset Scan")
        print(f"{'='*80}")
        
        # Get all prices at once
        all_prices = self.get_all_prices()
        
        results = []
        
        for coin in self.coins:
            if coin not in all_prices:
                print(f"⚠️  {coin} not available")
                continue
            
            price = float(all_prices[coin])
            print(f"\n📊 {coin} @ ${price:,.2f}")
            
            analysis = self.analyze_coin(coin, price)
            
            if analysis:
                results.append(analysis)
                
                # Display
                print(f"   Imbalance: {analysis['imbalance']:+.3f}", end="")
                if analysis['imbalance'] > 0.5:
                    print(" 🟢 BULLISH", end="")
                elif analysis['imbalance'] < -0.5:
                    print(" 🔴 BEARISH", end="")
                print()
                
                if analysis['whale_bids'] > 0:
                    print(f"   🐋 {analysis['whale_bids']} whale bid(s)")
                if analysis['whale_asks'] > 0:
                    print(f"   🐋 {analysis['whale_asks']} whale ask(s)")
                
                print(f"   Funding: {analysis['funding_pct']:.4f}%")
                
                if analysis['signal']:
                    print(f"   🎯 SIGNAL: {analysis['signal']} (confidence: {analysis['confidence']*100:.0f}%)")
                    for reason in analysis['reasons']:
                        print(f"      ✓ {reason}")
                else:
                    print(f"   ⏸️  No clear setup")
            else:
                print(f"   ❌ Failed to analyze")
        
        return results

# Main
if __name__ == "__main__":
    scanner = MultiAssetScanner()
    
    print("="*80)
    print("🚀 Phase 4 Multi-Asset Scanner")
    print("="*80)
    print(f"Assets: {', '.join(scanner.coins)}")
    print("="*80)
    
    # Run 3 scans
    for i in range(3):
        results = scanner.scan_all()
        
        # Show best signal
        if results:
            signals = [r for r in results if r['signal']]
            if signals:
                best = max(signals, key=lambda x: x['confidence'])
                print(f"\n{'='*80}")
                print(f"⭐ BEST SIGNAL: {best['coin']} {best['signal']}")
                print(f"   Confidence: {best['confidence']*100:.0f}%")
                print(f"   Price: ${best['price']:,.2f}")
                print(f"{'='*80}")
        
        if i < 2:
            print(f"\n⏳ Next scan in 10s...")
            time.sleep(10)
    
    print(f"\n{'='*80}")
    print("✅ Scan complete!")
    print("="*80)
