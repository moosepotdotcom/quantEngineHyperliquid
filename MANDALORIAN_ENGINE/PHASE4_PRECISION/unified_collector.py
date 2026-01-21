#!/usr/bin/env python3
"""
Unified Phase 4 Feature Collector
Combines all data sources into a single feature set
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from liquidation_collector import HyperliquidLiquidationCollector
from orderflow_tracker import OrderFlowTracker
from funding_monitor import FundingRateMonitor
import pandas as pd
from datetime import datetime

class Phase4FeatureCollector:
    """
    Unified collector for all Phase 4 features
    
    Combines:
    - Liquidation data
    - Order flow metrics
    - Funding rates
    - Open interest
    """
    
    def __init__(self):
        self.liq_collector = HyperliquidLiquidationCollector()
        self.orderflow_tracker = OrderFlowTracker()
        self.funding_monitor = FundingRateMonitor()
        
    def get_all_features(self, current_price):
        """
        Collect all Phase 4 features
        
        Args:
            current_price: Current BTC price
            
        Returns:
            Dictionary with all features
        """
        
        print(f"📊 Collecting Phase 4 features for BTC @ ${current_price:,.2f}")
        
        # Collect from each source
        print("   🔥 Liquidation features...")
        liq_features = self.liq_collector.get_liquidation_features(current_price)
        
        print("   📖 Order flow features...")
        orderflow_features = self.orderflow_tracker.get_orderflow_features(current_price)
        
        print("   💰 Funding rate features...")
        funding_features = self.funding_monitor.get_funding_features()
        
        # Combine all features
        all_features = {
            **liq_features,
            **orderflow_features,
            **funding_features,
            'timestamp': datetime.now(),
            'price': current_price
        }
        
        print(f"   ✅ Collected {len(all_features)} features")
        
        return all_features
    
    def get_feature_names(self):
        """Get list of all feature names"""
        sample_features = self.get_all_features(100000)  # Dummy price
        return list(sample_features.keys())
    
    def save_features(self, features, filename="phase4_features.csv"):
        """Save features to CSV"""
        df = pd.DataFrame([features])
        
        # Append if file exists
        if os.path.exists(filename):
            df.to_csv(filename, mode='a', header=False, index=False)
        else:
            df.to_csv(filename, index=False)
        
        print(f"✅ Features saved to {filename}")

# Example usage
if __name__ == "__main__":
    collector = Phase4FeatureCollector()
    
    print("="*60)
    print("🚀 Phase 4 Unified Feature Collector Test")
    print("="*60)
    
    # Get current price (approximate)
    current_price = 102000  # You would get this from live data
    
    # Collect all features
    features = collector.get_all_features(current_price)
    
    print("\n📈 Feature Summary:")
    print(f"   Total features: {len(features)}")
    print(f"\n   Sample features:")
    for key, value in list(features.items())[:15]:
        print(f"      {key}: {value}")
    
    # Save features
    print("\n💾 Saving features...")
    collector.save_features(features)
    
    print("\n" + "="*60)
    print("✅ Test Complete!")
    print("="*60)
