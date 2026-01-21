#!/usr/bin/env python3
"""
Unified Phase 4 Data Collector - COMPLETE VERSION
Integrates: Order Flow + Funding Rates + Liquidations (simulated from price action)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from working_collectors import WorkingCollectors
import pandas as pd
from datetime import datetime
import time

class UnifiedPhase4Collector:
    """
    Complete Phase 4 data collector with all features:
    - Order flow (real-time order book)
    - Funding rates (real-time)
    - Liquidation zones (calculated from price levels)
    """
    
    def __init__(self):
        self.collector = WorkingCollectors()
        
    def calculate_liquidation_zones(self, current_price, leverage=50):
        """
        Calculate liquidation price zones based on leverage
        
        With 50x leverage, liquidation happens at ~2% move
        """
        liq_threshold = 0.02  # 2% for 50x leverage
        
        # Calculate key liquidation levels
        long_liq_near = current_price * (1 - liq_threshold)      # -2%
        long_liq_far = current_price * (1 - liq_threshold * 2)   # -4%
        short_liq_near = current_price * (1 + liq_threshold)     # +2%
        short_liq_far = current_price * (1 + liq_threshold * 2)  # +4%
        
        # Calculate distance to nearest zone
        distances = [
            abs(current_price - long_liq_near),
            abs(current_price - long_liq_far),
            abs(current_price - short_liq_near),
            abs(current_price - short_liq_far)
        ]
        
        nearest_dist_pct = (min(distances) / current_price) * 100
        
        return {
            'liq_long_near': long_liq_near,
            'liq_long_far': long_liq_far,
            'liq_short_near': short_liq_near,
            'liq_short_far': short_liq_far,
            'liq_nearest_dist_pct': nearest_dist_pct,
            'liq_in_danger_zone': 1 if nearest_dist_pct < 1.0 else 0  # Within 1% of liquidation
        }
    
    def collect_all_features(self):
        """
        Collect complete feature set from all sources
        
        Returns:
            Dictionary with ~20 features
        """
        
        # Get current price
        current_price = self.collector.get_current_price()
        
        if current_price == 0:
            print("⚠️  Failed to get current price")
            return None
        
        print(f"📊 Collecting features for BTC @ ${current_price:,.2f}")
        
        # 1. Order flow features (7 features)
        print("   📖 Order flow...")
        ob_features = self.collector.get_orderbook_features()
        
        # 2. Funding features (5 features)
        print("   💰 Funding rates...")
        funding_features = self.collector.get_funding_features()
        
        # 3. Liquidation features (6 features)
        print("   🔥 Liquidation zones...")
        liq_features = self.calculate_liquidation_zones(current_price)
        
        # Combine all features
        all_features = {
            'timestamp': datetime.now(),
            'price': current_price,
            **ob_features,
            **funding_features,
            **liq_features
        }
        
        print(f"   ✅ Collected {len(all_features)} features")
        
        return all_features
    
    def collect_continuous(self, interval_seconds=300, max_samples=None, output_file="phase4_training_data.csv"):
        """
        Collect data continuously for model training
        
        Args:
            interval_seconds: Time between samples (300 = 5 min)
            max_samples: Max samples to collect (None = infinite)
            output_file: CSV file to save data
        """
        
        print("="*60)
        print("🚀 Phase 4 Unified Data Collector")
        print("="*60)
        print(f"Interval: {interval_seconds}s ({interval_seconds/60:.1f} min)")
        print(f"Output: {output_file}")
        print(f"Features: ~20 (order flow + funding + liquidations)")
        if max_samples:
            print(f"Max samples: {max_samples}")
        print("Press Ctrl+C to stop")
        print("="*60)
        
        sample_count = 0
        
        try:
            while True:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Sample {sample_count + 1}...")
                
                # Collect features
                features = self.collect_all_features()
                
                if features:
                    # Save to CSV
                    df = pd.DataFrame([features])
                    
                    if os.path.exists(output_file):
                        df.to_csv(output_file, mode='a', header=False, index=False)
                    else:
                        df.to_csv(output_file, index=False)
                    
                    print(f"   💾 Saved! Imbalance: {features['ob_imbalance']:.3f}, Funding: {features['funding_pct']:.4f}%")
                    sample_count += 1
                    
                    if max_samples and sample_count >= max_samples:
                        print(f"\n✅ Reached {max_samples} samples!")
                        break
                else:
                    print("   ⚠️  Failed to collect data")
                
                # Wait for next interval
                if not max_samples or sample_count < max_samples:
                    print(f"   ⏳ Next sample in {interval_seconds}s...")
                    time.sleep(interval_seconds)
                    
        except KeyboardInterrupt:
            print("\n\n🛑 Stopped by user")
        
        print(f"\n{'='*60}")
        print(f"✅ Collection Complete!")
        print(f"   Samples collected: {sample_count}")
        print(f"   Data saved to: {output_file}")
        print(f"{'='*60}")
        
        return sample_count

# Quick test mode
def quick_test():
    """Quick test - collect 3 samples"""
    print("="*60)
    print("⚡ Quick Test Mode (3 samples)")
    print("="*60)
    
    collector = UnifiedPhase4Collector()
    collector.collect_continuous(interval_seconds=10, max_samples=3, output_file="test_phase4_data.csv")

# Main
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Phase 4 Unified Data Collector')
    parser.add_argument('--mode', choices=['test', 'collect'], default='test',
                       help='Mode: test (3 samples) or collect (continuous)')
    parser.add_argument('--samples', type=int, default=None,
                       help='Number of samples (None = infinite)')
    parser.add_argument('--interval', type=int, default=300,
                       help='Seconds between samples (default: 300 = 5min)')
    parser.add_argument('--output', type=str, default='phase4_training_data.csv',
                       help='Output CSV file')
    
    args = parser.parse_args()
    
    collector = UnifiedPhase4Collector()
    
    if args.mode == 'test':
        quick_test()
    else:
        collector.collect_continuous(
            interval_seconds=args.interval,
            max_samples=args.samples,
            output_file=args.output
        )
