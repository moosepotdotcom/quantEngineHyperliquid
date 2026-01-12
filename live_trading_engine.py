#!/usr/bin/env python3
"""
Live Trading Integration Module
Connects AI trading bot with Hyperliquid live execution

This module:
1. Monitors AI model signals
2. Executes trades on Hyperliquid
3. Manages positions and risk
4. Runs paper trading in parallel
"""

import os
import sys
import time
from datetime import datetime
from typing import Optional, Dict

# Import existing components
from quant_engine import TradingEngine
from hyperliquid_live_trader import HyperliquidTrader


class LiveTradingEngine:
    """
    Integrated trading engine that runs both:
    - Paper trading (tracking signals)
    - Live trading (executing on Hyperliquid)
    """
    
    def __init__(self, enable_live: bool = False, testnet: bool = True):
        """
        Initialize integrated trading engine
        
        Args:
            enable_live: If True, execute real trades. If False, paper trade only.
            testnet: If True, use Hyperliquid testnet
        """
        print("🚀 Initializing Integrated Trading Engine")
        print("="*70)
        
        # Initialize paper trading engine
        print("\n📊 Loading Paper Trading Engine...")
        self.paper_engine = TradingEngine()
        
        # Initialize live trader (if enabled)
        self.enable_live = enable_live
        self.live_trader = None
        
        if enable_live:
            print("\n💰 Loading Live Trading Engine...")
            try:
                self.live_trader = HyperliquidTrader(testnet=testnet)
                print(f"✅ Live trading {'ENABLED' if not testnet else 'ENABLED (TESTNET)'}")
            except Exception as e:
                print(f"❌ Failed to initialize live trader: {e}")
                print("⚠️  Continuing with paper trading only")
                self.enable_live = False
        else:
            print("\n📝 Live trading DISABLED (paper trading only)")
        
        print("\n" + "="*70)
        print("✅ Initialization Complete!")
        print("="*70)
    
    def process_signal(self, signal: Optional[Dict], confidence: float, model_name: str):
        """
        Process a trading signal from AI model
        
        Args:
            signal: Signal dictionary (or None if no signal)
            confidence: Model confidence
            model_name: Name of the model
        """
        if signal is None:
            return
        
        print(f"\n🎯 Signal Detected!")
        print(f"   Model: {model_name}")
        print(f"   Price: ${signal.get('price'):,.2f}")
        print(f"   Confidence: {confidence:.2%}")
        
        # Always execute in paper trading
        print(f"\n📝 Paper Trading: Logging signal...")
        self.paper_engine.execute_trade(signal)
        
        # Execute in live trading (if enabled)
        if self.enable_live and self.live_trader:
            # We trust the engine's internal thresholding now.
            # If TradingEngine returned a signal, it passed metadata thresholds.
            print(f"\n💰 Live Trading: Executing {signal.get('direction', 'LONG')} order...")
            success = self.live_trader.execute_signal(signal)
            
            if success:
                print(f"✅ Live order executed!")
            else:
                print(f"❌ Live order failed")
    
    def check_positions(self, current_price: float):
        """
        Check positions for both paper and live trading
        
        Args:
            current_price: Current BTC price
        """
        # Check paper trading positions
        if hasattr(self.paper_engine, 'exit_monitor'):
            closed_trades = self.paper_engine.exit_monitor.check_exits()
            for trade in closed_trades:
                print(f"📊 Paper trade closed: {trade['model']} {trade['outcome']}. Reporting to learning engine...")
                self.paper_engine.report_outcome(trade['model'], trade['outcome'])
        
        # Check live trading positions
        if self.enable_live and self.live_trader:
            self.live_trader.check_positions(current_price)
    
    def run_continuous(self):
        """Run continuous monitoring for both paper and live trading"""
        print("\n🔄 Starting Continuous Monitoring")
        print("="*70)
        print("📝 Paper Trading: ACTIVE")
        print(f"💰 Live Trading: {'ACTIVE' if self.enable_live else 'INACTIVE'}")
        print("="*70)
        
        iteration = 0
        
        try:
            while True:
                iteration += 1
                current_time = datetime.now().strftime("%H:%M:%S")
                
                # Dynamic Threshold Reload
                if hasattr(self.paper_engine, 'load_thresholds'):
                    self.paper_engine.load_thresholds()
                
                print(f"\n{'='*70}")
                print(f"⏰ {current_time} | Check #{iteration}")
                print(f"{'='*70}")
                
                # Check Winner Hunter
                print("\n🏆 Checking Winner Hunter (1H)...")
                wh_signal, wh_confidence = self.paper_engine.check_winner_hunter()
                direction_wh = wh_signal.get('direction', 'None') if wh_signal else 'None'
                print(f"   Conf: {wh_confidence:.2%} | Signal: {direction_wh}")
                self.process_signal(wh_signal, wh_confidence, "Winner Hunter (1H)")
                
                # Check MTF Scalper
                print("\n🎯 Checking MTF Scalper (5M)...")
                mtf_signal, mtf_confidence = self.paper_engine.check_mtf_scalper()
                direction_mtf = mtf_signal.get('direction', 'None') if mtf_signal else 'None'
                print(f"   Conf: {mtf_confidence:.2%} | Signal: {direction_mtf}")
                self.process_signal(mtf_signal, mtf_confidence, "MTF Scalper (5M)")
                
                # Check Gem Sniper (Added for Ultra-Precision)
                print("\n💎 Checking Gem Sniper (5M)...")
                gem_signal, gem_confidence = self.paper_engine.check_gem_sniper()
                direction_gem = gem_signal.get('direction', 'None') if gem_signal else 'None'
                print(f"   Conf: {gem_confidence:.2%} | Signal: {direction_gem}")
                self.process_signal(gem_signal, gem_confidence, "Gem Sniper (ULTRA)")
                
                # Get current price for position checks
                import requests
                try:
                    response = requests.post(
                        "https://api.hyperliquid.xyz/info",
                        json={
                            "type": "candleSnapshot",
                            "req": {
                                "coin": "BTC",
                                "interval": "1h",
                                "startTime": 0,
                                "endTime": 9999999999999
                            }
                        },
                        timeout=10
                    )
                    if response.status_code == 200:
                        data = response.json()
                        current_price = float(data[-1]['c'])
                        
                        # Check positions
                        self.check_positions(current_price)
                        
                        # Display status
                        if self.enable_live and self.live_trader:
                            status = self.live_trader.get_status()
                            print(f"\n💰 Live Trading Status:")
                            print(f"   Daily P&L: ${status['daily_pnl']:.2f}")
                            print(f"   Active Positions: {status['active_positions']}")
                
                except Exception as e:
                    print(f"⚠️  Error checking positions: {e}")
                
                # Display exit monitor status
                if hasattr(self.paper_engine, 'exit_monitor'):
                    self.paper_engine.exit_monitor.display_status()
                
                # Wait before next check
                print(f"\n⏳ Next check in 60 seconds...")
                time.sleep(60)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping trading engine...")
            
            # Emergency stop live trading if active
            if self.enable_live and self.live_trader:
                print("🚨 Closing all live positions...")
                self.live_trader.emergency_stop_all()
            
            print("✅ Shutdown complete")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='AI Trading Bot with Live Execution')
    parser.add_argument(
        '--live',
        action='store_true',
        help='Enable live trading (default: paper trading only)'
    )
    parser.add_argument(
        '--mainnet',
        action='store_true',
        help='Use mainnet (default: testnet)'
    )
    
    args = parser.parse_args()
    
    # Confirm live trading (skip if running in cloud environment)
    if args.live:
        import os
        # Check if running in Cloud Run (no interactive terminal)
        is_cloud = os.getenv('K_SERVICE') is not None or not sys.stdin.isatty()
        
        if not is_cloud:
            print("\n" + "="*70)
            print("⚠️  WARNING: LIVE TRADING MODE")
            print("="*70)
            print("You are about to enable REAL trading with REAL money!")
            print(f"Mode: {'MAINNET' if args.mainnet else 'TESTNET'}")
            print("\nMake sure you have:")
            print("1. ✅ Tested on testnet successfully")
            print("2. ✅ Set up your .env.live_trading file")
            print("3. ✅ Deposited funds ($10 recommended for testing)")
            print("4. ✅ Understand the risks")
            print("="*70)
            
            confirm = input("\nType 'YES' to continue with live trading: ")
            if confirm != 'YES':
                print("❌ Live trading cancelled")
                return
        else:
            # Running in Cloud Run - auto-confirm
            print("\n" + "="*70)
            print("🚀 LIVE TRADING MODE - CLOUD RUN")
            print("="*70)
            print(f"Mode: {'MAINNET' if args.mainnet else 'TESTNET'}")
            print("Auto-starting (no confirmation needed in cloud)")
            print("="*70)
    
    # Initialize and run
    engine = LiveTradingEngine(
        enable_live=args.live,
        testnet=not args.mainnet
    )
    
    engine.run_continuous()


if __name__ == '__main__':
    main()
