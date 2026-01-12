
import asyncio
import json
import threading
import time
import selectors
from websockets import connect
from utils.logger import log_liquidation

class LiquidationMonitor(threading.Thread):
    def __init__(self, threshold_usd=50000):
        super().__init__()
        self.uri = 'wss://fstream.binance.com/ws/!forceOrder@arr'
        self.threshold_usd = threshold_usd
        self.running = True
        self.latest_liquidation = None
        self.daemon = True # Auto-kill when main program exits

    def run(self):
        """Entry point for the thread"""
        selector = selectors.SelectSelector()
        loop = asyncio.SelectorEventLoop(selector)
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._monitor())
        finally:
            loop.close()

    async def _monitor(self):
        """Async Websocket Loop"""
        print(f"🌊 Starting Liquidation Monitor (Threshold: ${self.threshold_usd:,.0f})...")
        while self.running:
            try:
                async with connect(self.uri) as websocket:
                    while self.running:
                        msg = await websocket.recv()
                        data = json.loads(msg)['o']
                        
                        symbol = data['s'].replace('USDT', '')
                        side = data['S'] # SELL means Long Liquidated (Sold into market)
                        qty = float(data['z'])
                        price = float(data['p'])
                        usd_size = qty * price
                        
                        if usd_size >= self.threshold_usd:
                            # SELL event = LONG Liquidation
                            # BUY event = SHORT Liquidation
                            rekt_side = "LONG" if side == "SELL" else "SHORT"
                            
                            self.latest_liquidation = {
                                'symbol': symbol,
                                'side': rekt_side,
                                'amount': usd_size,
                                'price': price,
                                'time': time.time()
                            }
                            
                            # Log significant events immediately
                            log_liquidation(symbol, rekt_side, usd_size, price)
                            
            except Exception as e:
                # print(f"⚠️ Liq Monitor Error: {e}")
                await asyncio.sleep(5) # Reconnect delay

    def get_bias(self):
        """Returns current bias from liquidations: 1 (Shorts Squeezed), -1 (Longs Cascaded), 0 (Neutral)"""
        if not self.latest_liquidation:
            return 0
        
        # Liquidations are fleeting, only consider last 2 minutes
        if time.time() - self.latest_liquidation['time'] < 120:
            return 1 if self.latest_liquidation['side'] == 'SHORT' else -1
        return 0

    def stop(self):
        self.running = False
