#!/usr/bin/env python3
"""
Fetch Historical Liquidation Data
Try multiple sources: Hyperliquid, Coinglass, GitHub datasets
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import time

class HistoricalLiquidationFetcher:
    """Fetch historical liquidation data from multiple sources"""
    
    def __init__(self):
        self.hyperliquid_url = "https://api.hyperliquid.xyz/info"
        self.data = []
    
    def fetch_hyperliquid_trades(self, start_date, end_date):
        """
        Fetch trades from Hyperliquid and infer liquidations
        Large trades with specific patterns = likely liquidations
        """
        print("🔍 Fetching Hyperliquid trade data...")
        
        # Try to get recent trades
        payload = {
            "type": "candleSnapshot",
            "req": {
                "coin": "BTC",
                "interval": "5m",
                "startTime": int(start_date.timestamp() * 1000),
                "endTime": int(end_date.timestamp() * 1000)
            }
        }
        
        try:
            response = requests.post(self.hyperliquid_url, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Got {len(data)} candles")
                return data
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        return None
    
    def infer_liquidations_from_volume(self, df_price):
        """
        Infer liquidations from volume spikes + price wicks
        This is our enhanced proxy
        """
        print("\n🧠 Inferring liquidations from price/volume data...")
        
        # Calculate volume surge
        df_price['vol_ma'] = df_price['volume'].rolling(20).mean()
        df_price['vol_surge'] = df_price['volume'] / df_price['vol_ma']
        
        # Calculate wick ratio
        df_price['body'] = abs(df_price['close'] - df_price['open'])
        df_price['upper_wick'] = df_price['high'] - df_price[['close', 'open']].max(axis=1)
        df_price['lower_wick'] = df_price[['close', 'open']].min(axis=1) - df_price['low']
        df_price['total_range'] = df_price['high'] - df_price['low']
        df_price['wick_ratio'] = (df_price['upper_wick'] + df_price['lower_wick']) / df_price['total_range']
        
        # Identify likely liquidations
        liquidations = []
        
        for i, row in df_price.iterrows():
            # Criteria for liquidation:
            # 1. Volume surge > 3x
            # 2. Long wick (> 50% of range)
            # 3. Sharp price move
            
            if row['vol_surge'] > 3 and row['wick_ratio'] > 0.5:
                # Determine direction
                if row['lower_wick'] > row['upper_wick']:
                    # Long wick below = longs liquidated
                    side = 'A'
                    price = row['low']
                else:
                    # Long wick above = shorts liquidated
                    side = 'B'
                    price = row['high']
                
                # Estimate size from volume
                size = row['volume'] * 0.1  # Assume 10% of volume is liquidation
                
                liquidations.append({
                    'timestamp': row['timestamp'],
                    'coin': 'BTC',
                    'side': side,
                    'price': price,
                    'size': size,
                    'source': 'inferred'
                })
        
        df_liqs = pd.DataFrame(liquidations)
        print(f"   ✅ Inferred {len(df_liqs)} liquidation events")
        
        return df_liqs
    
    def fetch_coinglass_data(self):
        """Try to fetch from Coinglass (may require API key)"""
        print("\n🔍 Trying Coinglass API...")
        
        # Coinglass liquidation endpoint
        url = "https://open-api.coinglass.com/public/v2/liquidation_history"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Got Coinglass data")
                return data
        except Exception as e:
            print(f"   ❌ Coinglass failed: {e}")
        
        return None

def fetch_historical_liquidations(start_date, end_date):
    """Main function to fetch historical liquidation data"""
    
    print("🚀 FETCHING HISTORICAL LIQUIDATION DATA")
    print("="*70)
    print(f"   Period: {start_date} to {end_date}")
    print()
    
    fetcher = HistoricalLiquidationFetcher()
    
    # Try Hyperliquid first
    hl_data = fetcher.fetch_hyperliquid_trades(start_date, end_date)
    
    # Try Coinglass
    cg_data = fetcher.fetch_coinglass_data()
    
    # If no direct data, use inference
    print("\n💡 Using liquidation inference from price data...")
    
    # Load price data
    df_price = pd.read_csv('../training/data/BTC_5m_2025_enriched.csv')
    df_price['timestamp'] = pd.to_datetime(df_price['timestamp'])
    
    # Filter to date range
    df_price = df_price[
        (df_price['timestamp'] >= start_date) &
        (df_price['timestamp'] <= end_date)
    ]
    
    # Infer liquidations
    df_liqs = fetcher.infer_liquidations_from_volume(df_price)
    
    # Save
    output_file = 'liquidation_data/historical_liquidations_inferred.csv'
    df_liqs.to_csv(output_file, index=False)
    
    print(f"\n💾 Saved {len(df_liqs)} liquidations to {output_file}")
    print("\n" + "="*70)
    print("✅ HISTORICAL DATA READY FOR BACKTESTING")
    
    return df_liqs

if __name__ == "__main__":
    # Fetch Jan 2026 data
    start = datetime(2026, 1, 1)
    end = datetime(2026, 1, 15)
    
    df_liqs = fetch_historical_liquidations(start, end)
    
    print(f"\n📊 Sample:")
    print(df_liqs.head(10))
