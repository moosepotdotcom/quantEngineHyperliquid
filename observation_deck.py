#!/usr/bin/env python3
"""
🔭 OBSERVATION DECK
Monitors the high-frequency/low-threshold Scalper V3 System.
"""
from scalper_system import config
import time
import os
import re

LOG_FILE = config.LIVE_LOG_FILE

def main():
    print(f"🔭 OBSERVATION DECK - Tracking >${config.LIQ_THRESHOLD_USD} Liquidations")
    print("="*60)
    
    signals = []
    liquidations = 0
    last_heartbeat = time.time()
    
    # Simple tail-f implementation
    with open(LOG_FILE, 'r') as f:
        # Go to end
        f.seek(0, 2)
        
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1)
                continue
                
            line = line.strip()
            
            # Count Liquidations
            if "Liq:" in line:
                liquidations += 1
                # Format: 2026... - INFO - 💦 LONG Liq: $25,000 @ 96000
                print(f"💦 {line.split(' - ')[-1]}")
                last_heartbeat = time.time()
                
            # Capture Signals
            if "SIGNAL:" in line:
                signals.append(line)
                print(f"\n🚀 {line.split(' - ')[-1]}\n")
                last_heartbeat = time.time()
                
            # Heartbeat (every 60s)
            if time.time() - last_heartbeat > 60:
                print(f"   (Waiting for Liquidations... {time.strftime('%H:%M:%S')})")
                last_heartbeat = time.time()
                
            # Periodic Summary (every 50 events or so, or keep it streaming)

if __name__ == "__main__":
    if not os.path.exists(LOG_FILE):
        print(f"Waiting for {LOG_FILE}...")
        while not os.path.exists(LOG_FILE):
            time.sleep(1)
            
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Exiting Observation Deck")
