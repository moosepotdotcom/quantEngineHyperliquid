
import asyncio
import json
import threading
import time
import selectors
from websockets import connect
from utils.logger import log_to_journal

class WhaleWatcher(threading.Thread):
    def __init__(self, threshold_usd=500000):
        super().__init__()
        self.uri = 'wss://stream.binance.com:9443/ws/btcusdt@aggTrade'
        self.threshold_usd = threshold_usd
        self.running = True
        self.latest_whale = None
        self.daemon = True 

    def run(self):
        selector = selectors.SelectSelector()
        loop = asyncio.SelectorEventLoop(selector)
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._monitor())
        finally:
            loop.close()

    async def _monitor(self):
        print(f"🐋 Starting Whale Watcher (Threshold: ${self.threshold_usd:,.0f})...")
        while self.running:
            try:
                async with connect(self.uri) as websocket:
                    while self.running:
                        msg = await websocket.recv()
                        data = json.loads(msg)
                        
                        # Binance AggTrade Format
                        # p = Price, q = Quantity, m = is_buyer_maker (True=Sell, False=Buy)
                        price = float(data['p'])
                        qty = float(data['q'])
                        is_sell = data['m'] 
                        usd_size = price * qty
                        
                        if usd_size >= self.threshold_usd:
                            side = "SELL" if is_sell else "BUY"
                            emoji = "🐋"
                            
                            self.latest_whale = {
                                'side': side,
                                'amount': usd_size,
                                'price': price,
                                'time': time.time()
                            }
                            
                            # Log immediately
                            title = "WHALE ALERT"
                            details = f"- **Side**: {side}\n- **Amount**: ${usd_size:,.0f}\n- **Price**: ${price:.2f}"
                            log_to_journal(title, details, emoji)
                            
            except Exception as e:
                await asyncio.sleep(5)

    def stop(self):
        self.running = False
