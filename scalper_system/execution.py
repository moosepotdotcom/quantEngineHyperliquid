"""
⚔️ EXECUTION MODULE
Handles order placement via Official SDK.
"""
import logging
import time
from scalper_system import config

# Import the existing trader class we verified earlier
import sys
sys.path.append('..')
try:
    from hyperliquid_live_trader import HyperliquidTrader
except ImportError:
    HyperliquidTrader = None

logger = logging.getLogger("EXEC")

class OrderManager:
    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        self.trader = None
        
        if not dry_run:
            # Inject credentials from config into ENV for the legacy trader class
            import os
            if config.WALLET_ADDRESS:
                os.environ['HYPERLIQUID_WALLET_ADDRESS'] = config.WALLET_ADDRESS
            if config.PRIVATE_KEY:
                os.environ['HYPERLIQUID_API_SECRET'] = config.PRIVATE_KEY
                
            if HyperliquidTrader:
                try:
                    self.trader = HyperliquidTrader(testnet=False)
                    logger.info("✅ Execution Connected (Mainnet)")
                except Exception as e:
                    logger.error(f"❌ Execution Connect Failed: {e}")
                    self.dry_run = True # Fallback
            else:
                logger.error("❌ SDK not found, falling back to Dry Run")
                self.dry_run = True
                
    def execute(self, signal):
        """Execute a signal from the Strategy Engine"""
        
        if self.dry_run:
            logger.info(f"⚔️ [DRY RUN] Executing {signal['side']} @ {signal['price']}")
            return True
            
        if not self.trader:
            logger.error("❌ No Execution Engine connected")
            return False
            
        try:
            logger.info(f"⚔️ [LIVE] Sending Order: {signal['side']}")
            
            # Map signal to trader format
            # Strategy says 'BUY' (Long), Trader expects 'LONG' direction
            # Strategy says 'SELL' (Short), Trader expects 'SHORT' direction
            direction = 'LONG' if signal['side'] == 'BUY' else 'SHORT'
            
            # Construct signal dict for the existing trader class
            trade_signal = {
                'price': signal['price'],
                'direction': direction,
                'model': 'V3_SYSTEM',
                'confidence': signal.get('confidence', 0.5)
            }
            
            return self.trader.execute_signal(trade_signal)
            
        except Exception as e:
            logger.error(f"Execution Error: {e}")
            return False
