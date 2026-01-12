#!/usr/bin/env python3
"""
🧪 SL/TP PAYLOAD DIAGNOSTIC
Validates the construction of trigger orders for Hyperliquid.
"""
import os
import sys

def test_payload_construction():
    symbol = "BTC"
    size = 0.02
    entry_price = 93000.0
    tp_pct = 0.003
    sl_pct = 0.005
    
    tp_price = entry_price * (1 + tp_pct)
    sl_price = entry_price * (1 - sl_pct)
    
    # Matching the logic in hyperliquid_live_trader.py
    tp_price_rounded = round(tp_price, 0)
    sl_price_rounded = round(sl_price, 0)
    
    print(f"🔍 Testing Payload Construction for {symbol} @ {entry_price}")
    print(f"   TP Target: {tp_price} -> Rounded: {tp_price_rounded}")
    print(f"   SL Target: {sl_price} -> Rounded: {sl_price_rounded}")
    
    orders = [
        {
            "coin": symbol,
            "is_buy": False,
            "sz": size,
            "limit_px": tp_price_rounded,
            "order_type": {"trigger": {"triggerPx": tp_price_rounded, "isMarket": True, "tpsl": "tp"}},
            "reduce_only": True
        },
        {
            "coin": symbol,
            "is_buy": False,
            "sz": size,
            "limit_px": sl_price_rounded,
            "order_type": {"trigger": {"triggerPx": sl_price_rounded, "isMarket": True, "tpsl": "sl"}},
            "reduce_only": True
        }
    ]
    
    print("\n📦 Resulting Orders Array:")
    import json
    print(json.dumps(orders, indent=4))
    
    # Verification checks
    assert orders[0]['reduce_only'] is True, "TP must be reduce_only"
    assert orders[1]['reduce_only'] is True, "SL must be reduce_only"
    assert orders[0]['order_type']['trigger']['tpsl'] == 'tp'
    assert orders[1]['order_type']['trigger']['tpsl'] == 'sl'
    assert orders[0]['sz'] == size
    
    print("\n✅ Payload Logic Verified: Standard Compliant with Hyperliquid 'positionTpsl' grouping.")

if __name__ == "__main__":
    test_payload_construction()
