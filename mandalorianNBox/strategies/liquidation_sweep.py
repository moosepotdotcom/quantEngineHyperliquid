import backtrader as bt
import logging

logger = logging.getLogger(__name__)

class LiquidationSweepStrategy(bt.Strategy):
    """
    Liquidation Sweep Strategy
    Capitalizes on market exhaustion following large liquidation events.
    
    Logic:
    - High Long Liquidations -> Potential Bottom -> BUY
    - High Short Liquidations -> Potential Top -> SELL
    """
    params = (
        ('liq_threshold', 100000),      # Threshold for cumulative liquidations
        ('lookback', 5),               # Bars to look back for liq events
        ('atr_period', 14),
        ('atr_multiplier', 2.0),
        ('take_profit_pct', 2.0),
    )

    def __init__(self):
        self.atr = bt.ind.ATR(period=self.params.atr_period)
        
        # We'll use custom lines or external data feed for liquidations
        # For now, we'll expose variables that the trading_agent can update
        self.long_liq_volume = 0
        self.short_liq_volume = 0
        
        self.order = None
        self.buy_price = None
        self.stop_price = None
        self.tp_price = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                logger.info(f"BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm {order.executed.comm:.2f}")
                self.buy_price = order.executed.price
            else:
                logger.info(f"SELL EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm {order.executed.comm:.2f}")

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            logger.warning('Order Canceled/Margin/Rejected')

        self.order = None

    def next(self):
        if self.order:
            return

        # Strategy Logic:
        # Check for exhaustion spikes (In live, these come from the liquidation_agent)
        # In backtest, we might use Volume/Volatility proxies if no liq_data exists
        
        if not self.position:
            # Check for Long Liquidation Sweep (Potential Bottom)
            if self.long_liq_volume >= self.params.liq_threshold:
                logger.info(f"🔥 LIQUIDATION SWEEP DETECTED: ${self.long_liq_volume:,.0f} Longs Rekt. Buying Bottom.")
                self.order = self.buy()
                self.tp_price = self.data.close[0] * (1 + self.params.take_profit_pct / 100.0)
                self.stop_price = self.data.close[0] - (self.atr[0] * self.params.atr_multiplier)
            
            # Check for Short Liquidation Sweep (Potential Top)
            elif self.short_liq_volume >= self.params.liq_threshold:
                logger.info(f"🚀 SHORT SQUEEZE DETECTED: ${self.short_liq_volume:,.0f} Shorts Rekt. Selling Top.")
                self.order = self.sell()
                self.tp_price = self.data.close[0] * (1 - self.params.take_profit_pct / 100.0)
                self.stop_price = self.data.close[0] + (self.atr[0] * self.params.atr_multiplier)

        else:
            # Exit Logic
            if self.position.size > 0: # Long
                if self.data.close[0] >= self.tp_price:
                    self.close(msg="Take Profit")
                elif self.data.close[0] <= self.stop_price:
                    self.close(msg="Stop Loss")
            else: # Short
                if self.data.close[0] <= self.tp_price:
                    self.close(msg="Take Profit")
                elif self.data.close[0] >= self.stop_price:
                    self.close(msg="Stop Loss")
                    
        # Decay volume slowly if not filled (Simulates a "memory" of a spike)
        self.long_liq_volume *= 0.5
        self.short_liq_volume *= 0.5
        
    def update_liquidations(self, long_vol, short_vol):
        """Called by the trading agent to feed live data"""
        self.long_liq_volume += long_vol
        self.short_liq_volume += short_vol
