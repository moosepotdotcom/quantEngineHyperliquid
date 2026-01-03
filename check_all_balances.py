#!/usr/bin/env python3
"""
Check USDC balance and spot balances on Hyperliquid
"""

import requests
import json

WALLET_ADDRESS = "0xc692111d70b42e32e7b87abdd7dae7900b6cdde1"
API_URL = "https://api.hyperliquid.xyz"

print("🔍 Checking All Balances on Hyperliquid")
print("=" * 70)

# Check spot balances (USDC)
print("\n📊 Checking Spot Balances (USDC)...")
try:
    response = requests.post(
        f"{API_URL}/info",
        json={
            "type": "spotClearinghouseState",
            "user": WALLET_ADDRESS
        },
        timeout=10
    )
    
    if response.status_code == 200:
        data = response.json()
        balances = data.get('balances', [])
        
        print(f"\n💰 Spot Balances:")
        if balances:
            for balance in balances:
                coin = balance.get('coin', 'Unknown')
                total = float(balance.get('total', 0))
                hold = float(balance.get('hold', 0))
                available = total - hold
                
                print(f"   {coin}:")
                print(f"      Total: ${total:,.2f}")
                print(f"      Hold: ${hold:,.2f}")
                print(f"      Available: ${available:,.2f}")
        else:
            print("   No spot balances found")
            
        print(f"\n📋 Full Spot Response:")
        print(json.dumps(data, indent=2))
    else:
        print(f"Error: {response.status_code}")
        
except Exception as e:
    print(f"Error: {e}")

# Check perp balances
print("\n\n📊 Checking Perpetual Margin...")
try:
    response = requests.post(
        f"{API_URL}/info",
        json={
            "type": "clearinghouseState",
            "user": WALLET_ADDRESS
        },
        timeout=10
    )
    
    if response.status_code == 200:
        data = response.json()
        margin = data.get('marginSummary', {})
        
        print(f"\n💰 Perpetual Margin:")
        print(f"   Account Value: ${float(margin.get('accountValue', 0)):,.2f}")
        print(f"   Available: ${float(margin.get('totalRawUsd', 0)):,.2f}")
        
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 70)
print("✅ Balance check complete!")
print("=" * 70)
