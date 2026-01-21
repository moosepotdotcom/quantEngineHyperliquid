# Stub functions for missing monitoring modules
class DummyLogger:
    def log_prediction(self, *args, **kwargs):
        pass

class DummyTracker:
    pass

class DummyMonitor:
    def add_trade(self, *args, **kwargs):
        pass
    def check_exits(self):
        pass
    def display_status(self):
        pass

def get_logger():
    return DummyLogger()

def get_tracker():
    return DummyTracker()

def get_monitor(logger):
    return DummyMonitor()

def get_market_regime(df):
    return "NEUTRAL"

def should_trade(direction, regime):
    return True, "OK"

def get_regime_info(df):
    return {
        'regime': 'NEUTRAL',
        'strength': 50.0,
        'ema_20': 95000,
        'ema_50': 95000,
        'price_vs_ema20': 0.0
    }
