#!/usr/bin/env python3
"""
Live Market Observation Dashboard
Real-time analysis of order flow, funding, and liquidation zones
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unified_phase4_collector import UnifiedPhase4Collector
import time
from datetime import datetime
import pandas as pd

class LiveMarketObserver:
    """
    Live market observation with strategy suggestions
    """
    
    def __init__(self):
        self.collector = UnifiedPhase4Collector()
        self.history = []
        
    def analyze_market_state(self, features):
        """
        Analyze current market state and identify patterns
        """
        
        analysis = {
            'timestamp': features['timestamp'],
            'price': features['price'],
            'signals': [],
            'warnings': [],
            'opportunities': []
        }
        
        # 1. Order Flow Analysis
        imbalance = features['ob_imbalance']
        
        if imbalance > 0.5:
            analysis['signals'].append(f"🟢 STRONG BUY PRESSURE (imbalance: {imbalance:.3f})")
            analysis['opportunities'].append("LONG setup - Large bids dominating")
        elif imbalance < -0.5:
            analysis['signals'].append(f"🔴 STRONG SELL PRESSURE (imbalance: {imbalance:.3f})")
            analysis['opportunities'].append("SHORT setup - Large asks dominating")
        else:
            analysis['signals'].append(f"⚪ BALANCED (imbalance: {imbalance:.3f})")
        
        # 2. Large Order Detection
        if features['ob_large_bids'] > 0:
            analysis['signals'].append(f"🐋 {features['ob_large_bids']} WHALE BID(S) detected")
            analysis['opportunities'].append(f"Whale support at ${features['ob_best_bid']:,.0f}")
        
        if features['ob_large_asks'] > 0:
            analysis['signals'].append(f"🐋 {features['ob_large_asks']} WHALE ASK(S) detected")
            analysis['warnings'].append(f"Whale resistance at ${features['ob_best_ask']:,.0f}")
        
        # 3. Funding Rate Analysis
        funding_pct = features['funding_pct']
        
        if features['funding_is_extreme']:
            if funding_pct > 0.08:
                analysis['warnings'].append(f"⚠️  EXTREME FUNDING: {funding_pct:.4f}% - Longs overcrowded")
                analysis['opportunities'].append("CONTRARIAN SHORT - Funding too high")
            elif funding_pct < -0.05:
                analysis['warnings'].append(f"⚠️  EXTREME FUNDING: {funding_pct:.4f}% - Shorts overcrowded")
                analysis['opportunities'].append("CONTRARIAN LONG - Funding too low")
        else:
            analysis['signals'].append(f"💰 Funding: {funding_pct:.4f}% (neutral)")
        
        # 4. Liquidation Zone Analysis
        liq_dist = features['liq_nearest_dist_pct']
        
        if features['liq_in_danger_zone']:
            analysis['warnings'].append(f"🔥 DANGER: {liq_dist:.2f}% from liquidation zone")
            analysis['opportunities'].append("Liquidation cascade possible - HIGH VOLATILITY expected")
        elif liq_dist < 1.5:
            analysis['warnings'].append(f"⚠️  Close to liquidation zone ({liq_dist:.2f}%)")
        
        # 5. Spread Analysis
        spread = features['ob_best_ask'] - features['ob_best_bid']
        spread_pct = (spread / features['price']) * 100
        
        if spread_pct > 0.05:
            analysis['warnings'].append(f"📊 WIDE SPREAD: ${spread:.2f} ({spread_pct:.3f}%)")
        
        return analysis
    
    def detect_pattern_changes(self):
        """
        Detect changes in market patterns over time
        """
        
        if len(self.history) < 2:
            return []
        
        changes = []
        current = self.history[-1]
        previous = self.history[-2]
        
        # Imbalance shift
        imb_change = current['ob_imbalance'] - previous['ob_imbalance']
        if abs(imb_change) > 0.3:
            direction = "BULLISH" if imb_change > 0 else "BEARISH"
            changes.append(f"📈 Order flow shifted {direction} ({imb_change:+.3f})")
        
        # Price movement
        price_change = current['price'] - previous['price']
        price_change_pct = (price_change / previous['price']) * 100
        if abs(price_change_pct) > 0.1:
            changes.append(f"💵 Price moved {price_change:+.2f} ({price_change_pct:+.3f}%)")
        
        # Whale activity
        if current['ob_large_bids'] > previous['ob_large_bids']:
            changes.append(f"🐋 NEW WHALE BID appeared!")
        if current['ob_large_asks'] > previous['ob_large_asks']:
            changes.append(f"🐋 NEW WHALE ASK appeared!")
        
        return changes
    
    def suggest_strategy(self, analysis, changes):
        """
        Suggest trading strategy based on analysis
        """
        
        suggestions = []
        
        # Count bullish vs bearish signals
        bullish_count = sum([
            1 for s in analysis['signals'] + analysis['opportunities'] 
            if 'BUY' in s or 'LONG' in s or 'BULLISH' in s or 'support' in s
        ])
        
        bearish_count = sum([
            1 for s in analysis['signals'] + analysis['opportunities'] 
            if 'SELL' in s or 'SHORT' in s or 'BEARISH' in s or 'resistance' in s
        ])
        
        # Strong directional bias
        if bullish_count >= 2 and bearish_count == 0:
            suggestions.append("✅ STRONG LONG SETUP")
            suggestions.append(f"   Entry: ${analysis['price']:,.2f}")
            suggestions.append(f"   TP: ${analysis['price'] * 1.012:,.2f} (+1.2%)")
            suggestions.append(f"   SL: ${analysis['price'] * 0.994:,.2f} (-0.6%)")
        
        elif bearish_count >= 2 and bullish_count == 0:
            suggestions.append("✅ STRONG SHORT SETUP")
            suggestions.append(f"   Entry: ${analysis['price']:,.2f}")
            suggestions.append(f"   TP: ${analysis['price'] * 0.988:,.2f} (-1.2%)")
            suggestions.append(f"   SL: ${analysis['price'] * 1.006:,.2f} (+0.6%)")
        
        elif bullish_count > 0 and bearish_count > 0:
            suggestions.append("⚠️  MIXED SIGNALS - Wait for clarity")
        
        else:
            suggestions.append("⏸️  NO CLEAR SETUP - Continue observing")
        
        return suggestions
    
    def observe_live(self, interval_seconds=30, max_iterations=None):
        """
        Observe market live and provide real-time analysis
        """
        
        print("="*80)
        print("🔴 LIVE MARKET OBSERVATION - Phase 4 Precision Engine")
        print("="*80)
        print(f"Interval: {interval_seconds}s")
        print(f"Data: Order Flow + Funding + Liquidations")
        print("Press Ctrl+C to stop")
        print("="*80)
        
        iteration = 0
        
        try:
            while True:
                iteration += 1
                
                # Collect features
                print(f"\n{'='*80}")
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Observation #{iteration}")
                print(f"{'='*80}")
                
                features = self.collector.collect_all_features()
                
                if not features:
                    print("❌ Failed to collect data")
                    time.sleep(interval_seconds)
                    continue
                
                # Store in history
                self.history.append(features)
                
                # Analyze
                analysis = self.analyze_market_state(features)
                
                # Display current state
                print(f"\n💰 BTC: ${analysis['price']:,.2f}")
                print(f"🕐 Time: {analysis['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Signals
                if analysis['signals']:
                    print(f"\n📊 MARKET SIGNALS:")
                    for signal in analysis['signals']:
                        print(f"   {signal}")
                
                # Warnings
                if analysis['warnings']:
                    print(f"\n⚠️  WARNINGS:")
                    for warning in analysis['warnings']:
                        print(f"   {warning}")
                
                # Opportunities
                if analysis['opportunities']:
                    print(f"\n💡 OPPORTUNITIES:")
                    for opp in analysis['opportunities']:
                        print(f"   {opp}")
                
                # Pattern changes
                if len(self.history) >= 2:
                    changes = self.detect_pattern_changes()
                    if changes:
                        print(f"\n🔄 PATTERN CHANGES:")
                        for change in changes:
                            print(f"   {change}")
                
                # Strategy suggestion
                suggestions = self.suggest_strategy(analysis, changes if len(self.history) >= 2 else [])
                if suggestions:
                    print(f"\n🎯 STRATEGY SUGGESTION:")
                    for suggestion in suggestions:
                        print(f"   {suggestion}")
                
                # Check if we should stop
                if max_iterations and iteration >= max_iterations:
                    print(f"\n✅ Completed {max_iterations} observations")
                    break
                
                # Wait
                print(f"\n⏳ Next observation in {interval_seconds}s...")
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Stopped by user")
        
        # Summary
        print(f"\n{'='*80}")
        print(f"📊 OBSERVATION SUMMARY")
        print(f"{'='*80}")
        print(f"Total observations: {len(self.history)}")
        
        if len(self.history) > 0:
            df = pd.DataFrame(self.history)
            print(f"\nPrice range: ${df['price'].min():,.2f} - ${df['price'].max():,.2f}")
            print(f"Avg imbalance: {df['ob_imbalance'].mean():.3f}")
            print(f"Avg funding: {df['funding_pct'].mean():.4f}%")
            print(f"Whale bids seen: {df['ob_large_bids'].sum()}")
            print(f"Whale asks seen: {df['ob_large_asks'].sum()}")
        
        print(f"{'='*80}")

# Main
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Live Market Observer')
    parser.add_argument('--interval', type=int, default=30,
                       help='Seconds between observations (default: 30)')
    parser.add_argument('--count', type=int, default=None,
                       help='Number of observations (None = infinite)')
    
    args = parser.parse_args()
    
    observer = LiveMarketObserver()
    observer.observe_live(interval_seconds=args.interval, max_iterations=args.count)
