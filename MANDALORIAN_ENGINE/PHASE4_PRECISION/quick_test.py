#!/usr/bin/env python3
"""Quick test of all fixed collectors"""

import sys
sys.path.insert(0, '/Users/alifiyaa/Downloads/quantEngineHyperliquid/MANDALORIAN_ENGINE/PHASE4_PRECISION')

print("="*60)
print("🧪 Testing Phase 4 Data Collectors")
print("="*60)

# Test 1: Order Flow
print("\n1️⃣ Order Flow Tracker...")
try:
    from orderflow_tracker import OrderFlowTracker
    tracker = OrderFlowTracker()
    ob = tracker.get_orderbook()
    if ob['bids'] and ob['asks']:
        print(f"   ✅ Working! {len(ob['bids'])} bids, {len(ob['asks'])} asks")
        print(f"   Best bid: ${ob['bids'][0][0]:,.2f}")
        print(f"   Best ask: ${ob['asks'][0][0]:,.2f}")
    else:
        print("   ❌ No data")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 2: Funding Monitor
print("\n2️⃣ Funding Monitor...")
try:
    from funding_monitor import FundingRateMonitor
    monitor = FundingRateMonitor()
    funding = monitor.get_current_funding()
    oi = monitor.get_open_interest()
    print(f"   ✅ Working!")
    print(f"   Funding: {funding*100:.4f}%")
    print(f"   OI: ${oi/1_000_000:.2f}M")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Unified Collector
print("\n3️⃣ Unified Collector...")
try:
    from unified_collector import Phase4FeatureCollector
    collector = Phase4FeatureCollector()
    features = collector.get_all_features(95000)
    print(f"   ✅ Working! {len(features)} features collected")
    print(f"   Sample: ob_imbalance_10 = {features.get('ob_imbalance_10', 'N/A')}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "="*60)
print("✅ Test Complete!")
print("="*60)
