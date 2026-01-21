
import os
import sys
import time
import pandas as pd
from datetime import datetime
from logic import MTFScalperV4Logic

# Add project utils
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from utils.fetch_data import fetch_live_data
from utils.feature_engineer import add_all_indicators

def run_backup_engine():
    print("🚀 Starting V4 Independent Backup Engine...")
    
    logic = MTFScalperV4Logic()
    
    # Simple Loop
    while True:
        try:
            print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} | Checking Markets...")
            
            # Fetch Data
            def get_data(tf, limit=500):
                df = fetch_live_data("BTC", tf, limit=limit)
                if df is not None:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
                    df = add_all_indicators(df)
                    return df.sort_values('timestamp').reset_index(drop=True)
                return None
            
            df_5m = get_data('5m')
            df_15m = get_data('15m')
            df_30m = get_data('30m')
            
            if df_5m is not None and df_15m is not None and df_30m is not None:
                signal = logic.analyze(df_5m, df_15m, df_30m)
                
                if signal:
                    print("\n" + "="*60)
                    print(f"🎉 V4 SIGNAL DETECTED!")
                    print(f"   Direction: {signal['direction']}")
                    print(f"   Price: ${signal['price']}")
                    print(f"   Confidence: {signal['confidence']:.4f}")
                    print("="*60 + "\n")
                else:
                    print("   ... No signal.")
            else:
                print("   ⚠️ Data fetch failed.")
                
            time.sleep(60)
            
        except KeyboardInterrupt:
            print("\n🛑 Stopping Backup Engine.")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_backup_engine()
