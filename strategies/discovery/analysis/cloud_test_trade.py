#!/usr/bin/env python3
"""
Cloud test endpoint - trigger a test trade from Cloud Run
"""

import os
import sys

# Set environment variables
os.environ['HYPERLIQUID_WALLET_ADDRESS'] = '0xb01713a6fcdc9419f37db065f0274ea172e4689e'
os.environ['HYPERLIQUID_API_SECRET'] = os.getenv('HYPERLIQUID_API_SECRET', '')
os.environ['MAX_POSITION_SIZE'] = '0.001'

from hyperliquid_live_trader import HyperliquidTrader
import time

print("🧪 CLOUD TEST - Executing from Cloud Run")
print("=" * 70)

try:
    # Initialize trader
    trader = HyperliquidTrader(testnet=False)
    
    # Check balance
    account = trader.get_account_info()
    print(f"\n💰 Balance: ${account['balance']:.2f}")
    
    if account['balance'] < 1:
        print("❌ Insufficient balance")
        sys.exit(1)
    
    # Execute test trade
    print("\n🧪 Executing test trade (0.001 BTC)...")
    
    # BUY
    buy_order = trader.place_market_order('BTC', True, 0.001)
    
    if buy_order:
        print("✅ BUY order executed!")
        
        # Wait
        print("\n⏳ Waiting 3 seconds...")
        time.sleep(3)
        
        # SELL
        print("\n🔄 Closing position...")
        sell_order = trader.place_market_order('BTC', False, 0.001)
        
        if sell_order:
            print("\n" + "=" * 70)
            print("🎉 CLOUD TEST SUCCESSFUL!")
            print("=" * 70)
            print("\nBoth orders executed from Cloud Run!")
            print("✅ Live trading is working from the cloud!")
        else:
            print("⚠️  Sell order failed")
            sys.exit(1)
    else:
        print("❌ Buy order failed")
        sys.exit(1)
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
