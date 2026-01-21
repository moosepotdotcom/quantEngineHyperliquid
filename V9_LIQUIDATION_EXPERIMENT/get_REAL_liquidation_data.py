#!/usr/bin/env python3
"""
GET REAL LIQUIDATION DATA
Try multiple sources to get actual historical liquidations
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import json

class RealLiquidationDataFetcher:
    """Fetch REAL liquidation data from multiple sources"""
    
    def __init__(self):
        self.hyperliquid_url = "https://api.hyperliquid.xyz/info"
        self.data = []
    
    def fetch_hyperliquid_liquidations_direct(self, start_time, end_time):
        """
        Try to get liquidations directly from Hyperliquid
        Using their user fills endpoint with liquidation filter
        """
        print("🔍 Method 1: Hyperliquid Direct API")
        print("="*70)
        
        # Try to get liquidation data
        # Hyperliquid stores liquidations as special fills
        payload = {
            "type": "userFills",
            "user": "0x0000000000000000000000000000000000000000"  # System address for liquidations
        }
        
        try:
            response = requests.post(self.hyperliquid_url, json=payload, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Response: {str(data)[:200]}")
                return data
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        return None
    
    def fetch_coinglass_liquidations(self):
        """Fetch from Coinglass API"""
        print("\n🔍 Method 2: Coinglass API")
        print("="*70)
        
        # Coinglass liquidation data endpoint
        url = "https://open-api.coinglass.com/public/v2/liquidation"
        
        params = {
            "symbol": "BTC",
            "time_type": "h1",  # 1 hour intervals
            "ex": "Binance"  # Exchange
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Got data: {len(data.get('data', []))} records")
                return data
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        return None
    
    def fetch_binance_liquidations(self):
        """Fetch from Binance API"""
        print("\n🔍 Method 3: Binance Liquidation Stream")
        print("="*70)
        
        # Binance provides liquidation data via their API
        url = "https://fapi.binance.com/fapi/v1/allForceOrders"
        
        params = {
            "symbol": "BTCUSDT",
            "limit": 1000
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Got {len(data)} liquidations")
                
                # Convert to our format
                liquidations = []
                for liq in data:
                    liquidations.append({
                        'timestamp': pd.to_datetime(liq['time'], unit='ms'),
                        'coin': 'BTC',
                        'side': 'A' if liq['side'] == 'SELL' else 'B',  # SELL = long liquidated
                        'price': float(liq['price']),
                        'size': float(liq['origQty']),
                        'source': 'binance_real'
                    })
                
                return pd.DataFrame(liquidations)
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        return None
    
    def fetch_bybit_liquidations(self):
        """Fetch from Bybit API"""
        print("\n🔍 Method 4: Bybit Liquidation Data")
        print("="*70)
        
        url = "https://api.bybit.com/v5/market/recent-trade"
        
        params = {
            "category": "linear",
            "symbol": "BTCUSDT",
            "limit": 1000
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Response: {str(data)[:200]}")
                return data
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        return None

def main():
    """Try all methods to get real liquidation data"""
    
    print("🚀 FETCHING REAL LIQUIDATION DATA")
    print("="*70)
    print("Trying multiple sources...")
    print()
    
    fetcher = RealLiquidationDataFetcher()
    
    # Method 1: Hyperliquid
    hl_data = fetcher.fetch_hyperliquid_liquidations_direct(
        datetime(2026, 1, 1),
        datetime(2026, 1, 15)
    )
    
    # Method 2: Coinglass
    cg_data = fetcher.fetch_coinglass_liquidations()
    
    # Method 3: Binance (MOST LIKELY TO WORK)
    binance_data = fetcher.fetch_binance_liquidations()
    
    if binance_data is not None and len(binance_data) > 0:
        print("\n" + "="*70)
        print("✅ SUCCESS! Got real Binance liquidations")
        print("="*70)
        
        # Save
        output_file = 'liquidation_data/REAL_liquidations_binance.csv'
        binance_data.to_csv(output_file, index=False)
        
        print(f"\n💾 Saved {len(binance_data)} REAL liquidations to {output_file}")
        print()
        print("📊 Sample:")
        print(binance_data.head(10))
        print()
        print(f"📈 Stats:")
        print(f"   Total volume: {binance_data['size'].sum():.2f} BTC")
        print(f"   Avg size: {binance_data['size'].mean():.2f} BTC")
        print(f"   Date range: {binance_data['timestamp'].min()} to {binance_data['timestamp'].max()}")
        
        return binance_data
    
    # Method 4: Bybit
    bybit_data = fetcher.fetch_bybit_liquidations()
    
    print("\n" + "="*70)
    print("⚠️  Could not get real liquidation data from any source")
    print("   Recommendations:")
    print("   1. Let monitor run for 24-48h to collect live data")
    print("   2. Use paid API (Coinglass Pro)")
    print("   3. Scrape liquidation websites")
    print("="*70)

if __name__ == "__main__":
    main()
