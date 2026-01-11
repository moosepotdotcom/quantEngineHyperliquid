import sys
import os
import time
import pandas as pd
from datetime import datetime

# Import from local directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quant_engine import TradingEngine

def live_dry_run():
    print("\n🧪 LIVE DRY RUN: EXPORT_DEV SANDBOX")
    print("   Target: Hyperliquid API (Live Stream)")
    print("   Mode:   Read-Only (No Orders)")
    print("="*60)
    
    try:
        engine = TradingEngine()
        print("✅ Engine Initialized Successfully")
    except Exception as e:
        print(f"❌ Engine Init Failed: {e}")
        return

    print("\n📡 STARTING DATA STREAM...")
    print("-" * 60)
    
    try:
        while True:
            start_time = time.time()
            now_str = datetime.now().strftime("%H:%M:%S")
            
            print(f"\n[{now_str}] 📥 Polling 5m/15m/1h Data...")
            
            # This calls fetch_data() internally -> HITS API
            try:
                signal, confidence = engine.check_mtf_scalper()
                
                # Fetch latest price just for display (from engine's last fetch if possible, or just ignore)
                # We can't easily get the price from inside check_mtf_scalper unless it returns a signal.
                # But check_mtf_scalper logic prints logs too.
                
                if signal:
                    dir_str = signal['direction']
                    price = signal['price']
                    conf_str = f"{confidence:.4f}"
                    print(f"   🚀 [SIMULATED SIGNAL] {dir_str} @ {price} | Conf: {conf_str}")
                    print("       (In a live run, this would execute an order)")
                else:
                    print(f"   💤 [WAIT] Confidence: {confidence:.4f} (Threshold: 0.4500)")
                    
            except Exception as e:
                print(f"   ⚠️  Cycle Error: {e}")
                import traceback
                traceback.print_exc()
            
            # Wait for next cycle
            # 5m candles update often, but no need to spam API too hard in dry run
            sleep_sec = 15
            print(f"   ⏳ Waiting {sleep_sec}s...")
            time.sleep(sleep_sec)
            
    except KeyboardInterrupt:
        print("\n🛑 Dry Run Stopped by User")

if __name__ == "__main__":
    live_dry_run()
