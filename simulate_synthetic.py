#!/usr/bin/env python3
"""
🧪 SYNTHETIC SIMULATOR
Generates FAKE liquidation cascades to verify Scalper V2 logic.
"""

from scalper_v2 import LiquidationEngine
from datetime import datetime
import time

def run_synthetic_test():
    print("🧪 Starting SYNTHETIC Test...")
    engine = LiquidationEngine(dry_run=True)
    
    # Scene 1: Quiet Market
    print("\n--- Scene 1: Quiet Market ---")
    base_price = 95000.0
    for i in range(5):
        trade = {
            'px': str(base_price + i),
            'sz': '0.01',
            'side': 'B', # Short Liq
            'liquidation': True
        }
        engine.process_liquidation(trade)
    
    # Scene 2: Massive LONG Liquidation Cascade (Should trigger BUY)
    print("\n--- Scene 2: 🔴 Massive Long Liquidation Cascade ---")
    print("   Injecting $100k Long Liquidations...")
    
    # Inject 5 large events
    for i in range(5):
        trade = {
            'px': str(base_price - (i*10)), # Price dropping
            'sz': '0.25', # ~$23k each
            'side': 'A', # Long Liq (Selling)
            'liquidation': True
        }
        engine.process_liquidation(trade)
        
    print("\n   [Expected: SIGNAL GENERATED: LONG]")
    
    # Clear state (simulate time passing)
    engine.short_liqs.clear()
    engine.long_liqs.clear()
    engine.last_signal_time = datetime.min
    
    # Scene 3: Massive SHORT Liquidation Cascade (Should trigger SELL)
    print("\n--- Scene 3: 🟢 Massive Short Liquidation Cascade ---")
    print("   Injecting $100k Short Liquidations...")
    
    for i in range(5):
        trade = {
            'px': str(base_price + (i*10)), # Price rising
            'sz': '0.25', # ~$23k each
            'side': 'B', # Short Liq (Buying)
            'liquidation': True
        }
        engine.process_liquidation(trade)

    print("\n   [Expected: SIGNAL GENERATED: SHORT]")
    print("\n✅ Synthetic Test Complete")

if __name__ == "__main__":
    run_synthetic_test()
