#!/usr/bin/env python3
"""
Liquidation Heatmap Builder
Creates price-level liquidation clusters for magnet strategy
"""

import pandas as pd
import numpy as np
from collections import defaultdict

class LiquidationHeatmap:
    """Build and analyze liquidation heatmaps"""
    
    def __init__(self, price_bucket_size=100):
        """
        Args:
            price_bucket_size: Group liquidations into price buckets (e.g., $100 increments)
        """
        self.price_bucket_size = price_bucket_size
        self.heatmap = defaultdict(lambda: {'long_liq': 0, 'short_liq': 0, 'total': 0})
        
    def add_liquidation(self, price, size, side):
        """
        Add a liquidation to the heatmap
        
        Args:
            price: Liquidation price
            size: Position size liquidated
            side: 'A' (ask/long liq) or 'B' (bid/short liq)
        """
        # Round price to bucket
        bucket = round(price / self.price_bucket_size) * self.price_bucket_size
        
        if side == 'A':  # Long liquidation
            self.heatmap[bucket]['long_liq'] += size
        else:  # Short liquidation
            self.heatmap[bucket]['short_liq'] += size
        
        self.heatmap[bucket]['total'] += size
    
    def get_clusters(self, current_price, min_cluster_size=10):
        """
        Get significant liquidation clusters
        
        Args:
            current_price: Current market price
            min_cluster_size: Minimum size to be considered a cluster
            
        Returns:
            DataFrame with clusters above and below current price
        """
        clusters = []
        
        for price_level, data in self.heatmap.items():
            if data['total'] >= min_cluster_size:
                distance = price_level - current_price
                distance_pct = (distance / current_price) * 100
                
                clusters.append({
                    'price': price_level,
                    'long_liq': data['long_liq'],
                    'short_liq': data['short_liq'],
                    'total_size': data['total'],
                    'distance': distance,
                    'distance_pct': distance_pct,
                    'direction': 'above' if distance > 0 else 'below'
                })
        
        df = pd.DataFrame(clusters)
        if len(df) > 0:
            df = df.sort_values('distance_pct')
        
        return df
    
    def get_magnet_zones(self, current_price, lookback_pct=2.0):
        """
        Get "magnet zones" - strong liquidation clusters that attract price
        
        Args:
            current_price: Current market price
            lookback_pct: Look within ±X% of current price
            
        Returns:
            Top magnet zones above and below price
        """
        clusters = self.get_clusters(current_price)
        
        if len(clusters) == 0:
            return None, None
        
        # Filter to nearby clusters
        nearby = clusters[abs(clusters['distance_pct']) <= lookback_pct]
        
        if len(nearby) == 0:
            return None, None
        
        # Get strongest clusters above and below
        above = nearby[nearby['direction'] == 'above'].nlargest(3, 'total_size')
        below = nearby[nearby['direction'] == 'below'].nlargest(3, 'total_size')
        
        return above, below

def build_heatmap_from_historical_data(df_liquidations):
    """
    Build heatmap from historical liquidation data
    
    Args:
        df_liquidations: DataFrame with columns: timestamp, px, sz, side
        
    Returns:
        LiquidationHeatmap object
    """
    print("🗺️  Building Liquidation Heatmap...")
    
    heatmap = LiquidationHeatmap(price_bucket_size=100)
    
    for _, row in df_liquidations.iterrows():
        heatmap.add_liquidation(
            price=row['px'],
            size=row['sz'],
            side=row['side']
        )
    
    print(f"   ✅ Processed {len(df_liquidations)} liquidations")
    print(f"   ✅ Created {len(heatmap.heatmap)} price levels")
    
    return heatmap

def analyze_magnet_strategy(df_price, df_liquidations):
    """
    Analyze how well the magnet strategy would have worked
    
    Args:
        df_price: Historical price data
        df_liquidations: Historical liquidation data
        
    Returns:
        Analysis results
    """
    print("\n📊 Analyzing Liquidation Magnet Strategy...")
    
    # Build heatmap
    heatmap = build_heatmap_from_historical_data(df_liquidations)
    
    # For each price point, check if it moved towards nearest magnet
    results = []
    
    for i in range(len(df_price) - 20):
        current_price = df_price.iloc[i]['close']
        future_prices = df_price.iloc[i+1:i+21]['close']
        
        # Get magnet zones
        above, below = heatmap.get_magnet_zones(current_price, lookback_pct=1.0)
        
        if above is not None and len(above) > 0:
            nearest_above = above.iloc[0]['price']
            hit_above = any(future_prices >= nearest_above)
            
            if hit_above:
                results.append({
                    'direction': 'up',
                    'target': nearest_above,
                    'hit': True
                })
        
        if below is not None and len(below) > 0:
            nearest_below = below.iloc[0]['price']
            hit_below = any(future_prices <= nearest_below)
            
            if hit_below:
                results.append({
                    'direction': 'down',
                    'target': nearest_below,
                    'hit': True
                })
    
    df_results = pd.DataFrame(results)
    
    if len(df_results) > 0:
        hit_rate = len(df_results[df_results['hit'] == True]) / len(df_results)
        print(f"\n   🎯 Magnet Hit Rate: {hit_rate:.1%}")
        print(f"   📈 Up magnets: {len(df_results[df_results['direction']=='up'])}")
        print(f"   📉 Down magnets: {len(df_results[df_results['direction']=='down'])}")
    
    return df_results

if __name__ == "__main__":
    print("🗺️  Liquidation Heatmap Builder")
    print("="*70)
    print("\nThis module builds liquidation heatmaps for the magnet strategy")
    print("Use with historical liquidation data to identify price magnets")
