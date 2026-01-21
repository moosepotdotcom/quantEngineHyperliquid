#!/usr/bin/env python3
"""
📊 LIVE MONITORING DASHBOARD
"""
import time
import os
import pandas as pd
from datetime import datetime

CSV_FILE = "data/live_liquidations_session.csv"
SCALPER_LOG = "logs/scalper.log"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_file_stats(filepath):
    if not os.path.exists(filepath):
        return 0, datetime.min
    
    stat = os.stat(filepath)
    mod_time = datetime.fromtimestamp(stat.st_mtime)
    size = stat.st_size
    return size, mod_time

def main():
    print("📊 Starting Dashboard...")
    
    while True:
        clear_screen()
        print(f"🌊 HYPERLIQUID SCALPER MONITOR | {datetime.now().strftime('%H:%M:%S')}")
        print("="*60)
        
        # 1. Collector Stats
        if os.path.exists(CSV_FILE):
            try:
                df = pd.read_csv(CSV_FILE)
                last_time = df['timestamp'].iloc[-1] if not df.empty else "N/A"
                print(f"📥 COLLECTOR:")
                print(f"   Events Captured: {len(df)}")
                print(f"   Last Event:      {last_time}")
                print(f"   File Size:       {os.path.getsize(CSV_FILE)} bytes")
                
                if not df.empty:
                    last_5 = df.tail(5)
                    print(f"\n   Recent Liquidations:")
                    for _, row in last_5.iterrows():
                        side = "🟢 SHORT" if row['side'] == 'B' else "🔴 LONG"
                        print(f"   {row['timestamp'][11:19]} | {side} | ${row['price']:,.1f} | ${row['usd_value']:,.0f}")
            except Exception as e:
                print(f"   Error reading CSV: {e}")
        else:
            print("📥 COLLECTOR: Waiting for file...")
            
        print("-" * 60)
        
        # 2. Scalper Stats
        if os.path.exists(SCALPER_LOG):
            print(f"🤖 SCALPER LOG (Tail):")
            try:
                # Read last 5 lines
                with open(SCALPER_LOG, 'r') as f:
                    lines = f.readlines()[-5:]
                    for line in lines:
                        print(f"   {line.strip()}")
            except:
                pass
        else:
             print("🤖 SCALPER: Log not found")
             
        print("-" * 60)
        print("Ctrl+C to Exit Monitor (Processes continue in background)")
        time.sleep(2)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
