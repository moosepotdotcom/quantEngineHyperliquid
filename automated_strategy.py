#!/usr/bin/env python3
"""
Phase 4 Automated Trading Strategy
Based on live market observations and real-time data
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from working_collectors import WorkingCollectors
from datetime import datetime
import time

class Phase4TradingStrategy:
    """
    Automated trading strategy using:
    - Order flow imbalance
    - Whale activity detection
    - Funding rate extremes
    - Liquidation zone proximity
    """
    
    def __init__(self):
        self.collector = WorkingCollectors()
        self.position = None
        self.trades = []
        
    def analyze_setup(self):
        """
        Analyze current market for trading setup
        
        Returns:
            dict with signal, entry, tp, sl, confidence
        """
        
        # Collect data
        price = self.collector.get_current_price()
        ob = self.collector.get_orderbook_features()
        funding = self.collector.get_funding_features()
        
        if price == 0:
            return None
        
        # Calculate liquidation zones
        liq_long_near = price * 0.98  # -2%
        liq_short_near = price * 1.02  # +2%
        
        # Initialize signal
        signal = {
            'timestamp': datetime.now(),
            'price': price,
            'direction': None,
            'entry': price,
            'tp': 0,
            'sl': 0,
            'confidence': 0,
            'reasons': []
        }
        
        # LONG SETUP CRITERIA
        long_score = 0
        long_reasons = []
        
        # 1. Strong buy pressure (imbalance > 0.5)
        if ob['ob_imbalance'] > 0.5:
            long_score += 3
            long_reasons.append(f"Strong buy pressure ({ob['ob_imbalance']:.3f})")
        elif ob['ob_imbalance'] > 0.3:
            long_score += 2
            long_reasons.append(f"Moderate buy pressure ({ob['ob_imbalance']:.3f})")
        
        # 2. Whale support
        if ob['ob_large_bids'] > 0:
            long_score += 2
            long_reasons.append(f"{ob['ob_large_bids']} whale bid(s)")
        
        # 3. Thin ask side (easy breakout)
        if ob['ob_ask_depth'] < ob['ob_bid_depth'] * 0.3:
            long_score += 2
            long_reasons.append(f"Thin asks ({ob['ob_ask_depth']:.1f} vs {ob['ob_bid_depth']:.1f} bids)")
        
        # 4. Funding not extreme (avoid overcrowded longs)
        if not funding['funding_is_extreme'] or funding['funding_pct'] < 0.05:
            long_score += 1
            long_reasons.append("Funding neutral")
        
        # 5. Not near long liquidation zone
        if price > liq_long_near * 1.01:  # At least 1% above liq zone
            long_score += 1
            long_reasons.append("Safe from liquidations")
        
        # SHORT SETUP CRITERIA
        short_score = 0
        short_reasons = []
        
        # 1. Strong sell pressure (imbalance < -0.5)
        if ob['ob_imbalance'] < -0.5:
            short_score += 3
            short_reasons.append(f"Strong sell pressure ({ob['ob_imbalance']:.3f})")
        elif ob['ob_imbalance'] < -0.3:
            short_score += 2
            short_reasons.append(f"Moderate sell pressure ({ob['ob_imbalance']:.3f})")
        
        # 2. Whale resistance
        if ob['ob_large_asks'] > 0:
            short_score += 2
            short_reasons.append(f"{ob['ob_large_asks']} whale ask(s)")
        
        # 3. Thin bid side (easy breakdown)
        if ob['ob_bid_depth'] < ob['ob_ask_depth'] * 0.3:
            short_score += 2
            short_reasons.append(f"Thin bids ({ob['ob_bid_depth']:.1f} vs {ob['ob_ask_depth']:.1f} asks)")
        
        # 4. Funding not extreme (avoid overcrowded shorts)
        if not funding['funding_is_extreme'] or funding['funding_pct'] > -0.03:
            short_score += 1
            short_reasons.append("Funding neutral")
        
        # 5. Not near short liquidation zone
        if price < liq_short_near * 0.99:  # At least 1% below liq zone
            short_score += 1
            short_reasons.append("Safe from liquidations")
        
        # DECISION LOGIC
        min_score = 5  # Minimum score to take trade
        
        if long_score >= min_score and long_score > short_score:
            signal['direction'] = 'LONG'
            signal['entry'] = price
            signal['tp'] = price * 1.012  # +1.2%
            signal['sl'] = price * 0.994  # -0.6%
            signal['confidence'] = min(long_score / 9, 1.0)  # Max 9 points
            signal['reasons'] = long_reasons
            
        elif short_score >= min_score and short_score > long_score:
            signal['direction'] = 'SHORT'
            signal['entry'] = price
            signal['tp'] = price * 0.988  # -1.2%
            signal['sl'] = price * 1.006  # +0.6%
            signal['confidence'] = min(short_score / 9, 1.0)
            signal['reasons'] = short_reasons
        
        return signal
    
    def execute_trade(self, signal):
        """
        Execute trade based on signal (paper trading)
        """
        
        if signal['direction'] is None:
            return None
        
        trade = {
            'entry_time': signal['timestamp'],
            'direction': signal['direction'],
            'entry_price': signal['entry'],
            'tp': signal['tp'],
            'sl': signal['sl'],
            'confidence': signal['confidence'],
            'reasons': signal['reasons'],
            'status': 'OPEN',
            'exit_price': None,
            'exit_time': None,
            'pnl': 0,
            'pnl_pct': 0
        }
        
        self.position = trade
        self.trades.append(trade)
        
        return trade
    
    def check_exit(self):
        """
        Check if current position should be closed
        """
        
        if self.position is None or self.position['status'] != 'OPEN':
            return None
        
        current_price = self.collector.get_current_price()
        
        if current_price == 0:
            return None
        
        # Check TP/SL
        if self.position['direction'] == 'LONG':
            if current_price >= self.position['tp']:
                return self.close_position(current_price, 'TP')
            elif current_price <= self.position['sl']:
                return self.close_position(current_price, 'SL')
        
        elif self.position['direction'] == 'SHORT':
            if current_price <= self.position['tp']:
                return self.close_position(current_price, 'TP')
            elif current_price >= self.position['sl']:
                return self.close_position(current_price, 'SL')
        
        return None
    
    def close_position(self, exit_price, reason):
        """
        Close current position
        """
        
        if self.position is None:
            return None
        
        self.position['exit_price'] = exit_price
        self.position['exit_time'] = datetime.now()
        self.position['status'] = reason
        
        # Calculate PnL
        if self.position['direction'] == 'LONG':
            pnl_pct = ((exit_price - self.position['entry_price']) / self.position['entry_price']) * 100
        else:  # SHORT
            pnl_pct = ((self.position['entry_price'] - exit_price) / self.position['entry_price']) * 100
        
        self.position['pnl_pct'] = pnl_pct
        
        closed_position = self.position
        self.position = None
        
        return closed_position
    
    def run_strategy(self, check_interval=30, max_trades=None):
        """
        Run automated strategy
        
        Args:
            check_interval: Seconds between checks
            max_trades: Max trades to execute (None = infinite)
        """
        
        print("="*80)
        print("🤖 PHASE 4 AUTOMATED TRADING STRATEGY")
        print("="*80)
        print(f"Check interval: {check_interval}s")
        print(f"Max trades: {max_trades if max_trades else 'Unlimited'}")
        print("Strategy: Order Flow + Whale Detection + Funding + Liquidations")
        print("="*80)
        print("\nPress Ctrl+C to stop\n")
        
        try:
            while True:
                # Check for exit if in position
                if self.position:
                    exit_result = self.check_exit()
                    if exit_result:
                        print(f"\n{'='*80}")
                        print(f"🔔 POSITION CLOSED - {exit_result['status']}")
                        print(f"{'='*80}")
                        print(f"Direction: {exit_result['direction']}")
                        print(f"Entry: ${exit_result['entry_price']:,.2f}")
                        print(f"Exit: ${exit_result['exit_price']:,.2f}")
                        print(f"PnL: {exit_result['pnl_pct']:+.2f}%")
                        print(f"Duration: {(exit_result['exit_time'] - exit_result['entry_time']).seconds}s")
                        print(f"{'='*80}\n")
                        
                        # Check if we've hit max trades
                        if max_trades and len([t for t in self.trades if t['status'] != 'OPEN']) >= max_trades:
                            print(f"✅ Reached {max_trades} trades. Stopping.")
                            break
                
                # Look for new setup if not in position
                if self.position is None:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Scanning for setup...")
                    
                    signal = self.analyze_setup()
                    
                    if signal and signal['direction']:
                        print(f"\n{'='*80}")
                        print(f"🎯 SIGNAL DETECTED - {signal['direction']}")
                        print(f"{'='*80}")
                        print(f"Price: ${signal['price']:,.2f}")
                        print(f"Confidence: {signal['confidence']*100:.0f}%")
                        print(f"Reasons:")
                        for reason in signal['reasons']:
                            print(f"   ✓ {reason}")
                        print(f"\nTrade Setup:")
                        print(f"   Entry: ${signal['entry']:,.2f}")
                        print(f"   TP: ${signal['tp']:,.2f} ({((signal['tp']/signal['entry'])-1)*100:+.2f}%)")
                        print(f"   SL: ${signal['sl']:,.2f} ({((signal['sl']/signal['entry'])-1)*100:+.2f}%)")
                        print(f"{'='*80}\n")
                        
                        # Execute trade
                        trade = self.execute_trade(signal)
                        print(f"✅ Position opened: {trade['direction']}\n")
                    else:
                        print("   No setup found\n")
                
                # Wait
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Strategy stopped by user")
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print trading summary"""
        
        print(f"\n{'='*80}")
        print("📊 TRADING SUMMARY")
        print(f"{'='*80}")
        
        closed_trades = [t for t in self.trades if t['status'] != 'OPEN']
        
        if not closed_trades:
            print("No completed trades")
            return
        
        wins = [t for t in closed_trades if t['pnl_pct'] > 0]
        losses = [t for t in closed_trades if t['pnl_pct'] < 0]
        
        print(f"Total trades: {len(closed_trades)}")
        print(f"Wins: {len(wins)} ({len(wins)/len(closed_trades)*100:.1f}%)")
        print(f"Losses: {len(losses)} ({len(losses)/len(closed_trades)*100:.1f}%)")
        print(f"Avg PnL: {sum([t['pnl_pct'] for t in closed_trades])/len(closed_trades):+.2f}%")
        print(f"Best trade: {max([t['pnl_pct'] for t in closed_trades]):+.2f}%")
        print(f"Worst trade: {min([t['pnl_pct'] for t in closed_trades]):+.2f}%")
        print(f"{'='*80}")

# Main
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Phase 4 Automated Trading Strategy')
    parser.add_argument('--interval', type=int, default=30,
                       help='Seconds between checks (default: 30)')
    parser.add_argument('--max-trades', type=int, default=None,
                       help='Maximum trades to execute')
    
    args = parser.parse_args()
    
    strategy = Phase4TradingStrategy()
    strategy.run_strategy(check_interval=args.interval, max_trades=args.max_trades)
