#!/usr/bin/env python3
"""
Real-Time Data Collector for Phase 4
Collects actual order book, funding, and price data from Hyperliquid API
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from working_collectors import WorkingCollectors
import pandas as pd
import time
from datetime import datetime
import signal

class RealTimeDataCollector:
    """
    Collects real market data from Hyperliquid API
    Saves to CSV for model training
    """
    
    def __init__(self, output_file="real_market_data.csv"):
        self.collector = WorkingCollectors()
        self.output_file = output_file
        self.running = True
        
        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        
    def signal_handler(self, sig, frame):
        print("\n\n🛑 Stopping data collection...")
        self.running = False
    
    def collect_snapshot(self):
        """Collect one snapshot of market data"""
        try:
            features = self.collector.get_all_features()
            return features
        except Exception as e:
            print(f"❌ Error collecting data: {e}")
            return None
    
    def save_snapshot(self, features):
        """Save snapshot to CSV"""
        df = pd.DataFrame([features])
        
        # Append if file exists
        if os.path.exists(self.output_file):
            df.to_csv(self.output_file, mode='a', header=False, index=False)
        else:
            df.to_csv(self.output_file, index=False)
    
    def collect_continuous(self, interval_seconds=300, max_samples=None):
        """
        Collect data continuously
        
        Args:
            interval_seconds: Time between samples (default: 300 = 5 min)
            max_samples: Maximum samples to collect (None = infinite)
        """
        
        print("="*60)
        print("📡 Real-Time Data Collector Started")
        print("="*60)
        print(f"Interval: {interval_seconds}s ({interval_seconds/60:.1f} min)")
        print(f"Output: {self.output_file}")
        print(f"Press Ctrl+C to stop")
        print("="*60)
        
        sample_count = 0
        
        while self.running:
            # Collect snapshot
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Collecting sample {sample_count + 1}...")
            
            features = self.collect_snapshot()
            
            if features:
                self.save_snapshot(features)
                print(f"✅ Saved! Price: ${features['price']:,.2f}, Imbalance: {features['ob_imbalance']:.3f}")
                sample_count += 1
                
                if max_samples and sample_count >= max_samples:
                    print(f"\n✅ Reached {max_samples} samples. Stopping.")
                    break
            else:
                print("⚠️  Failed to collect data, retrying...")
            
            # Wait for next interval
            if self.running:
                print(f"⏳ Waiting {interval_seconds}s for next sample...")
                time.sleep(interval_seconds)
        
        print(f"\n{'='*60}")
        print(f"✅ Collection Complete! Collected {sample_count} samples")
        print(f"📁 Data saved to: {self.output_file}")
        print(f"{'='*60}")

# Quick collection mode
def quick_collect(num_samples=12, interval_seconds=60):
    """
    Quick collection mode - collect N samples rapidly
    
    Args:
        num_samples: Number of samples (default: 12 = 1 hour at 5min intervals)
        interval_seconds: Seconds between samples (default: 60 = 1 min for testing)
    """
    
    print("="*60)
    print("⚡ Quick Collection Mode")
    print("="*60)
    print(f"Collecting {num_samples} samples at {interval_seconds}s intervals")
    print(f"Total time: ~{num_samples * interval_seconds / 60:.1f} minutes")
    print("="*60)
    
    collector = RealTimeDataCollector("quick_real_data.csv")
    collector.collect_continuous(interval_seconds=interval_seconds, max_samples=num_samples)

# Main
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Collect real market data from Hyperliquid')
    parser.add_argument('--mode', choices=['quick', 'continuous'], default='quick',
                       help='Collection mode (quick=12 samples, continuous=infinite)')
    parser.add_argument('--samples', type=int, default=12,
                       help='Number of samples for quick mode')
    parser.add_argument('--interval', type=int, default=60,
                       help='Seconds between samples')
    parser.add_argument('--output', type=str, default='real_market_data.csv',
                       help='Output CSV file')
    
    args = parser.parse_args()
    
    if args.mode == 'quick':
        quick_collect(num_samples=args.samples, interval_seconds=args.interval)
    else:
        collector = RealTimeDataCollector(args.output)
        collector.collect_continuous(interval_seconds=args.interval)
