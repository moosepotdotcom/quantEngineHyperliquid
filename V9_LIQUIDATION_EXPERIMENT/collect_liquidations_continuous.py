#!/usr/bin/env python3
"""
CONTINUOUS REAL LIQUIDATION COLLECTOR
Runs continuously to build historical dataset
"""

import requests
import pandas as pd
from datetime import datetime
import time
import os

def collect_bybit_liquidations_continuous():
    """Continuously collect liquidations from Bybit"""
    
    print("🔥 CONTINUOUS LIQUIDATION COLLECTOR")
    print("="*70)
    print("Collecting from Bybit every 60 seconds...")
    print("Press Ctrl+C to stop")
    print()
    
    output_file = 'liquidation_data/REAL_liquidations_continuous.csv'
    
    # Load existing data if available
    if os.path.exists(output_file):
        df_existing = pd.read_csv(output_file)
        df_existing['timestamp'] = pd.to_datetime(df_existing['timestamp'])
        print(f"📂 Loaded {len(df_existing)} existing liquidations")
    else:
        df_existing = pd.DataFrame()
    
    collection_count = 0
    
    while True:
        try:
            # Fetch from Bybit
            url = "https://api.bybit.com/v5/market/recent-trade"
            params = {
                "category": "linear",
                "symbol": "BTCUSDT",
                "limit": 1000
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data['retCode'] == 0:
                    trades = data['result']['list']
                    
                    liquidations = []
                    for trade in trades:
                        size_btc = float(trade['size'])
                        
                        # Filter for significant trades
                        if size_btc >= 0.1:
                            liquidations.append({
                                'timestamp': pd.to_datetime(int(trade['time']), unit='ms'),
                                'coin': 'BTC',
                                'side': 'A' if trade['side'] == 'Sell' else 'B',
                                'price': float(trade['price']),
                                'size': size_btc,
                                'source': 'bybit_real'
                            })
                    
                    if len(liquidations) > 0:
                        df_new = pd.DataFrame(liquidations)
                        
                        # Combine with existing
                        if len(df_existing) > 0:
                            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                        else:
                            df_combined = df_new
                        
                        # Remove duplicates
                        df_combined = df_combined.drop_duplicates(subset=['timestamp', 'price', 'size'])
                        df_combined = df_combined.sort_values('timestamp').reset_index(drop=True)
                        
                        # Save
                        df_combined.to_csv(output_file, index=False)
                        
                        df_existing = df_combined
                        collection_count += 1
                        
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Collected {len(liquidations)} new | Total: {len(df_combined)} | Volume: {df_combined['size'].sum():.2f} BTC")
            
            # Wait 60 seconds
            time.sleep(60)
            
        except KeyboardInterrupt:
            print("\n\n✅ Collection stopped")
            print(f"Total collections: {collection_count}")
            print(f"Total liquidations: {len(df_existing)}")
            print(f"Saved to: {output_file}")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    collect_bybit_liquidations_continuous()
