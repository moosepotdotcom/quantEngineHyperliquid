
from typing import Dict, Any, Optional
import pandas as pd
from core.base_engine import BaseModelEngine
from model_engines.mtf_scalper_v2.logic import MLScalperV2Logic

class MTFScalperV2Engine(BaseModelEngine):
    def __init__(self):
        super().__init__("MTF Scalper V2")
        self.logic = None

    def initialize(self) -> bool:
        try:
            self.logic = MLScalperV2Logic()
            return True
        except Exception as e:
            print(f"   ❌ Failed to init V2 Logic: {e}")
            return False

    def get_required_timeframes(self) -> list:
        return ['5m', '15m', '30m']

    def analyze(self, data: Dict[str, pd.DataFrame]) -> Optional[Dict[str, Any]]:
        if not self.logic:
            return None
            
        if '5m' not in data or '15m' not in data or '30m' not in data:
            return None
            
        return self.logic.analyze(data['5m'], data['15m'], data['30m'])
