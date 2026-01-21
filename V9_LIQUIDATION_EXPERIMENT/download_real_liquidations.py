#!/usr/bin/env python3
"""
Real Liquidation Data Scraper
Sources: Free public APIs and dashboards
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import json

class LiquidationDataCollector:
    """Collect real liquidation data from free sources"""
    
    def __init__(self):
        self.sources = {
            'coinglass_public': 'https://fapi.coinglass.com/api/futures/liquidation/chart',
            'bybit_public': 'https://api.bybit.com/v2/public/liq-records',
            'binance_public': 'https://fapi.binance.com/fapi/v1/allForceOrders'
        }
    
    def fetch_binance_liquidations(self, symbol="BTCUSDT", start_time=None, end_time=None, limit=1000):
        """
        Fetch liquidation data from Binance public API
        This is FREE and doesn't require authentication!
        """
        url = "https://fapi.binance.com/fapi/v1/allForceOrders"
        
        params = {
            'symbol': symbol,
            'limit': limit
        }
        
        if start_time:
            params['startTime'] = int(start_time.timestamp() * 1000)
        if end_time:
            params['endTime'] = int(end_time.timestamp() * 1000)
        
        try:
            print(f"📥 Fetching Binance liquidations for {symbol}...")
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    df = pd.DataFrame(data)
                    df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
                    df['exchange'] = 'Binance'
                    print(f"✅ Got {len(df)} liquidation records")
                    return df
                else:
                    print("⚠️  No data returned")
                    return pd.DataFrame()
            else:
                print(f"❌ Error {response.status_code}: {response.text}")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ Exception: {e}")
            return pd.DataFrame()
    
    def fetch_bybit_liquidations(self, symbol="BTCUSDT", start_time=None, limit=50):
        """
        Fetch liquidation data from Bybit public API
        FREE - no auth required
        """
        url = "https://api.bybit.com/v2/public/liq-records"
        
        params = {
            'symbol': symbol,
            'limit': limit
        }
        
        if start_time:
            params['start_time'] = int(start_time.timestamp())
        
        try:
            print(f"📥 Fetching Bybit liquidations for {symbol}...")
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('result'):
                    df = pd.DataFrame(data['result'])
                    df['timestamp'] = pd.to_datetime(df['time'], unit='s')
                    df['exchange'] = 'Bybit'
                    print(f"✅ Got {len(df)} liquidation records")
                    return df
                else:
                    print("⚠️  No data in result")
                    return pd.DataFrame()
            else:
                print(f"❌ Error {response.status_code}")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ Exception: {e}")
            return pd.DataFrame()
    
    def aggregate_liquidations_by_timeframe(self, df, timeframe='5min'):
        """
        Aggregate liquidation data into timeframe buckets
        
        Returns:
            DataFrame with columns: timestamp, liq_volume_long, liq_volume_short, liq_count
        """
        if df.empty:
            return pd.DataFrame()
        
        # Ensure we have the right columns
        df['side'] = df.get('side', df.get('Side', 'UNKNOWN'))
        df['qty'] = df.get('qty', df.get('origQty', df.get('Qty', 0))).astype(float)
        
        # Resample by timeframe
        df.set_index('timestamp', inplace=True)
        
        # Separate long and short liquidations
        long_liqs = df[df['side'].str.upper() == 'BUY'].resample(timeframe)['qty'].sum()
        short_liqs = df[df['side'].str.upper() == 'SELL'].resample(timeframe)['qty'].sum()
        total_count = df.resample(timeframe).size()
        
        result = pd.DataFrame({
            'liq_volume_long': long_liqs,
            'liq_volume_short': short_liqs,
            'liq_count': total_count,
            'liq_net': short_liqs - long_liqs  # Positive = more shorts liquidated (bullish)
        })
        
        result.reset_index(inplace=True)
        return result

def download_2025_liquidation_data():
    """
    Download liquidation data for 2025 (for training)
    We'll test on 2026 data
    """
    print("🚀 Downloading 2025 Liquidation Data for Training")
    print("="*70)
    
    collector = LiquidationDataCollector()
    
    # Define 2025 date range
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2025, 12, 31)
    
    all_liquidations = []
    
    # Fetch in chunks (Binance limits to 1000 records per request)
    current_date = start_date
    chunk_days = 7  # Fetch 1 week at a time
    
    while current_date < end_date:
        chunk_end = min(current_date + timedelta(days=chunk_days), end_date)
        
        print(f"\n📅 Fetching {current_date.date()} to {chunk_end.date()}...")
        
        # Binance liquidations
        binance_df = collector.fetch_binance_liquidations(
            symbol="BTCUSDT",
            start_time=current_date,
            end_time=chunk_end,
            limit=1000
        )
        
        if not binance_df.empty:
            all_liquidations.append(binance_df)
        
        # Rate limit
        time.sleep(0.5)
        
        # Bybit liquidations (smaller limit, so less frequent)
        if current_date.day == 1:  # Once per month
            bybit_df = collector.fetch_bybit_liquidations(
                symbol="BTCUSDT",
                start_time=current_date,
                limit=50
            )
            if not bybit_df.empty:
                all_liquidations.append(bybit_df)
            time.sleep(0.5)
        
        current_date = chunk_end
    
    # Combine all data
    if all_liquidations:
        combined_df = pd.concat(all_liquidations, ignore_index=True)
        combined_df = combined_df.sort_values('timestamp').reset_index(drop=True)
        
        print(f"\n✅ Total liquidation records collected: {len(combined_df)}")
        print(f"   Date range: {combined_df['timestamp'].min()} to {combined_df['timestamp'].max()}")
        
        # Save raw data
        combined_df.to_csv('liquidations_2025_raw.csv', index=False)
        print(f"   💾 Saved to liquidations_2025_raw.csv")
        
        # Aggregate to 5-minute timeframe
        agg_5m = collector.aggregate_liquidations_by_timeframe(combined_df, '5min')
        agg_5m.to_csv('liquidations_2025_5m.csv', index=False)
        print(f"   💾 Saved aggregated 5m data to liquidations_2025_5m.csv")
        
        # Show sample
        print(f"\n📊 Sample of aggregated data:")
        print(agg_5m.head(10))
        
        return combined_df, agg_5m
    else:
        print("❌ No liquidation data collected")
        return None, None

if __name__ == "__main__":
    raw_df, agg_df = download_2025_liquidation_data()
