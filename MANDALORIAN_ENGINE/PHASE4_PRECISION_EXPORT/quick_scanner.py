#!/usr/bin/env python3
"""
Quick Live Market Scanner - Immediate Results
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from working_collectors import WorkingCollectors
import time

def quick_scan(num_scans=5, interval=10):
    """Quick market scan with immediate analysis"""
    
    collector = WorkingCollectors()
    
    print("="*80)
    print("🔴 LIVE MARKET SCANNER - Quick Analysis")
    print("="*80)
    print(f"Scans: {num_scans} | Interval: {interval}s")
    print("="*80)
    
    for i in range(num_scans):
        print(f"\n{'='*80}")
        print(f"SCAN #{i+1}/{num_scans} - {time.strftime('%H:%M:%S')}")
        print(f"{'='*80}")
        
        # Get data
        price = collector.get_current_price()
        ob = collector.get_orderbook_features()
        funding = collector.get_funding_features()
        
        if price == 0:
            print("❌ Failed to get data")
            continue
        
        # Display
        print(f"\n💰 BTC PRICE: ${price:,.2f}")
        print(f"\n📊 ORDER BOOK:")
        print(f"   Imbalance: {ob['ob_imbalance']:+.3f} {'🟢 BULLISH' if ob['ob_imbalance'] > 0.3 else '🔴 BEARISH' if ob['ob_imbalance'] < -0.3 else '⚪ NEUTRAL'}")
        print(f"   Bid Depth: {ob['ob_bid_depth']:.2f} BTC")
        print(f"   Ask Depth: {ob['ob_ask_depth']:.2f} BTC")
        print(f"   Spread: ${ob['ob_best_ask'] - ob['ob_best_bid']:.2f}")
        
        if ob['ob_large_bids'] > 0:
            print(f"   🐋 {ob['ob_large_bids']} WHALE BID(S) @ ${ob['ob_best_bid']:,.0f}")
        if ob['ob_large_asks'] > 0:
            print(f"   🐋 {ob['ob_large_asks']} WHALE ASK(S) @ ${ob['ob_best_ask']:,.0f}")
        
        print(f"\n💸 FUNDING:")
        print(f"   Rate: {funding['funding_pct']:.4f}% (8h)")
        print(f"   Annual: {funding['funding_pct'] * 365 * 3:.2f}%")
        print(f"   OI: {funding['oi_millions']:.2f}M BTC (${funding['oi_millions'] * price:,.0f}M)")
        
        # Simple strategy
        print(f"\n🎯 QUICK ANALYSIS:")
        
        signals = []
        if ob['ob_imbalance'] > 0.5:
            signals.append("✅ STRONG BUY PRESSURE - Consider LONG")
        elif ob['ob_imbalance'] < -0.5:
            signals.append("✅ STRONG SELL PRESSURE - Consider SHORT")
        
        if ob['ob_large_bids'] > 0 and ob['ob_imbalance'] > 0:
            signals.append("🐋 Whale support + bullish flow = LONG SETUP")
        elif ob['ob_large_asks'] > 0 and ob['ob_imbalance'] < 0:
            signals.append("🐋 Whale resistance + bearish flow = SHORT SETUP")
        
        if funding['funding_is_extreme']:
            if funding['funding_pct'] > 0.08:
                signals.append("⚠️  Extreme funding - Longs overcrowded - CONTRARIAN SHORT")
            else:
                signals.append("⚠️  Extreme funding - Shorts overcrowded - CONTRARIAN LONG")
        
        if signals:
            for sig in signals:
                print(f"   {sig}")
        else:
            print("   ⏸️  No clear setup - Wait for better opportunity")
        
        if i < num_scans - 1:
            print(f"\n⏳ Next scan in {interval}s...")
            time.sleep(interval)
    
    print(f"\n{'='*80}")
    print("✅ SCAN COMPLETE")
    print("="*80)

if __name__ == "__main__":
    quick_scan(num_scans=5, interval=10)
