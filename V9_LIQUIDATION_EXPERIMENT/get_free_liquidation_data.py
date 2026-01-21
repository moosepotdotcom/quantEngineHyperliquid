#!/usr/bin/env python3
"""
Real Liquidation Data from Free Sources
Multiple sources to try
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import time

class FreeLiquidationSources:
    """Try multiple free liquidation data sources"""
    
    def try_coinalyze_api(self):
        """
        Coinalyze - Free liquidation data
        https://coinalyze.net/
        """
        print("📡 Trying Coinalyze API...")
        
        # Coinalyze has a free API for liquidations
        url = "https://api.coinalyze.net/v1/liquidation-history"
        
        params = {
            'symbols': 'BTCUSD',
            'interval': '1h',
            'from': int((datetime.now() - timedelta(days=365)).timestamp()),
            'to': int(datetime.now().timestamp())
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Coinalyze: Got {len(data)} records")
                return pd.DataFrame(data)
            else:
                print(f"❌ Coinalyze: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Coinalyze error: {e}")
            return None
    
    def try_alternative_data_api(self):
        """
        Alternative Data - Free crypto data
        """
        print("📡 Trying Alternative Data API...")
        
        # This is a hypothetical endpoint - trying common patterns
        url = "https://api.alternative.me/liquidations/btc"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Alternative Data: Got data")
                return pd.DataFrame(data)
            else:
                print(f"❌ Alternative Data: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Alternative Data error: {e}")
            return None
    
    def try_cryptoquant_free(self):
        """
        CryptoQuant has some free endpoints
        """
        print("📡 Trying CryptoQuant Free API...")
        
        url = "https://api.cryptoquant.com/v1/btc/exchange-flows/liquidation"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ CryptoQuant: Got data")
                return pd.DataFrame(data)
            else:
                print(f"❌ CryptoQuant: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ CryptoQuant error: {e}")
            return None
    
    def try_glassnode_free(self):
        """
        Glassnode has some free tier data
        """
        print("📡 Trying Glassnode Free API...")
        
        url = "https://api.glassnode.com/v1/metrics/derivatives/futures_liquidated_volume_long_sum"
        
        params = {
            'a': 'BTC',
            'i': '1h',
            's': int((datetime.now() - timedelta(days=365)).timestamp()),
            'u': int(datetime.now().timestamp())
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Glassnode: Got {len(data)} records")
                df = pd.DataFrame(data)
                df['timestamp'] = pd.to_datetime(df['t'], unit='s')
                df['liq_volume_long'] = df['v']
                return df
            else:
                print(f"❌ Glassnode: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Glassnode error: {e}")
            return None
    
    def try_coinank_api(self):
        """
        Coinank - Free liquidation heatmap data
        https://www.coinank.com/
        """
        print("📡 Trying Coinank API...")
        
        url = "https://api.coinank.com/api/liquidation/history"
        
        params = {
            'symbol': 'BTCUSDT',
            'interval': '1h',
            'limit': 1000
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    print(f"✅ Coinank: Got {len(data['data'])} records")
                    return pd.DataFrame(data['data'])
                else:
                    print(f"❌ Coinank: No data field")
                    return None
            else:
                print(f"❌ Coinank: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Coinank error: {e}")
            return None
    
    def try_aggr_trade_api(self):
        """
        aggr.trade - Free liquidation data
        https://aggr.trade/
        """
        print("📡 Trying aggr.trade API...")
        
        url = "https://api.aggr.trade/historical/liquidations/BINANCE:BTCUSDT"
        
        params = {
            'from': int((datetime.now() - timedelta(days=30)).timestamp() * 1000),
            'to': int(datetime.now().timestamp() * 1000)
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ aggr.trade: Got data")
                return pd.DataFrame(data)
            else:
                print(f"❌ aggr.trade: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ aggr.trade error: {e}")
            return None

def download_free_liquidation_data():
    """Try all free sources"""
    
    print("🚀 Searching for FREE Liquidation Data Sources")
    print("="*70)
    
    sources = FreeLiquidationSources()
    
    # Try each source
    results = {}
    
    # 1. Coinalyze
    df = sources.try_coinalyze_api()
    if df is not None and len(df) > 0:
        results['coinalyze'] = df
        df.to_csv('liquidations_coinalyze.csv', index=False)
    
    time.sleep(1)
    
    # 2. Coinank
    df = sources.try_coinank_api()
    if df is not None and len(df) > 0:
        results['coinank'] = df
        df.to_csv('liquidations_coinank.csv', index=False)
    
    time.sleep(1)
    
    # 3. aggr.trade
    df = sources.try_aggr_trade_api()
    if df is not None and len(df) > 0:
        results['aggr_trade'] = df
        df.to_csv('liquidations_aggr_trade.csv', index=False)
    
    time.sleep(1)
    
    # 4. Glassnode
    df = sources.try_glassnode_free()
    if df is not None and len(df) > 0:
        results['glassnode'] = df
        df.to_csv('liquidations_glassnode.csv', index=False)
    
    # Summary
    print("\n" + "="*70)
    print("📊 RESULTS:")
    if results:
        for source, df in results.items():
            print(f"   ✅ {source}: {len(df)} records")
            print(f"      Saved to liquidations_{source}.csv")
    else:
        print("   ❌ No free sources worked")
        print("\n💡 ALTERNATIVE: Use liquidation proxy from price data")
        print("   The proxy we created shows strong correlation!")
    
    return results

if __name__ == "__main__":
    results = download_free_liquidation_data()
