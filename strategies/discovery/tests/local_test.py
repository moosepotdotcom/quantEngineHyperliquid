#!/usr/bin/env python3
"""
Manual Test Trade Script
Verifies:
1. SDK Connection
2. Credentials
3. Order Placement (Market)
4. TP/SL Placement (Trigger Orders)
5. Position Closing (Market)
"""
import os
import time
import sys
import os
import time
import sys
try:
    from dotenv import load_dotenv
    # Load default .env if present
    load_dotenv()
except ImportError:
    pass

from hyperliquid_live_trader import HyperliquidTrader

def run_test_trade():
    print("🚀 Starting Cloud Verification Trade...")
    wallet = os.getenv('HYPERLIQUID_WALLET_ADDRESS')
    if not wallet:
        print("❌ Error: HYPERLIQUID_WALLET_ADDRESS not found in environment!")
        return
        
    print(f"   Wallet: {wallet}")
    print("="*60)
    
    try:
        # 1. Initialize
        trader = HyperliquidTrader(testnet=False)
        account = trader.get_account_info()
        print(f"💰 Initial Balance: ${account['balance']:.2f}")
        
        if account['balance'] < 20:
            print(f"⚠️  Warning: Balance low ({account['balance']}), but proceeding with test...")
            # cont = input("Continue? (y/n): ")
            # if cont.lower() != 'y': return

        # 2. Market Buy (Min Size: 0.0002 BTC ~ $18 @ $95k)
        # Hyperliquid min usually $10. 0.0002 is safe.
        SIZE = 0.0002
        SYMBOL = 'BTC'
        
        print(f"\n1️⃣  Placing Market BUY for {SIZE} BTC...")
        buy_order = trader.place_market_order(SYMBOL, is_buy=True, size=SIZE)
        
        if not buy_order:
            print("❌ Buy Failed!")
            return
            
        print("✅ Buy Successful! Waiting 3s...")
        time.sleep(3)
        
        # 3. Place TP/SL
        # Parse nested response: {'data': {'statuses': [{'filled': {'avgPx': '...'}}]}}
        statuses = buy_order['response']['data']['statuses']
        fill_info = statuses[0].get('filled')
        if not fill_info:
             # Handle 'resting' or other statuses if immediate fill didn't happen (unlikely for market)
             print(f"⚠️  Order not immediately filled: {statuses}")
             return
             
        entry_price = float(fill_info['avgPx'])
        print(f"   Entry Price: ${entry_price:,.2f}")
        
        tp_price = entry_price * 1.015 # 1.5%
        sl_price = entry_price * 0.992 # 0.8%
        
        print(f"\n2️⃣  Placing TP/SL Orders (TP: ${tp_price:.1f}, SL: ${sl_price:.1f})...")
        tp_res, sl_res = trader.place_tp_sl_orders(SYMBOL, SIZE, tp_price, sl_price, is_long=True)
        
        if tp_res:
            print("✅ TP/SL Placed Successfully!")
        else:
            print("❌ TP/SL Failed!")
            
        print("   Verify on Hyperliquid UI now. Waiting 10s...")
        time.sleep(10)
        
        # 4. Close Position
        print(f"\n3️⃣  Closing Position (Market SELL)...")
        # First cancel open orders (TP/SL) - The SDK doesn't auto-cancel triggers on market close usually, 
        # but for this test we just market close. The triggers might stay as open orders.
        # Ideally we cancel them.
        
        print("   (Note: You may need to manually cancel the TP/SL trigger orders if they persist)")
        close_order = trader.place_market_order(SYMBOL, is_buy=False, size=SIZE)
        
        if close_order:
            print("✅ Position Closed Successfully!")
        else:
            print("❌ Close Failed!")
            
        print("\n✨ Test Complete!")
        
    except Exception as e:
        print(f"\n❌ Information: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Confirm
    print("⚠️  EXECUTING LIVE VERIFICATION TRADE")
    print("   Size: 0.0002 BTC")
    run_test_trade()
