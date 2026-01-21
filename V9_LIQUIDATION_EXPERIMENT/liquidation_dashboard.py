#!/usr/bin/env python3
"""
Liquidation Dashboard - All-in-One Monitoring Tool
Combines monitor, heatmap, and predictor
"""

import os
import sys
import time
from datetime import datetime
import threading

# Import our tools
from liquidation_monitor import LiquidationMonitor
from heatmap_visualizer import LiquidationHeatmapVisualizer
from liquidation_predictor import LiquidationPredictor

class LiquidationDashboard:
    """Unified dashboard for liquidation monitoring"""
    
    def __init__(self):
        self.monitor = LiquidationMonitor()
        self.visualizer = LiquidationHeatmapVisualizer()
        self.predictor = LiquidationPredictor()
        self.running = False
    
    def start_monitor_background(self):
        """Start monitor in background thread"""
        def run_monitor():
            try:
                self.monitor.start()
            except Exception as e:
                print(f"Monitor error: {e}")
        
        monitor_thread = threading.Thread(target=run_monitor, daemon=True)
        monitor_thread.start()
        
        # Wait for connection
        time.sleep(3)
    
    def print_dashboard(self):
        """Print comprehensive dashboard"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("╔" + "="*68 + "╗")
        print("║" + " "*15 + "LIQUIDATION MONITORING DASHBOARD" + " "*21 + "║")
        print("╚" + "="*68 + "╝")
        print()
        
        # Monitor stats
        print("📊 MONITOR STATUS:")
        print(f"   Running: {'✅ YES' if self.monitor.running else '❌ NO'}")
        print(f"   Total liquidations: {self.monitor.stats['total_liquidations']}")
        print(f"   Long liquidations: {self.monitor.stats['long_liquidations']}")
        print(f"   Short liquidations: {self.monitor.stats['short_liquidations']}")
        
        if self.monitor.stats['last_liquidation']:
            last = self.monitor.stats['last_liquidation']
            print(f"   Last: ${last['price']:.2f} ({last['size']:.4f} BTC)")
        
        # Liquidation rate
        rate = self.monitor.get_liquidation_rate(minutes=10)
        print(f"   Rate (10min): {rate:.2f} liq/min")
        print()
        
        # Prediction
        current_price = self.predictor.get_current_price()
        if current_price:
            self.predictor.print_prediction_report()
            
            # Heatmap
            self.visualizer.print_heatmap(current_price, lookback_hours=24)
        
        print("\n" + "="*70)
        print(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
        print("Press Ctrl+C to stop")
    
    def run(self, refresh_seconds=30):
        """Run dashboard with auto-refresh"""
        print("🚀 Starting Liquidation Dashboard...")
        print("   Connecting to Hyperliquid...")
        
        # Start monitor
        self.start_monitor_background()
        
        self.running = True
        
        try:
            while self.running:
                self.print_dashboard()
                time.sleep(refresh_seconds)
        
        except KeyboardInterrupt:
            print("\n\n⏹️  Stopping dashboard...")
            self.monitor.stop()
            self.running = False

if __name__ == "__main__":
    dashboard = LiquidationDashboard()
    dashboard.run(refresh_seconds=30)
