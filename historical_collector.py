#!/usr/bin/env python3
"""
Historical Data Collector for Phase 4
Collects Phase 4 features aligned with existing price data
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from working_collectors import WorkingCollectors

class HistoricalDataCollector:
    """
    Collects Phase 4 features for historical backtesting
    
    Since we can't get historical order book/funding data from API,
    we'll simulate realistic features based on price action
    """
    
    def __init__(self):
        self.live_collector = WorkingCollectors()
        
    def simulate_orderflow_features(self, df_row, lookback_rows):
        """
        Simulate order flow features based on price action
        
        Args:
            df_row: Current price row
            lookback_rows: Previous rows for context
        """
        
        # Calculate price momentum
        if len(lookback_rows) > 0:
            price_change = (df_row['close'] - lookback_rows.iloc[-1]['close']) / lookback_rows.iloc[-1]['close']
        else:
            price_change = 0
        
        # Simulate imbalance based on price direction
        # Strong up move = bullish imbalance, strong down = bearish
        imbalance = np.tanh(price_change * 100)  # -1 to 1
        
        # Simulate depth based on volatility
        volatility = df_row.get('atr_ratio', 0.01)
        base_depth = 50  # BTC
        bid_depth = base_depth * (1 + imbalance * 0.5)
        ask_depth = base_depth * (1 - imbalance * 0.5)
        
        # Simulate large orders based on volume
        volume_ratio = df_row['volume'] / lookback_rows['volume'].mean() if len(lookback_rows) > 0 else 1
        large_bids = int(volume_ratio * (1 + imbalance)) if imbalance > 0 else 0
        large_asks = int(volume_ratio * (1 - imbalance)) if imbalance < 0 else 0
        
        return {
            'ob_imbalance': imbalance,
            'ob_bid_depth': bid_depth,
            'ob_ask_depth': ask_depth,
            'ob_large_bids': large_bids,
            'ob_large_asks': large_asks,
            'ob_spread_pct': volatility * 0.1  # Spread widens with volatility
        }
    
    def simulate_funding_features(self, df_row, lookback_rows):
        """
        Simulate funding rate features based on price trends
        
        Funding rate typically follows price momentum with lag
        """
        
        if len(lookback_rows) < 24:
            return {
                'funding_rate': 0.0001,
                'funding_pct': 0.01,
                'funding_is_extreme': 0
            }
        
        # Calculate 24h price change
        price_24h_ago = lookback_rows.iloc[-24]['close']
        price_change_24h = (df_row['close'] - price_24h_ago) / price_24h_ago
        
        # Funding follows price with dampening
        # Typical range: -0.05% to +0.1%
        funding = price_change_24h * 0.01  # Scale down
        funding = np.clip(funding, -0.0005, 0.001)  # Realistic bounds
        
        is_extreme = 1 if abs(funding) > 0.0008 else 0
        
        return {
            'funding_rate': funding,
            'funding_pct': funding * 100,
            'funding_is_extreme': is_extreme
        }
    
    def simulate_liquidation_features(self, df_row, lookback_rows):
        """
        Simulate liquidation features based on volatility and price action
        
        Liquidations spike during volatile moves
        """
        
        if len(lookback_rows) < 10:
            return {
                'liq_cluster_nearby': 0,
                'liq_pressure': 0
            }
        
        # High volatility = more liquidations
        volatility = df_row.get('atr_ratio', 0.01)
        
        # Recent sharp moves = liquidation clusters
        recent_range = lookback_rows.iloc[-10:]['high'].max() - lookback_rows.iloc[-10:]['low'].min()
        avg_range = lookback_rows.iloc[-50:]['high'].mean() - lookback_rows.iloc[-50:]['low'].mean() if len(lookback_rows) >= 50 else recent_range
        
        range_ratio = recent_range / avg_range if avg_range > 0 else 1
        
        # Cluster nearby if we're in volatile zone
        cluster_nearby = 1 if range_ratio > 1.5 else 0
        
        # Liquidation pressure (0-1)
        liq_pressure = min(volatility * 50, 1.0)
        
        return {
            'liq_cluster_nearby': cluster_nearby,
            'liq_pressure': liq_pressure
        }
    
    def collect_features_for_dataset(self, price_df):
        """
        Collect Phase 4 features for entire dataset
        
        Args:
            price_df: DataFrame with OHLCV + indicators
            
        Returns:
            DataFrame with Phase 4 features added
        """
        
        print(f"📊 Collecting Phase 4 features for {len(price_df)} rows...")
        
        phase4_features = []
        
        for i in range(len(price_df)):
            row = price_df.iloc[i]
            lookback = price_df.iloc[max(0, i-100):i]  # Last 100 rows for context
            
            # Simulate features
            ob_features = self.simulate_orderflow_features(row, lookback)
            funding_features = self.simulate_funding_features(row, lookback)
            liq_features = self.simulate_liquidation_features(row, lookback)
            
            # Combine
            features = {
                **ob_features,
                **funding_features,
                **liq_features
            }
            
            phase4_features.append(features)
            
            if (i + 1) % 1000 == 0:
                print(f"   Processed {i+1}/{len(price_df)} rows...")
        
        # Convert to DataFrame
        phase4_df = pd.DataFrame(phase4_features)
        
        # Combine with original data
        result = pd.concat([price_df.reset_index(drop=True), phase4_df], axis=1)
        
        print(f"✅ Phase 4 features collected! Total columns: {len(result.columns)}")
        
        return result

# Example usage
if __name__ == "__main__":
    print("="*60)
    print("📦 Phase 4 Historical Data Collector")
    print("="*60)
    
    # Test with December data
    data_file = "../dec2025_binance_data.csv"
    
    if not os.path.exists(data_file):
        print(f"❌ Data file not found: {data_file}")
        sys.exit(1)
    
    print(f"\n📂 Loading {data_file}...")
    df = pd.read_csv(data_file)
    print(f"✅ Loaded {len(df)} rows")
    
    # Collect features
    collector = HistoricalDataCollector()
    df_with_features = collector.collect_features_for_dataset(df)
    
    # Save
    output_file = "dec2025_with_phase4_features.csv"
    df_with_features.to_csv(output_file, index=False)
    print(f"\n💾 Saved to {output_file}")
    
    # Show sample
    print(f"\n📊 Sample features:")
    phase4_cols = ['ob_imbalance', 'ob_bid_depth', 'funding_rate', 'liq_pressure']
    print(df_with_features[phase4_cols].head(10))
    
    print("\n" + "="*60)
    print("✅ Historical data collection complete!")
    print("="*60)
