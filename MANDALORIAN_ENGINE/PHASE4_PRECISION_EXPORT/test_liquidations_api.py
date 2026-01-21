#!/usr/bin/env python3
"""
Test Hyperliquid Liquidation API
"""

import requests
import json
from datetime import datetime, timedelta

base_url = "https://api.hyperliquid.xyz/info"

print("="*60)
print("🔥 Testing Hyperliquid Liquidation API")
print("="*60)

# Test 1: Try to get recent fills (liquidations might be here)
print("\n1️⃣ Testing userFills endpoint...")
print("   Note: Liquidations might be under a special address")

# Try the zero address (common for system events)
test_addresses = [
    "0x0000000000000000000000000000000000000000",
    "0x000000000000000000000000000000000000dead",
]

for addr in test_addresses:
    print(f"\n   Trying address: {addr[:10]}...")
    payload = {"type": "userFills", "user": addr}
    
    try:
        response = requests.post(base_url, json=payload, timeout=5)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Response type: {type(data)}")
            print(f"   Length: {len(data) if isinstance(data, list) else 'N/A'}")
            
            if isinstance(data, list) and len(data) > 0:
                print(f"   ✅ Got {len(data)} fills!")
                print(f"   Sample: {json.dumps(data[0], indent=2)[:500]}")
                break
            else:
                print(f"   Empty or wrong format")
        else:
            print(f"   Error: {response.text[:200]}")
    except Exception as e:
        print(f"   Exception: {e}")

# Test 2: Try clearinghouseState
print("\n\n2️⃣ Testing clearinghouseState endpoint...")
payload = {"type": "clearinghouseState", "user": "0x0000000000000000000000000000000000000000"}

try:
    response = requests.post(base_url, json=payload, timeout=5)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Success!")
        print(f"   Keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
        print(f"   Sample: {json.dumps(data, indent=2)[:500]}")
    else:
        print(f"   Error: {response.text[:200]}")
except Exception as e:
    print(f"   Exception: {e}")

# Test 3: Check if there's a liquidations endpoint
print("\n\n3️⃣ Testing potential liquidations endpoints...")

test_types = [
    "liquidations",
    "recentLiquidations", 
    "liquidationHistory",
    "allLiquidations"
]

for test_type in test_types:
    print(f"\n   Trying type: {test_type}...")
    payload = {"type": test_type}
    
    try:
        response = requests.post(base_url, json=payload, timeout=5)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ SUCCESS! This endpoint works!")
            print(f"   Response: {json.dumps(data, indent=2)[:500]}")
            break
        elif response.status_code == 422:
            print(f"   ❌ Invalid type")
        else:
            print(f"   Error: {response.text[:100]}")
    except Exception as e:
        print(f"   Exception: {e}")

print("\n" + "="*60)
print("🔍 Liquidation API Investigation Complete")
print("="*60)
print("\nNote: Hyperliquid may not expose public liquidation data")
print("Alternative: Use price action to infer liquidation zones")
print("="*60)
