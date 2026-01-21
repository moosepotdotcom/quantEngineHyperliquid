
from core.base_engine import BaseModelEngine
from .logic import MTFScalperV3Logic

class MTFScalperV3Engine(BaseModelEngine):
    def __init__(self, config=None):
        super().__init__("MTF Scalper V3")
        self.config = config or {}
        self.logic = MTFScalperV3Logic()
        
    def initialize(self):
        print(f"   🚀 Initializing {self.name}...")
        # Logic already loads model in init
        return True
        
    def analyze(self, market_data):
        # Router passes { '5m': df, '15m': df, '30m': df }
        # Logic expects explicit args
        if '5m' not in market_data: return None
        
        return self.logic.analyze(
            market_data.get('5m'),
            market_data.get('15m'),
            market_data.get('30m')
        )
        
    def on_trade_complete(self, trade_result):
        pass
