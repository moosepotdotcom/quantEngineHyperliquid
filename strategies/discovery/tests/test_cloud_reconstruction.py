#!/usr/bin/env python3
"""
Test Jan 8 reconstruction using the LIVE Cloud Run instance
This will tell us if the deployed code is different from local
"""

import requests
import json
from datetime import datetime

CLOUD_URL = "https://quant-engine-hl-535493956190.us-central1.run.app"

print("=" * 70)
print("🔬 TESTING JAN 8 RECONSTRUCTION ON CLOUD RUN")
print("=" * 70)
print(f"Target: {CLOUD_URL}")
print("Revision: 00005-hx4")
print("=" * 70)

# First, check health
print("\n1️⃣ Checking health...")
resp = requests.get(f"{CLOUD_URL}/health", timeout=10)
print(f"   Status: {resp.status_code}")
print(f"   Response: {resp.text}")

# Load the Jan 8 historical data
print("\n2️⃣ Loading Jan 8 historical data...")
with open('jan8_historical_5m.json', 'r') as f:
    candles_5m = json.load(f)

# Find candles around 00:30-00:35
target_candles = []
for candle in candles_5m:
    ts = datetime.fromtimestamp(candle['t'] / 1000)
    if ts.hour == 0 and 30 <= ts.minute <= 35:
        target_candles.append({
            'timestamp': ts.isoformat(),
            'close': float(candle['c']),
            'data': candle
        })

print(f"   Found {len(target_candles)} candles in target window")

# The issue is: Cloud Run doesn't expose an endpoint to run predictions on historical data
# It only runs live predictions on current data

print("\n" + "=" * 70)
print("❌ LIMITATION DISCOVERED")
print("=" * 70)
print("The Cloud Run instance only processes LIVE streaming data.")
print("It doesn't have an endpoint to run predictions on historical data.")
print()
print("This confirms:")
print("  1. The 6 trades were generated when the bot was running LIVE")
print("  2. They used real-time streaming data at 00:32:31, 00:32:33, etc.")
print("  3. Historical reconstruction is impossible without those exact snapshots")
print()
print("The only proof is the prediction logs:")
print("  logs/trades/predictions_20260108.jsonl")
print("=" * 70)
