#!/usr/bin/env python3
"""
Liquidation Heatmap Visualizer
Real-time visualization of liquidation clusters
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

class LiquidationHeatmapVisualizer:
    """Visualize and analyze liquidation heatmaps"""
    
    def __init__(self, data_dir='liquidation_data'):
        self.data_dir = data_dir
    
    def load_recent_liquidations(self, hours=24):
        """Load liquidations from last N hours"""
        all_liqs = []
        
        # Load files from last N days
        for days_ago in range(int(hours/24) + 2):
            date = datetime.now() - timedelta(days=days_ago)
            filename = f"liquidations_{date.strftime('%Y%m%d')}.csv"
            filepath = os.path.join(self.data_dir, filename)
            
            if os.path.exists(filepath):
                df = pd.read_csv(filepath)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                all_liqs.append(df)
        
        if not all_liqs:
            return pd.DataFrame()
        
        df_all = pd.concat(all_liqs, ignore_index=True)
        
        # Filter to last N hours
        cutoff = datetime.now() - timedelta(hours=hours)
        df_recent = df_all[df_all['timestamp'] > cutoff]
        
        return df_recent
    
    def build_heatmap(self, df_liquidations, bucket_size=100):
        """
        Build price-level heatmap
        
        Returns:
            DataFrame with columns: price_level, long_liq, short_liq, total, intensity
        """
        if len(df_liquidations) == 0:
            return pd.DataFrame()
        
        # Group by price buckets
        df_liquidations['price_bucket'] = (
            (df_liquidations['price'] / bucket_size).round() * bucket_size
        )
        
        # Aggregate by bucket and side
        heatmap_data = []
        
        for price_level in df_liquidations['price_bucket'].unique():
            bucket_data = df_liquidations[df_liquidations['price_bucket'] == price_level]
            
            long_liq = bucket_data[bucket_data['side'] == 'A']['size'].sum()
            short_liq = bucket_data[bucket_data['side'] == 'B']['size'].sum()
            total = long_liq + short_liq
            
            heatmap_data.append({
                'price_level': price_level,
                'long_liq': long_liq,
                'short_liq': short_liq,
                'total': total,
                'count': len(bucket_data)
            })
        
        df_heatmap = pd.DataFrame(heatmap_data)
        df_heatmap = df_heatmap.sort_values('price_level')
        
        # Calculate intensity (normalized 0-100)
        if len(df_heatmap) > 0:
            max_total = df_heatmap['total'].max()
            df_heatmap['intensity'] = (df_heatmap['total'] / max_total * 100).round(1)
        
        return df_heatmap
    
    def identify_clusters(self, df_heatmap, current_price, min_intensity=20):
        """
        Identify significant liquidation clusters
        
        Returns:
            DataFrame with nearby clusters sorted by distance
        """
        if len(df_heatmap) == 0:
            return pd.DataFrame()
        
        # Filter significant clusters
        clusters = df_heatmap[df_heatmap['intensity'] >= min_intensity].copy()
        
        # Calculate distance from current price
        clusters['distance'] = clusters['price_level'] - current_price
        clusters['distance_pct'] = (clusters['distance'] / current_price * 100).round(3)
        clusters['direction'] = clusters['distance'].apply(lambda x: 'ABOVE' if x > 0 else 'BELOW')
        
        # Sort by absolute distance
        clusters['abs_distance'] = clusters['distance'].abs()
        clusters = clusters.sort_values('abs_distance')
        
        return clusters[['price_level', 'long_liq', 'short_liq', 'total', 
                        'intensity', 'distance', 'distance_pct', 'direction']]
    
    def print_heatmap(self, current_price, lookback_hours=24):
        """Print ASCII heatmap visualization"""
        print("\n🗺️  LIQUIDATION HEATMAP")
        print("="*70)
        
        # Load data
        df_liqs = self.load_recent_liquidations(lookback_hours)
        
        if len(df_liqs) == 0:
            print("   ⚠️  No liquidation data available")
            print(f"   Waiting for liquidations... (monitoring {lookback_hours}h)")
            return
        
        print(f"   Period: Last {lookback_hours} hours")
        print(f"   Total liquidations: {len(df_liqs)}")
        print(f"   Current price: ${current_price:,.2f}")
        print()
        
        # Build heatmap
        df_heatmap = self.build_heatmap(df_liqs, bucket_size=100)
        
        # Identify clusters
        clusters = self.identify_clusters(df_heatmap, current_price, min_intensity=15)
        
        if len(clusters) == 0:
            print("   ⚠️  No significant clusters found")
            return
        
        # Show top clusters
        print("   🎯 SIGNIFICANT CLUSTERS:")
        print()
        print("   Price Level  | Direction | Distance | Intensity | Size (BTC)")
        print("   " + "-"*65)
        
        for _, cluster in clusters.head(10).iterrows():
            bar_length = int(cluster['intensity'] / 5)
            bar = "█" * bar_length
            
            print(f"   ${cluster['price_level']:>10,.0f} | "
                  f"{cluster['direction']:>9} | "
                  f"{cluster['distance_pct']:>+6.2f}% | "
                  f"{bar:10} | "
                  f"{cluster['total']:>8.2f}")
        
        # Show nearest magnets
        print("\n   🧲 NEAREST MAGNETS:")
        above = clusters[clusters['direction'] == 'ABOVE'].head(1)
        below = clusters[clusters['direction'] == 'BELOW'].head(1)
        
        if len(above) > 0:
            a = above.iloc[0]
            print(f"      ⬆️  ABOVE: ${a['price_level']:,.0f} ({a['distance_pct']:+.2f}%) - {a['total']:.2f} BTC")
        
        if len(below) > 0:
            b = below.iloc[0]
            print(f"      ⬇️  BELOW: ${b['price_level']:,.0f} ({b['distance_pct']:+.2f}%) - {b['total']:.2f} BTC")
        
        print()

def visualize_current_heatmap(current_price):
    """Quick visualization of current heatmap"""
    viz = LiquidationHeatmapVisualizer()
    viz.print_heatmap(current_price, lookback_hours=24)

if __name__ == "__main__":
    # Example: Visualize heatmap at current BTC price
    # Get current price from API or use approximate
    current_btc_price = 102000  # Update with real price
    
    visualize_current_heatmap(current_btc_price)
