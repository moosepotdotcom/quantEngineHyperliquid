#!/usr/bin/env python3
"""
Simple Live Trade Test using HyperliquidTrader
"""
import os
import sys

# Load environment - handle both HYPERLIQUID_PRIVATE_KEY and HYPERLIQUID_API_SECRET
env_file = '.env.live_trading'
if os.path.exists(env_file):
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                # Strip inline comments
                value = value.split('#')[0].strip().strip('"').strip("'")
                os.environ[key] = value
                # Also set API_SECRET if PRIVATE_KEY is found
                if key == 'HYPERLIQUID_PRIVATE_KEY':
                    os.environ['HYPERLIQUID_API_SECRET'] = value

from hyperliquid_live_trader import HyperliquidTrader

print("="*70)
print("🧪 LIVE TRADE TEST - Using HyperliquidTrader")
print("="*70)

try:
    # Initialize trader (testnet=False for mainnet)
    trader = HyperliquidTrader(testnet=False)
    
    # Get account info
    account = trader.get_account_info()
    print(f"\n💰 Account Balance: ${account['balance']:,.2f}")
    
    if account['balance'] < 10:
        print(f"❌ Insufficient funds for test (need $10, have ${account['balance']:.2f})")
        sys.exit(1)
    
    # Get current BTC price using Info API
    from hyperliquid.info import Info
    info = Info("https://api.hyperliquid.xyz", skip_ws=True)
    all_mids = info.all_mids()
    price = float(all_mids.get('BTC', 0))
    
    print(f"📊 Current BTC Price: ${price:,.2f}")
    
    # Calculate position size for $10 test
    test_size_usd = 10
    position_size = test_size_usd / price
    position_size = round(position_size, 5)  # 5 decimals for BTC
    
    print(f"\n🎯 Test Trade Parameters:")
    print(f"   Size: {position_size} BTC (${test_size_usd})")
    print(f"   Entry: ${price:,.2f}")
    print(f"   TP: ${price * 1.015:,.2f} (+1.5%)")
    print(f"   SL: ${price * 0.992:,.2f} (-0.8%)")
    
    response = input("\n⚠️  Proceed with REAL trade? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Test cancelled")
        sys.exit(0)
    
    # Place market order
    print(f"\n📤 Placing LONG market order...")
    result = trader.place_market_order('BTC', True, position_size)
    
    if result:
        print(f"✅ Order placed successfully!")
        print(f"   Result: {result}")
        
        # Wait a moment
        import time
        time.sleep(3)
        
        # Close position
        cleanup = input("\nClose position now? (yes/no): ")
        if cleanup.lower() == 'yes':
            print(f"\n📤 Closing position...")
            close_result = trader.place_market_order('BTC', False, position_size)
            if close_result:
                print(f"✅ Position closed!")
            else:
                print(f"⚠️  Failed to close - please close manually")
    else:
        print(f"❌ Order failed")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("✅ Test complete")
print("="*70)
