#!/usr/bin/env python3
"""
🚀 HYPERLIQUID SCALPER V3 - SYSTEM ONE
Entry point for the modular scalping system.
"""
import sys
import time
import threading
import logging
from datetime import datetime

# Setup paths
sys.path.append('..') 

from scalper_system import config
# We will import modules as we create them
# from scalper_system.feed import LiquidationStream
# from scalper_system.strategy import StrategyEngine
# from scalper_system.execution import OrderManager

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LIVE_LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("SYSTEM")

class ScalperSystem:
    def __init__(self, dry_run=True):
        self.running = False
        self.dry_run = dry_run
        logger.info(f"Initializing System (Dry Run: {dry_run})")
        
    def start(self):
        self.running = True
        logger.info("🌊 System Started")
        
        # Initialize Modules
        from scalper_system.feed import LiquidationStream
        from scalper_system.strategy import StrategyEngine
        from scalper_system.execution import OrderManager
        from scalper_system.recorder import CSVRecorder
        
        # 1. Execution
        self.executor = OrderManager(dry_run=self.dry_run)
        
        # 2. Strategy (Callbacks to Execution)
        self.strategy = StrategyEngine(execution_callback=self.executor.execute)
        
        # 3. Recorder
        self.recorder = CSVRecorder()
        
        # 4. Data Feed (Callbacks to Strategy AND Recorder)
        self.feed = LiquidationStream()
        self.feed.add_callback(self.strategy.on_event)
        self.feed.add_callback(self.recorder.on_event)
        self.feed.start()
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
            
    def stop(self):
        self.running = False
        logger.info("👋 System Shutting Down...")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true', help='Enable LIVE TRADING')
    args = parser.parse_args()
    
    system = ScalperSystem(dry_run=not args.live)
    system.start()
