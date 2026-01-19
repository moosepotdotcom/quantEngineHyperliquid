#!/usr/bin/env python3
"""
Hyperliquid Liquidation Data Collector
Collects real-time and historical liquidation data for BTC perpetuals
"""

import requests
import pandas as pd
import json
from datetime import datetime, timedelta
import time

class HyperliquidLiquidationCollector:
    """
    Collects liquidation data from Hyperliquid API
    
    Features:
    - Real-time liquidation events
    - Liquidation heatmap (price levels with high liquidation risk)
    - Historical liquidation analysis
    """
    
    def __init__(self):
        self.base_url = "https://api.hyperliquid.xyz/info"
        self.session = requests.Session()
        
    def get_recent_liquidations(self, symbol="BTC", hours=24):
        """
        Get recent liquidation events
        
        Returns:
            List of liquidation events with price, size, timestamp
        """
        
        payload = {
            "type": "userFills",
            "user": "liquidation"  # Special user for liquidations
        }
        
        try:
            response = self.session.post(self.base_url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Filter for BTC and recent timeframe
            cutoff_time = datetime.now() - timedelta(hours=hours)
            liquidations = []
            
            for event in data:
                if event.get('coin') == symbol:
                    event_time = datetime.fromtimestamp(event['time'] / 1000)
                    if event_time > cutoff_time:
                        liquidations.append({
                            'timestamp': event_time,
                            'price': float(event['px']),
                            'size': float(event['sz']),
                            'side': event['side'],  # 'A' = long liq, 'B' = short liq
                            'value_usd': float(event['px']) * float(event['sz'])
                        })
            
            return pd.DataFrame(liquidations)
            
        except Exception as e:
            print(f"Error fetching liquidations: {e}")
            return pd.DataFrame()
    
    def calculate_liquidation_heatmap(self, current_price, liquidations_df, bins=50):
        """
        Calculate liquidation density at different price levels
        
        Args:
            current_price: Current BTC price
            liquidations_df: DataFrame of recent liquidations
            bins: Number of price bins
            
        Returns:
            DataFrame with price levels and liquidation density
        """
        
        if liquidations_df.empty:
            return pd.DataFrame()
        
        # Create price range around current price (±10%)
        price_min = current_price * 0.90
        price_max = current_price * 1.10
        
        # Create bins
        price_bins = pd.cut(
            liquidations_df['price'],
            bins=bins,
            labels=False
        )
        
        # Aggregate liquidations by bin
        heatmap = liquidations_df.groupby(price_bins).agg({
            'value_usd': 'sum',
            'size': 'sum',
            'price': 'mean'
        }).reset_index(drop=True)
        
        heatmap.columns = ['total_value', 'total_size', 'avg_price']
        
        # Calculate density score (normalized)
        heatmap['density_score'] = (
            heatmap['total_value'] / heatmap['total_value'].max()
        )
        
        return heatmap.sort_values('avg_price')
    
    def get_liquidation_clusters(self, heatmap_df, threshold=0.7):
        """
        Identify price levels with high liquidation risk
        
        Args:
            heatmap_df: Liquidation heatmap
            threshold: Density threshold for clusters (0-1)
            
        Returns:
            List of price levels with high liquidation risk
        """
        
        if heatmap_df.empty:
            return []
        
        clusters = heatmap_df[heatmap_df['density_score'] >= threshold]
        
        return clusters[['avg_price', 'density_score', 'total_value']].to_dict('records')
    
    def get_liquidation_features(self, current_price):
        """
        Generate liquidation-based trading features
        
        Returns:
            Dictionary of features for ML model
        """
        
        # Get recent liquidations
        liq_df = self.get_recent_liquidations(hours=24)
        
        if liq_df.empty:
            return self._empty_features()
        
        # Calculate heatmap
        heatmap = self.calculate_liquidation_heatmap(current_price, liq_df)
        
        # Get clusters
        clusters = self.get_liquidation_clusters(heatmap)
        
        # Calculate features
        features = {
            # Volume metrics
            'liq_total_24h': liq_df['value_usd'].sum(),
            'liq_count_24h': len(liq_df),
            'liq_avg_size': liq_df['value_usd'].mean() if len(liq_df) > 0 else 0,
            
            # Directional bias
            'liq_long_pct': len(liq_df[liq_df['side'] == 'A']) / len(liq_df) if len(liq_df) > 0 else 0.5,
            'liq_short_pct': len(liq_df[liq_df['side'] == 'B']) / len(liq_df) if len(liq_df) > 0 else 0.5,
            
            # Cluster analysis
            'liq_cluster_count': len(clusters),
            'liq_nearest_cluster_dist': self._nearest_cluster_distance(current_price, clusters),
            'liq_cluster_above': len([c for c in clusters if c['avg_price'] > current_price]),
            'liq_cluster_below': len([c for c in clusters if c['avg_price'] < current_price]),
            
            # Recent activity (last 1 hour)
            'liq_recent_1h': len(liq_df[liq_df['timestamp'] > datetime.now() - timedelta(hours=1)]),
            'liq_recent_value_1h': liq_df[liq_df['timestamp'] > datetime.now() - timedelta(hours=1)]['value_usd'].sum(),
        }
        
        return features
    
    def _nearest_cluster_distance(self, current_price, clusters):
        """Calculate distance to nearest liquidation cluster"""
        if not clusters:
            return 999999
        
        distances = [abs(c['avg_price'] - current_price) / current_price for c in clusters]
        return min(distances) if distances else 999999
    
    def _empty_features(self):
        """Return empty features when no data available"""
        return {
            'liq_total_24h': 0,
            'liq_count_24h': 0,
            'liq_avg_size': 0,
            'liq_long_pct': 0.5,
            'liq_short_pct': 0.5,
            'liq_cluster_count': 0,
            'liq_nearest_cluster_dist': 999999,
            'liq_cluster_above': 0,
            'liq_cluster_below': 0,
            'liq_recent_1h': 0,
            'liq_recent_value_1h': 0,
        }

# Example usage
if __name__ == "__main__":
    collector = HyperliquidLiquidationCollector()
    
    print("="*60)
    print("🔥 Hyperliquid Liquidation Collector Test")
    print("="*60)
    
    # Get recent liquidations
    print("\n📊 Fetching recent liquidations...")
    liq_df = collector.get_recent_liquidations(hours=24)
    
    if not liq_df.empty:
        print(f"✅ Found {len(liq_df)} liquidations in last 24h")
        print(f"   Total Value: ${liq_df['value_usd'].sum():,.0f}")
        print(f"   Avg Size: ${liq_df['value_usd'].mean():,.0f}")
        print(f"   Long Liqs: {len(liq_df[liq_df['side'] == 'A'])}")
        print(f"   Short Liqs: {len(liq_df[liq_df['side'] == 'B'])}")
        
        # Get current BTC price (approximate from liquidations)
        current_price = liq_df['price'].iloc[-1]
        print(f"\n💰 Current BTC Price: ${current_price:,.2f}")
        
        # Calculate heatmap
        print("\n🗺️  Calculating liquidation heatmap...")
        heatmap = collector.calculate_liquidation_heatmap(current_price, liq_df)
        
        if not heatmap.empty:
            print(f"✅ Heatmap generated with {len(heatmap)} price levels")
            
            # Get clusters
            clusters = collector.get_liquidation_clusters(heatmap, threshold=0.6)
            print(f"\n🎯 Found {len(clusters)} liquidation clusters:")
            for c in clusters[:5]:  # Show top 5
                print(f"   ${c['avg_price']:,.2f} - Density: {c['density_score']:.2f} - Value: ${c['total_value']:,.0f}")
        
        # Get features
        print("\n📈 Generating features...")
        features = collector.get_liquidation_features(current_price)
        print("✅ Features:")
        for key, value in features.items():
            print(f"   {key}: {value}")
    else:
        print("❌ No liquidations found")
    
    print("\n" + "="*60)
    print("✅ Test Complete!")
    print("="*60)
