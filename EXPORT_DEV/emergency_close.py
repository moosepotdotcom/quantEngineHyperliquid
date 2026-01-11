import sys
import os
import time
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hyperliquid_live_trader import HyperliquidTrader

def emergency_close():
    print("\n🚨 EMERGENCY CLOSE ALL POSITIONS 🚨")
    print("========================================")
    
    try:
        # Connect to MAINNET (since drill was mainnet)
        trader = HyperliquidTrader(testnet=False)
        print("✅ Trader Connected")
        
        info = trader.get_account_info()
        positions = info.get('positions', [])
        
        print(f"📊 Found {len(positions)} raw position entries")
        
        closed_count = 0
        
        for p in positions:
            # Handle nested position structure if needed
            # Hyperliquid API return: {'position': {'coin': 'BTC', 'szi': '1.0', ...}}
            pos_data = p.get('position', p) 
            coin = pos_data.get('coin', 'Unknown')
            size_str = pos_data.get('szi', '0')
            size = float(size_str)
            
            if size != 0:
                print(f"   🔻 OPEN: {coin} Size: {size}")
                
                # Determine side to close
                # If size > 0 (Long), we Sell (is_buy=False)
                # If size < 0 (Short), we Buy (is_buy=True)
                is_buy_to_close = (size < 0)
                abs_size = abs(size)
                
                print(f"      Closing {coin}...")
                trader.exchange.market_open(
                    name=coin,
                    is_buy=is_buy_to_close,
                    sz=abs_size,
                    px=None
                )
                print(f"      ✅ Closed {coin}")
                closed_count += 1
                
        if closed_count == 0:
            print("✅ No open positions found.")
        else:
            print(f"✅ Closed {closed_count} positions.")

        print("🧹 Cancelling all open orders (TP/SL)...")
        trader.exchange.cancel_all_orders()
        print("✅ Orders Cancelled.")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    emergency_close()
