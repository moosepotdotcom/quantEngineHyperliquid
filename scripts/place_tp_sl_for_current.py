#!/usr/bin/env python3
"""
Place TP/SL orders for current open position
"""

import os
os.environ['HYPERLIQUID_WALLET_ADDRESS'] = '0xb01713a6fcdc9419f37db065f0274ea172e4689e'
os.environ['HYPERLIQUID_API_SECRET'] = os.getenv('HYPERLIQUID_API_SECRET', 'f06f4fd2a7516373cc4c8e99afd8c7445b4db0735de0fbe860cfa2b343bfc086')

from hyperliquid_live_trader import HyperliquidTrader

print("📋 Placing TP/SL Orders for Current Position")
print("=" * 70)

# Initialize trader
trader = HyperliquidTrader(testnet=False)

# Get current position
account = trader.get_account_info()
positions = account.get('positions', [])

if not positions:
    print("❌ No open positions found")
    exit(1)

# Get position details
position = positions[0].get('position', {})
size = abs(float(position.get('szi', 0)))
entry_px = float(position.get('entryPx', 0))

print(f"\n📊 Current Position:")
print(f"   Size: {size} BTC")
print(f"   Entry: ${entry_px:,.2f}")

# Calculate TP and SL
tp_price = entry_px * 1.015  # +1.5%
sl_price = entry_px * 0.992  # -0.8%

print(f"\n🎯 Calculated TP/SL:")
print(f"   TP: ${tp_price:,.2f} (+1.5%)")
print(f"   SL: ${sl_price:,.2f} (-0.8%)")

# Place orders
tp_order, sl_order = trader.place_tp_sl_orders('BTC', size, tp_price, sl_price)

if tp_order and sl_order:
    print("\n" + "=" * 70)
    print("✅ TP/SL Orders Placed Successfully!")
    print("=" * 70)
    print("\nYour position now has automatic TP/SL orders on Hyperliquid!")
    print("They will execute even if the bot goes offline.")
else:
    print("\n⚠️  Some orders may have failed - check Hyperliquid")
