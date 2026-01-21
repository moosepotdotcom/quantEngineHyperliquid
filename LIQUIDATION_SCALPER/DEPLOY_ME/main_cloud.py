import time
import logging
import os
from hyperliquid.info import Info
from hyperliquid.utils import constants

# STRATEGY CONFIG
MOMENTUM_THRESHOLD_VOL = 500000.0  # V2 Config
TP_PCT = 0.002
SL_PCT = 0.001
MIN_BODY_PCT = 0.0003  # 0.03% Min Body for Breakout
LEVERAGE = 400
SIZE_BTC = 0.5  # Exness Paper Size

# LOGGING
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("CLOUD_SCALPER")

class CloudScalper:
    def __init__(self):
        self.info = Info(constants.MAINNET_API_URL, skip_ws=False)
        self.position = None
        self.balance = 1000.0  # Paper Tracking
        
        # State
        self.candle = {'vol': 0, 'open': 0, 'close': 0, 'high': 0, 'low': 999999}
        self.last_minute = -1
        
        logger.info("☁️  CLOUD SCALPER INITIALIZED")
        logger.info(f"Strategy: V2 Momentum | Thresh: ${MOMENTUM_THRESHOLD_VOL:,.0f}")
        logger.info(f"Settings: Lev {LEVERAGE}x | Size {SIZE_BTC} BTC")

    def on_trade(self, trade):
        # Trade: {'coin': 'BTC', 'side': 'B', 'px': '95000.0', 'sz': '0.1', ...}
        px = float(trade['px'])
        sz = float(trade['sz'])
        val = px * sz
        side = trade['side']
        
        # 1. Update Candle
        import datetime
        now_min = datetime.datetime.now().minute
        
        if now_min != self.last_minute:
            # Candle Close Logic
            if self.last_minute != -1:
                # Check Momentum
                if self.candle['vol'] > MOMENTUM_THRESHOLD_VOL:
                    # CHOP FILTER
                    body_pct = abs(self.candle['close'] - self.candle['open']) / self.candle['open'] if self.candle['open'] != 0 else 0
                    if body_pct < MIN_BODY_PCT:
                        logger.info(f"🚫 CHOP FILTER: High Vol but Small Body ({body_pct*100:.4f}%) - SKIPPING")
                    else:
                        direction = "BUY" if self.candle['close'] > self.candle['open'] else "SELL"
                        logger.info(f"⚡ MOMENTUM SIGNAL: {direction} (Vol: ${self.candle['vol']:,.0f})")
                        self.execute_trade(direction, px)
            
            # Reset
            self.candle = {'vol': 0, 'open': px, 'close': px, 'high': px, 'low': px}
            self.last_minute = now_min
            
        # Accumulate
        if self.candle['open'] == 0:
            self.candle['open'] = px
        self.candle['vol'] += val
        self.candle['close'] = px
        self.candle['high'] = max(self.candle['high'], px)
        self.candle['low'] = min(self.candle['low'], px)
        
        # 2. Monitor Position
        if self.position:
            entry = self.position['entry']
            pside = self.position['side']
            
            pnl_pct = (px - entry)/entry if pside == "BUY" else (entry - px)/entry
            
            if pnl_pct >= TP_PCT:
                self.close_position(px, "TP")
            elif pnl_pct <= -SL_PCT:
                self.close_position(px, "SL")

    def execute_trade(self, side, price):
        if self.position: return
        
        logger.info(f"🚀 OPEN {side} @ {price} ({SIZE_BTC} BTC)")
        self.position = {'side': side, 'entry': price, 'size': SIZE_BTC}
        
    def close_position(self, price, reason):
        if not self.position: return
        
        entry = self.position['entry']
        # PnL = Delta * Size (BTC)
        pnl = (price - entry) * SIZE_BTC if self.position['side'] == "BUY" else (entry - price) * SIZE_BTC
        
        self.balance += pnl
        
        logger.info(f"💰 {reason} CLOSED @ {price} | PnL: ${pnl:.2f} | Bal: ${self.balance:.2f}")
        self.position = None

    def run(self):
        logger.info("📡 Subscribing to BTC trades...")
        # Subscribe to trades
        def handler(msg):
            if 'data' in msg and msg['channel'] == 'trades':
                for t in msg['data']:
                    if t['coin'] == 'BTC':
                        self.on_trade(t)
                        
        self.info.subscribe({'type': 'trades', 'coin': 'BTC'}, handler)
        
        # Keep alive
        while True:
            time.sleep(1)

if __name__ == "__main__":
    bot = CloudScalper()
    bot.run()
