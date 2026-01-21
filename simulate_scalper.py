#!/usr/bin/env python3
"""
🔄 SCALPER SIMULATOR
Replays 'live_liquidations_session.csv' to test strategy parameters.
"""

import pandas as pd
from datetime import datetime
import time
from scalper_v2 import LiquidationEngine # Import logic from main bot

DATA_FILE = "data/live_liquidations_session.csv"

class SimulationEngine(LiquidationEngine):
    def __init__(self):
        super().__init__(dry_run=True)
        self.trades_simulated = []
        
    def execute(self, signal):
        print(f"   [SIM] Executed {signal['direction']} @ {signal['price']} | Conf: {signal['confidence']:.2f}")
        self.trades_simulated.append(signal)

def run_simulation():
    try:
        df = pd.read_csv(DATA_FILE)
        if df.empty:
            print("⚠️ No data in CSV yet. Waiting for liquidations...")
            return
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return

    print(f"📊 Replaying {len(df)} events...")
    sim = SimulationEngine()
    
    # We need to simulate time passing for the window cleanup
    # This is a simplified replay that just aggressively feeds data
    
    start_time = df['timestamp'].iloc[0]
    end_time = df['timestamp'].iloc[-1]
    duration = (end_time - start_time).total_seconds() / 60
    print(f"   Time span: {duration:.1f} minutes")
    
    for i, row in df.iterrows():
        # Construct trade object compatible with LiquidationEngine
        # We need to reconstruct the 'trade' dict structure
        trade = {
            'px': str(row['price']),
            'sz': str(row['size']),
            'side': row['side'],
            # We add a fake liquidtion marker/field since the collector only saves confirmed liqs
            'liquidation': True 
        }
        
        # We also need to mock datetime.now() logic in the engine if we want perfect accuracy,
        # but for V1 let's just push it through. 
        # Ideally, we should override process_liquidation to accept a timestamp, 
        # or mock datetime.now.
        
        # For this quick verification, we will just print what WOULD trigger 
        # if the events happened *now* in rapid succession (burst test).
        # A proper backtest needs the `backtest_scalping.py` time-step logic.
        
        sim.process_liquidation(trade)
        
    print(f"\n✅ Simulation Complete. Signals Triggered: {len(sim.trades_simulated)}")

if __name__ == "__main__":
    run_simulation()
