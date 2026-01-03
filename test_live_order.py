#!/usr/bin/env python3
"""
Test script to place a small order and immediately close it
This verifies the real API integration is working
"""

import time
from hyperliquid_live_trader import HyperliquidTrader

print("🧪 Testing Live Trading - Quick Order Test")
print("=" * 70)

# Initialize trader (mainnet)
trader = HyperliquidTrader(testnet=False)

# Get current account info
print("\n📊 Checking account...")
account = trader.get_account_info()
print(f"Balance: ${account['balance']:.2f}")

if account['balance'] < 1:
    print("❌ Insufficient balance for test")
    exit(1)

# Get current BTC price
import requests
response = requests.post(
    "https://api.hyperliquid.xyz/info",
    json={
        "type": "candleSnapshot",
        "req": {
            "coin": "BTC",
            "interval": "1h",
            "startTime": 0,
            "endTime": 9999999999999
        }
    },
    timeout=10
)

if response.status_code == 200:
    data = response.json()
    current_price = float(data[-1]['c'])
    print(f"Current BTC: ${current_price:,.2f}")
else:
    print("❌ Failed to get BTC price")
    exit(1)

# Place a tiny test order (0.001 BTC - very small!)
print("\n🧪 Placing TEST order (0.001 BTC)...")
print("This is a REAL order with REAL money!")

test_size = 0.001  # Very small test

order = trader.place_market_order(
    symbol='BTC',
    is_buy=True,
    size=test_size
)

if order:
    print(f"✅ TEST ORDER PLACED!")
    print(f"   Size: {test_size} BTC")
    print(f"   Value: ~${test_size * current_price:.2f}")
    
    # Wait a moment
    print("\n⏳ Waiting 3 seconds...")
    time.sleep(3)
    
    # Immediately close the position
    print("\n🔄 Closing test position...")
    close_order = trader.place_market_order(
        symbol='BTC',
        is_buy=False,
        size=test_size
    )
    
    if close_order:
        print(f"✅ TEST POSITION CLOSED!")
        print("\n" + "=" * 70)
        print("🎉 SUCCESS! Live trading is working!")
        print("=" * 70)
        print("\nYour bot can now execute real trades!")
        print("Check Hyperliquid to see the test orders.")
    else:
        print("❌ Failed to close position")
        print("⚠️  You may need to manually close on Hyperliquid")
else:
    print("❌ Test order failed")
    print("Check the error messages above")

# Check final balance
print("\n📊 Final account check...")
time.sleep(2)
account = trader.get_account_info()
print(f"Balance: ${account['balance']:.2f}")
