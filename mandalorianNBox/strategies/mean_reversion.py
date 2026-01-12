import backtrader as bt

class MeanReversionStrategy(bt.Strategy):
    """
    Mean Reversion Strategy
    Buys when price deviates significantly below SMA (Lower Band).
    Sells when price deviates significantly above SMA (Upper Band).
    """
    params = (
        ('sma_period', 20),
        ('deviation', 2.0),
        ('stop_loss_pct', 2.0),
    )
    
    def __init__(self):
        self.sma = bt.ind.SMA(period=self.params.sma_period)
        self.std = bt.ind.StandardDeviation(self.data.close, period=self.params.sma_period)
        
    def next(self):
        if len(self) < self.params.sma_period:
            return

        upper_band = self.sma[0] + (self.std[0] * self.params.deviation)
        lower_band = self.sma[0] - (self.std[0] * self.params.deviation)
        
        # Stop Loss Check
        if self.position:
            if self.position.size > 0 and self.data.close[0] < self.position.price * (1 - self.params.stop_loss_pct/100):
                self.close()
            elif self.position.size < 0 and self.data.close[0] > self.position.price * (1 + self.params.stop_loss_pct/100):
                self.close()
        
        # Entry Logic
        if not self.position:
            if self.data.close[0] < lower_band:  # Oversold
                self.buy()
            elif self.data.close[0] > upper_band:  # Overbought
                self.sell()
        else:
            # Exit Logic (Return to Mean)
            if self.position.size > 0 and self.data.close[0] >= self.sma[0]:
                self.close()
            elif self.position.size < 0 and self.data.close[0] <= self.sma[0]:
                self.close()
