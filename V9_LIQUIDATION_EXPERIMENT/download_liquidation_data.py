#!/usr/bin/env python3
"""
V9 Liquidation Data Downloader
Fetches liquidation, funding rate, and open interest data from Hyperliquid
"""

import requests
import pandas as pd
import json
from datetime import datetime, timedelta
import time

class HyperliquidDataFetcher:
    """Fetch market microstructure data from Hyperliquid"""
    
    def __init__(self):
        self.base_url = "https://api.hyperliquid.xyz/info"
        
    def fetch_funding_history(self, coin="BTC", start_time=None, end_time=None):
        """
        Fetch funding rate history
        
        Args:
            coin: Asset symbol (default: BTC)
            start_time: Start timestamp (ms)
            end_time: End timestamp (ms)
        """
        payload = {
            "type": "fundingHistory",
            "coin": coin
        }
        
        if start_time:
            payload["startTime"] = start_time
        if end_time:
            payload["endTime"] = end_time
            
        try:
            response = requests.post(self.base_url, json=payload)
            if response.status_code == 200:
                data = response.json()
                df = pd.DataFrame(data)
                print(f"✅ Fetched {len(df)} funding rate records")
                return df
            else:
                print(f"❌ Error: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Exception: {e}")
            return None
    
    def fetch_open_interest(self, coin="BTC"):
        """Fetch current open interest"""
        payload = {
            "type": "metaAndAssetCtxs"
        }
        
        try:
            response = requests.post(self.base_url, json=payload)
            if response.status_code == 200:
                data = response.json()
                # Extract OI for BTC
                for asset in data[1]:
                    if asset.get('coin') == coin:
                        oi = asset.get('openInterest', 0)
                        print(f"✅ Current OI for {coin}: {oi}")
                        return oi
                return None
            else:
                print(f"❌ Error: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Exception: {e}")
            return None
    
    def fetch_user_fills(self, user_address, start_time=None):
        """
        Fetch user trade fills (can be used to infer liquidations)
        
        Note: Hyperliquid doesn't have a direct liquidation endpoint,
        but we can infer from large forced trades
        """
        payload = {
            "type": "userFills",
            "user": user_address
        }
        
        if start_time:
            payload["startTime"] = start_time
            
        try:
            response = requests.post(self.base_url, json=payload)
            if response.status_code == 200:
                data = response.json()
                df = pd.DataFrame(data)
                print(f"✅ Fetched {len(df)} fill records")
                return df
            else:
                print(f"❌ Error: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Exception: {e}")
            return None

def fetch_coinglass_liquidations(symbol="BTCUSDT", start_date="2026-01-01", end_date="2026-01-14"):
    """
    Fetch aggregated liquidation data from Coinglass
    
    Note: Requires API key for full access
    Free tier: Limited historical data
    """
    # Coinglass API endpoint
    base_url = "https://open-api.coinglass.com/public/v2/liquidation_history"
    
    params = {
        "symbol": symbol,
        "time_type": "h1",  # 1-hour intervals
        "ex": "Binance"  # Can aggregate across exchanges
    }
    
    try:
        # Note: This is a placeholder - actual implementation needs API key
        print("⚠️  Coinglass requires API key")
        print("   Alternative: Use Hyperliquid data or scrape public dashboards")
        return None
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None

def download_all_data():
    """Download all available market microstructure data"""
    
    print("🚀 V9 Data Collection - Liquidations & Market Microstructure")
    print("="*70)
    
    fetcher = HyperliquidDataFetcher()
    
    # 1. Funding rates
    print("\n📊 Fetching Funding Rate History...")
    funding_df = fetcher.fetch_funding_history(coin="BTC")
    if funding_df is not None:
        funding_df.to_csv('V9_funding_rates.csv', index=False)
        print(f"   Saved to V9_funding_rates.csv")
    
    # 2. Open interest
    print("\n📊 Fetching Open Interest...")
    oi = fetcher.fetch_open_interest(coin="BTC")
    
    # 3. Liquidation proxy (using large trades)
    print("\n📊 Note: Direct liquidation data requires:")
    print("   - Coinglass API (paid)")
    print("   - CryptoQuant API (paid)")
    print("   - Or scraping public liquidation dashboards")
    
    print("\n💡 Alternative Approach:")
    print("   We can use CVD spikes + volume surges as liquidation proxy")
    print("   Our model already has CVD - we can enhance it!")
    
    return funding_df

if __name__ == "__main__":
    download_all_data()
