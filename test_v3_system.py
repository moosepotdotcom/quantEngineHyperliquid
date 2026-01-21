"""
🧪 V3 SYSTEM SYNTHETIC TEST
Injects fake data into the Scalper V3 System to verify end-to-end flow.
"""
import sys
import time
import threading
from datetime import datetime

# Path Hack
sys.path.append('.')

import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

from scalper_system.feed import LiquidationStream
from scalper_system.strategy import StrategyEngine
from scalper_system.execution import OrderManager

def run_test():
    print("🧪 STARTING V3 SYNTHETIC TEST")
    
    # 1. Setup Components (Manual Wiring)
    executor = OrderManager(dry_run=True)
    strategy = StrategyEngine(execution_callback=executor.execute)
    
    # note: We don't start the real WS, we just use the class
    # We will invoke the callback manually
    
    # 2. Inject Events
    print("\n--- Injecting $100k LONG Liquidation (Should BUY) ---")
    
    base_price = 96000.0
    
    # Simulate 5 events of $25k each
    for i in range(5):
        event = {
            'timestamp': datetime.now(),
            'symbol': 'BTC',
            'type': 'LONG', # Selling pressure
            'price': base_price - i,
            'size': 0.26, # ~$25k
            'usd': 25000.0,
            'user': '0xFAKE'
        }
        strategy.on_event(event)
        time.sleep(0.1)
        
    print("\n--- Injecting $100k SHORT Liquidation (Should SELL) ---")
    
    # Force reset cooldown for test
    strategy.last_signal_time = datetime.min
    
    for i in range(5):
        event = {
            'timestamp': datetime.now(),
            'symbol': 'BTC',
            'type': 'SHORT', # Buying pressure
            'price': base_price + i,
            'size': 0.26, # ~$25k
            'usd': 25000.0,
            'user': '0xFAKE'
        }
        strategy.on_event(event) # This will print log messages
        time.sleep(0.1)

    print("\n✅ V3 Test Complete")

if __name__ == "__main__":
    run_test()
