"""
📡 LIQUIDATION DATA STREAM
Robust WebSocket client for live trade/liquidation ingestion.
"""
import websocket
import json
import time
import threading
import logging
from datetime import datetime
from collections import deque
from scalper_system import config

logger = logging.getLogger("FEED")

class LiquidationStream:
    def __init__(self):
        self.ws = None
        self.running = False
        self.callbacks = []
        
        # State
        self.connected = False
        self.last_msg_time = datetime.now()
        
        # Aggregation Stats
        self.event_count = 0
        self.total_volume = 0.0
        
    def add_callback(self, callback_func):
        """Register a function to call on new liquidation event"""
        self.callbacks.append(callback_func)
        
    def start(self):
        self.running = True
        # Run WS in separate thread
        self.thread = threading.Thread(target=self._run_ws, daemon=True)
        self.thread.start()
        logger.info("📡 Data Stream Started")
        
    def _run_ws(self):
        while self.running:
            try:
                # websocket.enableTrace(True) # Debug only
                self.ws = websocket.WebSocketApp(
                    config.WS_URL,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close
                )
                self.ws.run_forever()
                
                if self.running:
                    logger.warning("🔌 Connection lost. Reconnecting in 2s...")
                    time.sleep(2)
            except Exception as e:
                logger.error(f"WS Critical Error: {e}")
                time.sleep(5)
                
    def _on_open(self, ws):
        logger.info(f"🔗 Connected to {config.WS_URL}")
        self.connected = True
        msg = {
            "method": "subscribe",
            "subscription": {"type": "trades", "coin": config.SYMBOL}
        }
        ws.send(json.dumps(msg))
        
    def _on_message(self, ws, message):
        try:
            self.last_msg_time = datetime.now()
            data = json.loads(message)
            channel = data.get('channel')
            
            if channel == 'trades':
                trades = data.get('data', [])
                for trade in trades:
                    # Filter for liquidations (using multiple heuristics from research)
                    # 1. Explicit 'liquidation' field
                    # 2. Side deduction (optional, stick to strict for now)
                    
                    if 'liquidation' in trade:
                        self._process_event(trade)
                        
        except Exception as e:
            logger.error(f"Message Error: {e}")
            
    def _process_event(self, trade):
        try:
            # Parse
            price = float(trade['px'])
            size = float(trade['sz'])
            usd_val = price * size
            side = trade['side'] # 'B' or 'A'
            
            event = {
                'timestamp': datetime.now(),
                'symbol': config.SYMBOL,
                'type': 'SHORT' if side == 'B' else 'LONG',
                'price': price,
                'size': size,
                'usd': usd_val,
                'user': trade.get('users', [''])[0]
            }
            
            # Stats
            self.event_count += 1
            self.total_volume += usd_val
            
            # Notify subscribers (Strategy)
            for cb in self.callbacks:
                cb(event)
                
        except Exception as e:
            logger.error(f"Process Error: {e}")

    def _on_error(self, ws, error):
        logger.error(f"WS Error: {error}")
        
    def _on_close(self, ws, *args):
        self.connected = False
        logger.info("🔌 WS Closed")
