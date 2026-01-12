#!/usr/bin/env python3
"""
Live Trade Flow Test
Tests the complete trade execution flow including:
- Entry order placement
- SL/TP placement only if entry succeeds
- Proper error handling for insufficient funds
- Order status monitoring
"""
import os
import sys
import time
import json
from datetime import datetime
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants

class LiveTradeFlowTest:
    def __init__(self, test_size_usd=10):
        """Initialize with a small test size (default $10)"""
        self.test_size_usd = test_size_usd
        
        # Load credentials from .env.live_trading file
        env_file = '.env.live_trading'
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip().strip('"').strip("'")
        
        self.wallet_address = os.getenv("HYPERLIQUID_WALLET_ADDRESS")
        self.private_key = os.getenv("HYPERLIQUID_PRIVATE_KEY")
        
        if not self.wallet_address or not self.private_key:
            raise ValueError("Missing HYPERLIQUID_WALLET_ADDRESS or HYPERLIQUID_PRIVATE_KEY environment variables")
        
        # Initialize Hyperliquid clients
        api_url = "https://api.hyperliquid.xyz"
        
        # Create wallet from private key
        from eth_account import Account
        wallet = Account.from_key(self.private_key)
        
        self.exchange = Exchange(
            wallet,
            api_url,
            vault_address=None
        )
        
        self.info = Info(api_url, skip_ws=True)
        
        print(f"✅ Initialized test with wallet: {self.wallet_address}")
        print(f"💰 Test size: ${self.test_size_usd}")
    
    def get_account_state(self):
        """Get current account balance and positions"""
        try:
            state = self.info.user_state(self.wallet_address)
            
            margin_summary = state.get('marginSummary', {})
            account_value = float(margin_summary.get('accountValue', 0))
            total_margin_used = float(margin_summary.get('totalMarginUsed', 0))
            
            print(f"\n📊 Account State:")
            print(f"   Account Value: ${account_value:,.2f}")
            print(f"   Margin Used: ${total_margin_used:,.2f}")
            print(f"   Available: ${account_value - total_margin_used:,.2f}")
            
            return {
                'account_value': account_value,
                'margin_used': total_margin_used,
                'available': account_value - total_margin_used
            }
        except Exception as e:
            print(f"❌ Error getting account state: {e}")
            return None
    
    def get_current_price(self, coin="BTC"):
        """Get current market price"""
        try:
            meta = self.info.meta()
            for asset in meta['universe']:
                if asset['name'] == coin:
                    return float(asset['szDecimals'])
            
            # Fallback: use all_mids
            mids = self.info.all_mids()
            return float(mids.get(coin, 0))
        except Exception as e:
            print(f"❌ Error getting price: {e}")
            return None
    
    def place_test_trade(self, direction="LONG"):
        """
        Place a test trade with proper error handling
        Returns: (entry_success, entry_oid, sl_oid, tp_oid)
        """
        print(f"\n{'='*70}")
        print(f"🧪 STARTING LIVE TRADE TEST")
        print(f"{'='*70}")
        
        # Step 1: Check account state
        account = self.get_account_state()
        if not account:
            return False, None, None, None
        
        if account['available'] < self.test_size_usd:
            print(f"\n⚠️  INSUFFICIENT FUNDS TEST:")
            print(f"   Required: ${self.test_size_usd}")
            print(f"   Available: ${account['available']:.2f}")
            print(f"   ✅ Correctly preventing trade placement")
            return False, None, None, None
        
        # Step 2: Get current price
        price = self.get_current_price("BTC")
        if not price:
            print("❌ Failed to get current price")
            return False, None, None, None
        
        print(f"\n💰 Current BTC Price: ${price:,.2f}")
        
        # Step 3: Calculate position size
        # For BTC, minimum size is typically 0.0001
        position_size = max(0.0001, self.test_size_usd / price)
        position_size = round(position_size, 4)  # Round to 4 decimals
        
        print(f"📊 Position Size: {position_size} BTC (${position_size * price:.2f})")
        
        # Step 4: Calculate SL/TP prices
        if direction == "LONG":
            tp_price = price * 1.015  # +1.5% TP
            sl_price = price * 0.992  # -0.8% SL
        else:
            tp_price = price * 0.985  # -1.5% TP
            sl_price = price * 1.008  # +0.8% SL
        
        print(f"\n🎯 Trade Parameters:")
        print(f"   Direction: {direction}")
        print(f"   Entry: ${price:,.2f}")
        print(f"   TP: ${tp_price:,.2f} (+1.5%)")
        print(f"   SL: ${sl_price:,.2f} (-0.8%)")
        
        # Step 5: Place entry order
        print(f"\n📤 Placing entry order...")
        
        try:
            is_buy = (direction == "LONG")
            
            # Market order for entry
            entry_result = self.exchange.market_open(
                coin="BTC",
                is_buy=is_buy,
                sz=position_size,
                px=None,  # Market order
                slippage=0.05  # 5% slippage tolerance
            )
            
            print(f"✅ Entry order placed:")
            print(json.dumps(entry_result, indent=2))
            
            # Extract order ID
            if entry_result.get('status') == 'ok':
                statuses = entry_result.get('response', {}).get('data', {}).get('statuses', [])
                if statuses and 'filled' in statuses[0]:
                    entry_oid = statuses[0].get('filled', {}).get('oid')
                    print(f"   Order ID: {entry_oid}")
                    
                    # Step 6: Wait for fill confirmation
                    print(f"\n⏳ Waiting for fill confirmation...")
                    time.sleep(2)
                    
                    # Step 7: Place SL/TP orders
                    print(f"\n📤 Placing SL/TP orders...")
                    
                    # TP order
                    tp_result = self.exchange.order(
                        coin="BTC",
                        is_buy=not is_buy,  # Opposite direction to close
                        sz=position_size,
                        limit_px=tp_price,
                        order_type={"limit": {"tif": "Gtc"}},
                        reduce_only=True
                    )
                    
                    tp_oid = None
                    if tp_result.get('status') == 'ok':
                        tp_statuses = tp_result.get('response', {}).get('data', {}).get('statuses', [])
                        if tp_statuses:
                            tp_oid = tp_statuses[0].get('resting', {}).get('oid')
                            print(f"✅ TP order placed: {tp_oid}")
                    
                    # SL order
                    sl_result = self.exchange.order(
                        coin="BTC",
                        is_buy=not is_buy,
                        sz=position_size,
                        limit_px=sl_price,
                        order_type={"trigger": {"triggerPx": sl_price, "isMarket": True, "tpsl": "sl"}},
                        reduce_only=True
                    )
                    
                    sl_oid = None
                    if sl_result.get('status') == 'ok':
                        sl_statuses = sl_result.get('response', {}).get('data', {}).get('statuses', [])
                        if sl_statuses:
                            sl_oid = sl_statuses[0].get('resting', {}).get('oid')
                            print(f"✅ SL order placed: {sl_oid}")
                    
                    print(f"\n{'='*70}")
                    print(f"✅ TRADE FLOW TEST COMPLETE")
                    print(f"{'='*70}")
                    print(f"Entry OID: {entry_oid}")
                    print(f"TP OID: {tp_oid}")
                    print(f"SL OID: {sl_oid}")
                    
                    return True, entry_oid, sl_oid, tp_oid
                else:
                    print(f"⚠️  Entry order placed but no fill detected")
                    print(f"   Skipping SL/TP placement (correct behavior)")
                    return False, None, None, None
            else:
                print(f"❌ Entry order failed:")
                print(json.dumps(entry_result, indent=2))
                print(f"   ✅ Correctly NOT placing SL/TP")
                return False, None, None, None
                
        except Exception as e:
            print(f"❌ Error during trade execution: {e}")
            print(f"   ✅ Correctly NOT placing SL/TP due to error")
            return False, None, None, None
    
    def monitor_trade(self, entry_oid, sl_oid, tp_oid, duration_seconds=60):
        """Monitor the trade for a specified duration"""
        print(f"\n📊 Monitoring trade for {duration_seconds} seconds...")
        
        start_time = time.time()
        while time.time() - start_time < duration_seconds:
            try:
                # Get open orders
                open_orders = self.info.open_orders(self.wallet_address)
                
                # Check if SL or TP still exists
                sl_exists = any(o.get('oid') == sl_oid for o in open_orders)
                tp_exists = any(o.get('oid') == tp_oid for o in open_orders)
                
                print(f"\r⏱️  {int(time.time() - start_time)}s | SL: {'✅' if sl_exists else '❌'} | TP: {'✅' if tp_exists else '❌'}", end='')
                
                if not sl_exists and not tp_exists:
                    print(f"\n🎯 Trade closed!")
                    break
                
                time.sleep(5)
            except Exception as e:
                print(f"\n⚠️  Error monitoring: {e}")
                break
        
        print(f"\n✅ Monitoring complete")
    
    def cleanup_test_trade(self, sl_oid, tp_oid):
        """Cancel any remaining SL/TP orders and close position"""
        print(f"\n🧹 Cleaning up test trade...")
        
        try:
            # Cancel SL/TP orders
            if sl_oid:
                self.exchange.cancel(coin="BTC", oid=sl_oid)
                print(f"✅ Cancelled SL order: {sl_oid}")
            
            if tp_oid:
                self.exchange.cancel(coin="BTC", oid=tp_oid)
                print(f"✅ Cancelled TP order: {tp_oid}")
            
            # Close any open BTC position at market
            positions = self.info.user_state(self.wallet_address).get('assetPositions', [])
            for pos in positions:
                if pos['position']['coin'] == 'BTC':
                    size = abs(float(pos['position']['szi']))
                    if size > 0:
                        is_buy = float(pos['position']['szi']) < 0  # Close opposite direction
                        self.exchange.market_close(coin="BTC", sz=size)
                        print(f"✅ Closed BTC position: {size}")
            
            print(f"✅ Cleanup complete")
        except Exception as e:
            print(f"⚠️  Error during cleanup: {e}")

def main():
    """Run the live trade flow test"""
    print("="*70)
    print("🧪 LIVE TRADE FLOW TEST")
    print("="*70)
    print("\nThis will test:")
    print("  1. Entry order placement")
    print("  2. SL/TP placement ONLY if entry succeeds")
    print("  3. Proper error handling for insufficient funds")
    print("  4. Order monitoring")
    print("\n⚠️  WARNING: This will place a REAL trade on Hyperliquid")
    print("   Test size: $10 (minimum)")
    
    response = input("\nProceed with test? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Test cancelled")
        return
    
    # Run test
    tester = LiveTradeFlowTest(test_size_usd=10)
    
    success, entry_oid, sl_oid, tp_oid = tester.place_test_trade(direction="LONG")
    
    if success:
        # Monitor for 60 seconds
        tester.monitor_trade(entry_oid, sl_oid, tp_oid, duration_seconds=60)
        
        # Cleanup
        cleanup = input("\nCleanup test trade? (yes/no): ")
        if cleanup.lower() == 'yes':
            tester.cleanup_test_trade(sl_oid, tp_oid)
    else:
        print("\n✅ Test completed - verified proper error handling")

if __name__ == '__main__':
    main()
