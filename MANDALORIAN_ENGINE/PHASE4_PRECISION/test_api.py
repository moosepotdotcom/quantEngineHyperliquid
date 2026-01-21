#!/usr/bin/env python3
"""
Test Hyperliquid API endpoints individually
"""

import requests
import json

base_url = "https://api.hyperliquid.xyz/info"

print("="*60)
print("🔍 Testing Hyperliquid API Endpoints")
print("="*60)

# Test 1: Meta and Asset Contexts (Funding, OI)
print("\n1️⃣ Testing metaAndAssetCtxs...")
payload = {"type": "metaAndAssetCtxs"}
try:
    response = requests.post(base_url, json=payload, timeout=10)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Success! Got {len(data)} items")
        if len(data) > 1:
            # Show BTC data
            for asset in data[1][:3]:  # Show first 3 assets
                print(f"      Asset: {asset.get('name', 'N/A')}")
                print(f"      Funding: {asset.get('funding', 'N/A')}")
                print(f"      OI: {asset.get('openInterest', 'N/A')}")
                print()
    else:
        print(f"   ❌ Error: {response.text}")
except Exception as e:
    print(f"   ❌ Exception: {e}")

# Test 2: L2 Order Book
print("\n2️⃣ Testing l2Book...")
payload = {"type": "l2Book", "coin": "BTC"}
try:
    response = requests.post(base_url, json=payload, timeout=10)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Success!")
        if 'levels' in data:
            print(f"      Levels: {len(data['levels'])}")
            # Show top 3 bids and asks
            bids = [l for l in data['levels'][:10] if l.get('n') == 1]
            asks = [l for l in data['levels'][:10] if l.get('n') == 0]
            print(f"      Top bid: {bids[0] if bids else 'N/A'}")
            print(f"      Top ask: {asks[0] if asks else 'N/A'}")
    else:
        print(f"   ❌ Error: {response.text}")
except Exception as e:
    print(f"   ❌ Exception: {e}")

# Test 3: Funding History
print("\n3️⃣ Testing fundingHistory...")
payload = {"type": "fundingHistory", "coin": "BTC"}
try:
    response = requests.post(base_url, json=payload, timeout=10)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Success! Got {len(data)} funding updates")
        if len(data) > 0:
            print(f"      Latest: {data[-1]}")
    else:
        print(f"   ❌ Error: {response.text}")
except Exception as e:
    print(f"   ❌ Exception: {e}")

# Test 4: User Fills (for liquidations)
print("\n4️⃣ Testing userFills (liquidations)...")
# Note: This might need a specific user address
payload = {"type": "userFills", "user": "0x0000000000000000000000000000000000000000"}
try:
    response = requests.post(base_url, json=payload, timeout=10)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Success! Got {len(data)} fills")
    else:
        print(f"   ❌ Error: {response.text}")
except Exception as e:
    print(f"   ❌ Exception: {e}")

# Test 5: All Mids (current prices)
print("\n5️⃣ Testing allMids...")
payload = {"type": "allMids"}
try:
    response = requests.post(base_url, json=payload, timeout=10)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Success!")
        if 'BTC' in data:
            print(f"      BTC price: ${data['BTC']}")
    else:
        print(f"   ❌ Error: {response.text}")
except Exception as e:
    print(f"   ❌ Exception: {e}")

print("\n" + "="*60)
print("✅ API Test Complete!")
print("="*60)
