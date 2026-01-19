#!/usr/bin/env python3
"""
Debug API response formats
"""

import requests
import json

base_url = "https://api.hyperliquid.xyz/info"

# Test l2Book to see actual format
print("Testing l2Book response format...")
payload = {"type": "l2Book", "coin": "BTC"}
response = requests.post(base_url, json=payload, timeout=5)

if response.status_code == 200:
    data = response.json()
    print("\nFull response:")
    print(json.dumps(data, indent=2)[:1000])  # First 1000 chars
else:
    print(f"Error: {response.text}")
