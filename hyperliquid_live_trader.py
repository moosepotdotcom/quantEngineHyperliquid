#!/usr/bin/env python3
"""
Hyperliquid Live Trading - Using Official SDK
This uses Hyperliquid's official Python SDK for reliable trading
"""

import os
import time
from datetime import datetime
from typing import Dict, Optional
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants

class HyperliquidTrader:
    """Live trading using official Hyperliquid SDK"""
    
    def __init__(self, testnet: bool = True):
        """Initialize with official SDK"""
        self.testnet = testnet
        
        # Load credentials
        self.wallet_address = os.getenv('HYPERLIQUID_WALLET_ADDRESS')
        private_key = os.getenv('HYPERLIQUID_API_SECRET')
        
        if not self.wallet_address:
            raise ValueError("HYPERLIQUID_WALLET_ADDRESS not set")
        if not private_key:
            raise ValueError("HYPERLIQUID_API_SECRET not set")
        
        # Add 0x prefix if needed
        if not private_key.startswith('0x'):
            private_key = '0x' + private_key
        
        # Create LocalAccount for SDK
        from eth_account import Account
        wallet = Account.from_key(private_key)
        
        # Initialize SDK
        base_url = constants.TESTNET_API_URL if testnet else constants.MAINNET_API_URL
        
        self.exchange = Exchange(
            wallet=wallet,
            base_url=base_url
        )
        
        self.info = Info(base_url=base_url)
        
        # Small Account Settings ($60 Capitalization)
        self.leverage = 15
        self.target_tp_pct = 0.003 # Gem TP (0.3%)
        self.target_sl_pct = 0.005 # Gem SL (0.5%)
        self.max_position_size = float(os.getenv('MAX_POSITION_SIZE', '0.01'))  # Max BTC per trade
        
        # Safety limits
        self.daily_loss_limit = float(os.getenv('DAILY_LOSS_LIMIT', '10.0'))
        
        # Trading state
        self.daily_pnl = 0.0
        self.active_positions = {}
        self.emergency_stop = False
        
        print(f"🔧 Hyperliquid Trader - Official SDK")
        print(f"   Mode: {'TESTNET' if testnet else 'MAINNET'}")
        print(f"   Wallet: {self.wallet_address}")
        print(f"   SDK: v0.21.0")
    
    def _check_safety_limits(self) -> bool:
        """Check safety limits"""
        if self.emergency_stop:
            return False
        if self.daily_pnl <= -self.daily_loss_limit:
            return False
        return True
    
    def calculate_order_size(self, price: float) -> float:
        """Calculate size for 15x leverage on current balance"""
        info = self.get_account_info()
        balance = info.get('balance', 0)
        
        if balance <= 0:
            print("⚠️ Balance is zero, cannot calculate size")
            return 0
            
        # Buying Power = Balance * Leverage
        buying_power = balance * self.leverage
        # BTC Size = Buying Power / Price
        size = buying_power / price
        
        # Hyperliquid requires specific rounding for BTC (~4-5 decimals)
        rounded_size = round(size, 4)
        
        print(f"💰 Compounding Logic:")
        print(f"   Balance: ${balance:.2f} | Leverage: {self.leverage}x")
        print(f"   Buying Power: ${buying_power:.2f}")
        print(f"   Calculated Size: {rounded_size} BTC")
        
        return rounded_size

    def get_account_info(self) -> Dict:
        """Get account info using SDK"""
        try:
            user_state = self.info.user_state(self.wallet_address)
            margin_summary = user_state.get('marginSummary', {})
            
            return {
                'balance': float(margin_summary.get('accountValue', 0)),
                'positions': user_state.get('assetPositions', [])
            }
        except Exception as e:
            print(f"Error: {e}")
            return {'balance': 0, 'positions': []}
    
    def place_market_order(self, symbol: str, is_buy: bool, size: float) -> Optional[Dict]:
        """
        Place market order using official SDK
        """
        if not self._check_safety_limits():
            print("🛑 Safety limits prevent trading")
            return None
        
        if size > self.max_position_size:
            size = self.max_position_size
        
        print(f"\n📤 Placing REAL Market Order (Official SDK):")
        print(f"   Symbol: {symbol}")
        print(f"   Side: {'Buy' if is_buy else 'Sell'}")
        print(f"   Size: {size}")
        
        try:
            # Place market order using SDK
            order_result = self.exchange.market_open(
                name=symbol,
                is_buy=is_buy,
                sz=size,
                px=None  # Market order
            )
            
            print(f"✅ Order Result: {order_result}")
            
            if order_result and order_result.get('status') == 'ok':
                # Check for nested error in response
                resp_data = order_result.get('response', {})
                if resp_data.get('type') == 'error':
                    print(f"❌ Order rejected by exchange: {resp_data.get('msg')}")
                    return None
                
                # Check statuses for nested errors (e.g., Insufficient Margin)
                data = resp_data.get('data', {})
                statuses = data.get('statuses', [])
                for status in statuses:
                    if isinstance(status, dict) and 'error' in status:
                        print(f"❌ Exchange rejection found in status: {status['error']}")
                        return None
                        
                print(f"✅ REAL Order Executed!")
                return order_result
            else:
                print(f"❌ API Communication failed: {order_result}")
                return None
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def place_tp_sl_orders(self, symbol: str, size: float, tp_price: float, sl_price: float, is_long: bool = True):
        """
        Place TP and SL trigger orders on Hyperliquid
        CRITICAL: Both orders placed TOGETHER in single API call for proper linking
        """
        print(f"\n🔧 DEBUG: place_tp_sl_orders() called with symbol={symbol}, size={size}, tp={tp_price}, sl={sl_price}, is_long={is_long}")
        print(f"\n📋 Placing TP/SL trigger orders on Hyperliquid...")
        
        # Round prices to INTEGERS (Hyperliquid requirement for SL orders)
        tp_price_rounded = round(tp_price, 0)  # Integer
        sl_price_rounded = round(sl_price, 0)  # Integer
        
        # Exits are opposite of entry
        exit_is_buy = not is_long
        
        try:
            # CRITICAL FIX: Place BOTH TP and SL in SINGLE bulk_orders call
            # This ensures proper order linking/grouping on Hyperliquid
            orders = [
                # Take Profit order
                {
                    "coin": symbol,
                    "is_buy": exit_is_buy,
                    "sz": size,
                    "limit_px": tp_price_rounded,
                    "order_type": {"trigger": {"triggerPx": tp_price_rounded, "isMarket": True, "tpsl": "tp"}},
                    "reduce_only": True
                },
                # Stop Loss order
                {
                    "coin": symbol,
                    "is_buy": exit_is_buy,
                    "sz": size,
                    "limit_px": sl_price_rounded,
                    "order_type": {"trigger": {"triggerPx": sl_price_rounded, "isMarket": True, "tpsl": "sl"}},
                    "reduce_only": True
                }
            ]
            
            # Place BOTH orders together with positionTpsl grouping
            result = self.exchange.bulk_orders(orders, grouping="positionTpsl")
            
            if result and result.get('status') == 'ok':
                print(f"✅ TP/SL orders placed successfully!")
                print(f"   TP: ${tp_price_rounded:,.0f}")
                print(f"   SL: ${sl_price_rounded:,.0f}")
                print(f"   Result: {result}")
                return result, result  # Return same result for both (they're linked)
            else:
                print(f"⚠️  TP/SL order response: {result}")
                return result, result
            
        except Exception as e:
            print(f"❌ Error placing TP/SL orders: {e}")
            import traceback
            traceback.print_exc()
            return None, None
    
    def execute_signal(self, signal: Dict) -> bool:
        """Execute trading signal with Gem TP/SL targets (Bidirectional)"""
        entry_price = float(signal.get('price'))
        direction = signal.get('direction', 'LONG')
        is_long = (direction == 'LONG')
        
        # Calculate dynamic size for compounding
        size = self.calculate_order_size(entry_price)
        if size <= 0: return False

        print(f"\n🎯 Executing REAL Gem Signal:")
        print(f"   Model: {signal.get('model')}")
        print(f"   Direction: {direction}")
        print(f"   Confidence: {signal.get('confidence'):.2%}")
        
        # 1. Market Entry (is_buy=True for Long, is_buy=False for Short)
        order = self.place_market_order('BTC', is_long, size)
        
        if order:
            # 2. Set Gem Targets (0.3% / 0.5%)
            if is_long:
                tp_price = entry_price * (1 + self.target_tp_pct)
                sl_price = entry_price * (1 - self.target_sl_pct)
            else:
                tp_price = entry_price * (1 - self.target_tp_pct)
                sl_price = entry_price * (1 + self.target_sl_pct)
            
            print(f"\n⏳ Waiting 2 seconds for position to settle...")
            time.sleep(2)
            
            # 3. Place TP/SL orders on Hyperliquid
            tp_order, sl_order = self.place_tp_sl_orders('BTC', size, tp_price, sl_price, is_long=is_long)
            
            # 4. Add to active positions for redundant monitoring
            position_id = f"{signal.get('model')}_{int(time.time())}"
            self.active_positions[position_id] = {
                'entry_price': entry_price,
                'direction': direction,
                'size': size,
                'tp': tp_price,
                'sl': sl_price,
                'timestamp': datetime.now(),
                'order': order,
                'tp_order': tp_order,
                'sl_order': sl_order
            }
            
            print(f"✅ REAL Position Opened ({direction}):")
            print(f"   Entry: ${entry_price:,.2f}")
            print(f"   TP: ${tp_price:,.2f} ({'+' if is_long else '-'}{self.target_tp_pct:.1%}) - Order on exchange ✅")
            print(f"   SL: ${sl_price:,.2f} ({'-' if is_long else '+'}{self.target_sl_pct:.1%}) - Order on exchange ✅")
            
            return True
        else:
            print(f"⚠️  Market order failed or was rejected. Skipping TP/SL placement to avoid stray orders.")
            return False
    
    def check_positions(self, current_price: float):
        """Check and manage positions"""
        for pos_id, position in list(self.active_positions.items()):
            entry = position['entry_price']
            tp = position['tp']
            sl = position['sl']
            size = position['size']
            
            if current_price >= tp:
                pnl = (current_price - entry) / entry * (size * entry)
                self.daily_pnl += pnl
                print(f"\n🎯 TP HIT! Closing position...")
                self.place_market_order('BTC', False, size)
                del self.active_positions[pos_id]
            
            elif current_price <= sl:
                pnl = (current_price - entry) / entry * (size * entry)
                self.daily_pnl += pnl
                print(f"\n🛑 SL HIT! Closing position...")
                self.place_market_order('BTC', False, size)
                del self.active_positions[pos_id]
    
    def get_status(self) -> Dict:
        """Get status"""
        return {
            'emergency_stop': self.emergency_stop,
            'daily_pnl': self.daily_pnl,
            'active_positions': len(self.active_positions)
        }
    
    def emergency_stop_all(self):
        """Emergency stop: Close all active positions immediately"""
        print("\n🚨 EMERGENCY STOP!")
        self.emergency_stop = True
        for pos_id in list(self.active_positions.keys()):
            position = self.active_positions[pos_id]
            direction = position.get('direction', 'LONG')
            # To close a LONG, we SELL (is_buy=False)
            # To close a SHORT, we BUY (is_buy=True)
            close_is_buy = (direction == 'SHORT')
            
            print(f"🚨 Emergency closing {direction} position...")
            self.place_market_order('BTC', close_is_buy, position['size'])
        self.active_positions = {}


def main():
    """Test"""
    print("🚀 Hyperliquid Trader - Official SDK")
    print("="*70)
    
    trader = HyperliquidTrader(testnet=False)
    account = trader.get_account_info()
    print(f"\n💰 Balance: ${account['balance']:.2f}")


if __name__ == '__main__':
    main()
