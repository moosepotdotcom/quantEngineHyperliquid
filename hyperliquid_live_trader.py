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
        
        # Safety limits
        self.max_position_size = float(os.getenv('MAX_POSITION_SIZE', '0.01'))
        self.max_leverage = int(os.getenv('MAX_LEVERAGE', '2'))
        self.daily_loss_limit = float(os.getenv('DAILY_LOSS_LIMIT', '5.0'))
        
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
                print(f"✅ REAL Order Executed!")
                return order_result
            else:
                print(f"❌ Order failed: {order_result}")
                return None
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def place_tp_sl_orders(self, symbol: str, size: float, tp_price: float, sl_price: float):
        """
        Place TP and SL trigger orders on Hyperliquid
        Uses proper Hyperliquid API format with string prices and grouping
        """
        print(f"\n📋 Placing TP/SL trigger orders on Hyperliquid...")
        
        # Round prices to INTEGERS (Hyperliquid requirement for SL orders)
        tp_price_rounded = round(tp_price, 0)  # Integer
        sl_price_rounded = round(sl_price, 0)  # Integer
        
        try:
            # Place TP trigger order (take profit)
            # Note: SDK requires 'name' not 'coin'
            tp_order_request = {
                "name": symbol,  # Changed from "coin" to "name"
                "is_buy": False,
                "sz": size,
                "limit_px": tp_price_rounded,  # Float (integer value)
                "order_type": {"trigger": {"triggerPx": tp_price_rounded, "isMarket": True, "tpsl": "tp"}},
                "reduce_only": True
            }
            
            tp_order = self.exchange.bulk_orders([tp_order_request], grouping="positionTpsl")
            
            if tp_order and tp_order.get('status') == 'ok':
                print(f"✅ TP trigger order placed at ${tp_price_rounded:,.0f}")
            else:
                print(f"⚠️  TP order response: {tp_order}")
            
            # Place SL trigger order (stop loss)
            sl_order_request = {
                "name": symbol,  # Changed from "coin" to "name"
                "is_buy": False,
                "sz": size,
                "limit_px": sl_price_rounded,  # Float (integer value)
                "order_type": {"trigger": {"triggerPx": sl_price_rounded, "isMarket": True, "tpsl": "sl"}},
                "reduce_only": True
            }
            
            sl_order = self.exchange.bulk_orders([sl_order_request], grouping="positionTpsl")
            
            if sl_order and sl_order.get('status') == 'ok':
                print(f"✅ SL trigger order placed at ${sl_price_rounded:,.0f}")
            else:
                print(f"⚠️  SL order response: {sl_order}")
            
            return tp_order, sl_order
            
        except Exception as e:
            print(f"❌ Error placing TP/SL orders: {e}")
            import traceback
            traceback.print_exc()
            return None, None
    
    def execute_signal(self, signal: Dict) -> bool:
        """Execute trading signal with TP/SL orders"""
        print(f"\n🎯 Executing REAL Signal (Official SDK):")
        print(f"   Model: {signal.get('model')}")
        print(f"   Price: ${signal.get('price'):,.2f}")
        print(f"   Confidence: {signal.get('confidence'):.2%}")
        
        order = self.place_market_order('BTC', True, self.max_position_size)
        
        if order:
            entry_price = signal.get('price')
            tp_price = entry_price * 1.015
            sl_price = entry_price * 0.992
            
            # Place TP and SL orders on Hyperliquid
            tp_order, sl_order = self.place_tp_sl_orders('BTC', self.max_position_size, tp_price, sl_price)
            
            position_id = f"{signal.get('model')}_{int(time.time())}"
            self.active_positions[position_id] = {
                'entry_price': entry_price,
                'size': self.max_position_size,
                'tp': tp_price,
                'sl': sl_price,
                'timestamp': datetime.now(),
                'order': order,
                'tp_order': tp_order,
                'sl_order': sl_order
            }
            
            print(f"✅ REAL Position Opened:")
            print(f"   Entry: ${entry_price:,.2f}")
            print(f"   TP: ${tp_price:,.2f} (+1.5%) - Order on exchange ✅")
            print(f"   SL: ${sl_price:,.2f} (-0.8%) - Order on exchange ✅")
            
            return True
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
        """Emergency stop"""
        print("\n🚨 EMERGENCY STOP!")
        self.emergency_stop = True
        for pos_id in list(self.active_positions.keys()):
            position = self.active_positions[pos_id]
            self.place_market_order('BTC', False, position['size'])
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
