
from typing import Dict, Any, Optional
import pandas as pd
from core.base_engine import BaseModelEngine
from model_engines.winner_hunter_1h.logic import WinnerHunter1HLogic

class WinnerHunter1HEngine(BaseModelEngine):
    def __init__(self):
        super().__init__("Winner Hunter (1H)")
        self.logic = None

    def initialize(self) -> bool:
        try:
            self.logic = WinnerHunter1HLogic()
            return True
        except Exception as e:
            print(f"   ❌ Failed to init WH Logic: {e}")
            return False

    def get_required_timeframes(self) -> list:
        # WH uses 1H primarily, but can use 5m/15m for context
        return ['1h', '5m', '15m']

    def analyze(self, data: Dict[str, pd.DataFrame]) -> Optional[Dict[str, Any]]:
        if not self.logic:
            return None
            
        if '1h' not in data:
            return None
            
        return self.logic.analyze(
            data['1h'], 
            data.get('5m'), # Context optional
            data.get('15m') # Context optional
        )
