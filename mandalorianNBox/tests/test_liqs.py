
import time
from data.liquidation_monitor import LiquidationMonitor

print("🧪 Testing Liquidation Monitor...")
mon = LiquidationMonitor(threshold_usd=1000) # Low threshold to see events fast
mon.start()

try:
    for i in range(10):
        if mon.latest_liquidation:
            print(f"🔥 CAUGHT ONE: {mon.latest_liquidation}")
            mon.latest_liquidation = None # Reset to see new ones
        time.sleep(1)
        print(f"Tick {i}...", end='\r')
except KeyboardInterrupt:
    pass
    
print("\nStopping...")
mon.stop()
mon.join()
print("Test Complete.")
