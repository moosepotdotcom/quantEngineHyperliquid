"""
🧪 SYNTHETIC DATA GENERATOR
Creates a sample CSV to verify the Backcaster tool.
"""
import csv
import random
from datetime import datetime, timedelta
from scalper_system import config

FILE = "data/liquidations_synthetic.csv"

def generate():
    print(f"Generating {FILE}...")
    
    start_time = datetime.now() - timedelta(hours=1)
    base_price = 95000.0
    
    with open(FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'symbol', 'type', 'price', 'size', 'usd', 'user'])
        
        # 1. Quiet Period
        for i in range(30):
            t = start_time + timedelta(minutes=i)
            writer.writerow([t.isoformat(), 'BTC', 'SHORT', base_price, 0.01, 1000, '0xUser'])
            
        # 2. Massive Long Cascade (Should trigger BUY)
        cascade_time = start_time + timedelta(minutes=35)
        for i in range(10):
            t = cascade_time + timedelta(seconds=i)
            writer.writerow([t.isoformat(), 'BTC', 'LONG', base_price-i, 1.0, 95000, '0xWhale'])
            
        # 3. Recovery
        
        # 4. Massive Short Cascade (Should trigger SELL)
        cascade_time2 = start_time + timedelta(minutes=50)
        for i in range(10):
            t = cascade_time2 + timedelta(seconds=i)
            writer.writerow([t.isoformat(), 'BTC', 'SHORT', base_price+i, 1.0, 95000, '0xWhale'])
            
    print("✅ Done.")

if __name__ == "__main__":
    generate()
