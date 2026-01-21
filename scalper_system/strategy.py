"""
🧠 STRATEGY ENGINE
Processes incoming liquidation events and generates signals.
"""
import logging
from collections import deque
from datetime import datetime, timedelta
from scalper_system import config

logger = logging.getLogger("STRAT")

class StrategyEngine:
    def __init__(self, execution_callback):
        self.execution_callback = execution_callback
        
        # State
        self.short_liqs = deque()
        self.long_liqs = deque()
        self.last_signal_time = datetime.min
        
    def on_event(self, event):
        """Called by Feed when new liquidation arrives"""
        now = datetime.now()
        
        # 1. Log Event
        logger.info(f"💦 {event['type']} Liq: ${event['usd']:,.0f} @ {event['price']}")
        
        # 2. Store
        if event['type'] == 'SHORT':
            self.short_liqs.append((now, event['usd']))
        else:
            self.long_liqs.append((now, event['usd']))
            
        # 3. Clean
        self._cleanup(now)
        
        # 4. Check Signals
        self._check_reversal(event['price'], now)
        
    def _cleanup(self, now):
        cutoff = now - timedelta(seconds=config.LIQ_WINDOW_SECONDS)
        while self.short_liqs and self.short_liqs[0][0] < cutoff:
            self.short_liqs.popleft()
        while self.long_liqs and self.long_liqs[0][0] < cutoff:
            self.long_liqs.popleft()
            
    def _check_reversal(self, current_price, now):
        # Cooldown
        if (now - self.last_signal_time).total_seconds() < config.COOLDOWN_SECONDS:
            return
            
        # Sums
        total_short = sum(x[1] for x in self.short_liqs)
        total_long = sum(x[1] for x in self.long_liqs)
        
        signal = None
        
        # Rule 1: Long Liq Reversal (Oversold -> Buy)
        if total_long > config.LIQ_THRESHOLD_USD:
            # TODO: Add RSI check here in future
            signal = {
                'side': 'BUY',
                'sl_side': 'SELL',
                'price': current_price,
                'reason': f"Long Pressure ${total_long:,.0f} > ${config.LIQ_THRESHOLD_USD}",
                'confidence': 0.8
            }
            
        # Rule 2: Short Liq Reversal (Overbought -> Sell)
        elif total_short > config.LIQ_THRESHOLD_USD:
            signal = {
                'side': 'SELL',
                'sl_side': 'BUY',
                'price': current_price,
                'reason': f"Short Pressure ${total_short:,.0f} > ${config.LIQ_THRESHOLD_USD}",
                'confidence': 0.8
            }
            
        if signal:
            logger.info(f"🚨 SIGNAL: {signal['side']} | {signal['reason']}")
            self.last_signal_time = now
            self.execution_callback(signal)
