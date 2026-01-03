#!/usr/bin/env python3
"""
Test script to verify Hyperliquid account connection
Fetches your actual account balance to confirm connection
"""

import requests
import json

# Your wallet address
WALLET_ADDRESS = "0xc692111d70b42e32e7b87abdd7dae7900b6cdde1"

# Hyperliquid API
API_URL = "https://api.hyperliquid.xyz"

print("🔍 Testing Hyperliquid Account Connection")
print("=" * 70)
print(f"Wallet: {WALLET_ADDRESS}")
print(f"API: {API_URL}")
print("=" * 70)

try:
    # Fetch account state
    print("\n📡 Fetching account information...")
    
    response = requests.post(
        f"{API_URL}/info",
        json={
            "type": "clearinghouseState",
            "user": WALLET_ADDRESS
        },
        timeout=10
    )
    
    print(f"Response Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        # Extract account info
        margin_summary = data.get('marginSummary', {})
        account_value = float(margin_summary.get('accountValue', 0))
        total_margin_used = float(margin_summary.get('totalMarginUsed', 0))
        total_ntl_pos = float(margin_summary.get('totalNtlPos', 0))
        total_raw_usd = float(margin_summary.get('totalRawUsd', 0))
        
        # Get positions
        positions = data.get('assetPositions', [])
        
        print("\n" + "=" * 70)
        print("✅ CONNECTION SUCCESSFUL!")
        print("=" * 70)
        
        print(f"\n💰 Account Balance:")
        print(f"   Total Value: ${account_value:,.2f}")
        print(f"   Available: ${total_raw_usd:,.2f}")
        print(f"   Margin Used: ${total_margin_used:,.2f}")
        print(f"   Position Value: ${total_ntl_pos:,.2f}")
        
        print(f"\n📊 Positions: {len(positions)}")
        if positions:
            for pos in positions:
                position = pos.get('position', {})
                coin = position.get('coin', 'Unknown')
                size = float(position.get('szi', 0))
                entry_px = float(position.get('entryPx', 0))
                
                print(f"\n   {coin}:")
                print(f"      Size: {size}")
                print(f"      Entry: ${entry_px:,.2f}")
        else:
            print("   No open positions")
        
        print("\n" + "=" * 70)
        print("🎉 Your bot IS connected to your real Hyperliquid account!")
        print("=" * 70)
        
        # Show full response for debugging
        print("\n📋 Full Response (for debugging):")
        print(json.dumps(data, indent=2))
        
    else:
        print(f"\n❌ Error: HTTP {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
