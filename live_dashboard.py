#!/usr/bin/env python3
"""
Phase 4 Multi-Asset Live Dashboard
Real-time terminal UI monitoring 5 coins simultaneously
"""

import requests
from datetime import datetime
import time
import os
import sys

class LiveDashboard:
    """
    Beautiful terminal dashboard for multi-asset monitoring
    """
    
    def __init__(self, coins=None):
        self.coins = coins or ["BTC", "ETH", "SOL", "AVAX", "ARB"]
        self.api_url = "https://api.hyperliquid.xyz/info"
        self.data_history = {coin: [] for coin in self.coins}
        
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def get_all_data(self):
        """Fetch all data for all coins"""
        try:
            # Get prices
            prices_payload = {"type": "allMids"}
            prices_response = requests.post(self.api_url, json=prices_payload, timeout=5)
            all_prices = prices_response.json()
            
            # Get funding/OI
            funding_payload = {"type": "metaAndAssetCtxs"}
            funding_response = requests.post(self.api_url, json=funding_payload, timeout=5)
            funding_data = funding_response.json()
            
            results = {}
            
            for coin in self.coins:
                if coin not in all_prices:
                    continue
                
                price = float(all_prices[coin])
                
                # Get order book
                ob_payload = {"type": "l2Book", "coin": coin}
                ob_response = requests.post(self.api_url, json=ob_payload, timeout=5)
                ob_data = ob_response.json()
                
                if not ob_data or 'levels' not in ob_data[0]:
                    continue
                
                levels = ob_data[0]['levels']
                bids = levels[0]
                asks = levels[1]
                
                bid_depth = sum([float(b[1]) for b in bids])
                ask_depth = sum([float(a[1]) for a in asks])
                imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth) if (bid_depth + ask_depth) > 0 else 0
                
                # Whale detection
                whale_threshold = {"BTC": 10, "ETH": 100, "SOL": 1000, "AVAX": 500, "ARB": 5000}.get(coin, 100)
                large_bids = len([b for b in bids if float(b[1]) > whale_threshold])
                large_asks = len([a for a in asks if float(a[1]) > whale_threshold])
                
                # Get funding
                coin_index = None
                for i, meta in enumerate(funding_data[0]['universe']):
                    if meta['name'] == coin:
                        coin_index = i
                        break
                
                funding_pct = 0
                oi_millions = 0
                if coin_index is not None:
                    ctx = funding_data[1][coin_index]
                    funding_pct = float(ctx.get('funding', 0)) * 100
                    oi_millions = float(ctx.get('openInterest', 0)) / 1_000_000
                
                # Generate signal
                score = 0
                direction = None
                
                if imbalance > 0.5:
                    score += 3
                if large_bids > 0:
                    score += 2
                if ask_depth < bid_depth * 0.3:
                    score += 2
                if abs(funding_pct) < 0.08:
                    score += 1
                
                if score >= 5:
                    direction = "LONG"
                
                short_score = 0
                if imbalance < -0.5:
                    short_score += 3
                if large_asks > 0:
                    short_score += 2
                if bid_depth < ask_depth * 0.3:
                    short_score += 2
                if abs(funding_pct) < 0.08:
                    short_score += 1
                
                if short_score >= 5 and short_score > score:
                    direction = "SHORT"
                    score = short_score
                
                results[coin] = {
                    'price': price,
                    'imbalance': imbalance,
                    'whale_bids': large_bids,
                    'whale_asks': large_asks,
                    'funding_pct': funding_pct,
                    'oi_millions': oi_millions,
                    'signal': direction,
                    'score': score,
                    'confidence': score / 9,
                }
                
                # Store history
                self.data_history[coin].append({
                    'time': datetime.now(),
                    'price': price,
                    'imbalance': imbalance,
                })
                
                # Keep only last 10 samples
                if len(self.data_history[coin]) > 10:
                    self.data_history[coin].pop(0)
            
            return results
            
        except Exception as e:
            return {}
    
    def render_dashboard(self, data):
        """Render beautiful dashboard"""
        
        self.clear_screen()
        
        # Header
        print("╔" + "═" * 118 + "╗")
        print("║" + " " * 35 + "🚀 PHASE 4 MULTI-ASSET LIVE DASHBOARD" + " " * 45 + "║")
        print("║" + f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(118) + "║")
        print("╠" + "═" * 118 + "╣")
        
        # Column headers
        print("║ " + "COIN".ljust(6) + "│ " + "PRICE".ljust(12) + "│ " + "IMBALANCE".ljust(12) + "│ " + 
              "WHALES".ljust(10) + "│ " + "FUNDING".ljust(10) + "│ " + "OI(M)".ljust(8) + "│ " + 
              "SIGNAL".ljust(18) + "│ " + "TREND".ljust(25) + " ║")
        print("╠" + "═" * 118 + "╣")
        
        # Data rows
        for coin in self.coins:
            if coin not in data:
                print("║ " + coin.ljust(6) + "│ " + "N/A".ljust(12) + "│ " + "-".ljust(12) + "│ " + 
                      "-".ljust(10) + "│ " + "-".ljust(10) + "│ " + "-".ljust(8) + "│ " + 
                      "-".ljust(18) + "│ " + "-".ljust(25) + " ║")
                continue
            
            d = data[coin]
            
            # Price with change indicator
            price_str = f"${d['price']:,.2f}"
            if len(self.data_history[coin]) >= 2:
                prev_price = self.data_history[coin][-2]['price']
                if d['price'] > prev_price:
                    price_str += " ↑"
                elif d['price'] < prev_price:
                    price_str += " ↓"
            
            # Imbalance with color
            imb = d['imbalance']
            if imb > 0.5:
                imb_str = f"{imb:+.3f} 🟢"
            elif imb < -0.5:
                imb_str = f"{imb:+.3f} 🔴"
            else:
                imb_str = f"{imb:+.3f} ⚪"
            
            # Whales
            whale_str = ""
            if d['whale_bids'] > 0:
                whale_str += f"🐋↑{d['whale_bids']} "
            if d['whale_asks'] > 0:
                whale_str += f"🐋↓{d['whale_asks']}"
            if not whale_str:
                whale_str = "-"
            
            # Funding
            funding_str = f"{d['funding_pct']:.4f}%"
            if abs(d['funding_pct']) > 0.08:
                funding_str += " ⚠️"
            
            # Signal
            if d['signal']:
                signal_str = f"{d['signal']} ({d['confidence']*100:.0f}%)"
                if d['signal'] == "LONG":
                    signal_str = "🟢 " + signal_str
                else:
                    signal_str = "🔴 " + signal_str
            else:
                signal_str = "⏸️  No signal"
            
            # Trend (mini chart)
            trend_str = self.get_mini_chart(coin)
            
            print("║ " + coin.ljust(6) + "│ " + price_str.ljust(12) + "│ " + imb_str.ljust(12) + "│ " + 
                  whale_str.ljust(10) + "│ " + funding_str.ljust(10) + "│ " + 
                  f"{d['oi_millions']:.1f}".ljust(8) + "│ " + signal_str.ljust(18) + "│ " + 
                  trend_str.ljust(25) + " ║")
        
        print("╠" + "═" * 118 + "╣")
        
        # Best signal
        signals = [(coin, d) for coin, d in data.items() if d['signal']]
        if signals:
            best_coin, best_data = max(signals, key=lambda x: x[1]['confidence'])
            print("║ " + f"⭐ BEST SIGNAL: {best_coin} {best_data['signal']} @ ${best_data['price']:,.2f} (Confidence: {best_data['confidence']*100:.0f}%)".ljust(117) + "║")
        else:
            print("║ " + "⏸️  No clear signals at the moment".ljust(117) + "║")
        
        print("╚" + "═" * 118 + "╝")
        
        print("\n💡 Press Ctrl+C to stop monitoring")
    
    def get_mini_chart(self, coin):
        """Generate mini ASCII chart"""
        if len(self.data_history[coin]) < 2:
            return "-" * 20
        
        prices = [h['price'] for h in self.data_history[coin]]
        min_price = min(prices)
        max_price = max(prices)
        
        if max_price == min_price:
            return "─" * 20
        
        # Normalize to 0-5 range
        normalized = [(p - min_price) / (max_price - min_price) * 5 for p in prices]
        
        # Create chart
        chart = ""
        for i in range(len(normalized) - 1):
            curr = int(normalized[i])
            next_val = int(normalized[i + 1])
            
            if next_val > curr:
                chart += "/"
            elif next_val < curr:
                chart += "\\"
            else:
                chart += "─"
        
        # Pad to 20 chars
        chart = chart[-20:].ljust(20, " ")
        
        return chart
    
    def run(self, interval=10):
        """Run live dashboard"""
        
        print("Starting Phase 4 Multi-Asset Dashboard...")
        print("Fetching initial data...")
        
        try:
            while True:
                data = self.get_all_data()
                
                if data:
                    self.render_dashboard(data)
                else:
                    print("⚠️  Failed to fetch data, retrying...")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n✅ Dashboard stopped")
            print("Thank you for using Phase 4 Multi-Asset Dashboard!")

# Main
if __name__ == "__main__":
    dashboard = LiveDashboard()
    
    # Get interval from args
    interval = 10
    if len(sys.argv) > 1:
        try:
            interval = int(sys.argv[1])
        except:
            pass
    
    print("="*60)
    print("🚀 Phase 4 Multi-Asset Live Dashboard")
    print("="*60)
    print(f"Monitoring: {', '.join(dashboard.coins)}")
    print(f"Update Interval: {interval}s")
    print("="*60)
    print()
    
    dashboard.run(interval=interval)
