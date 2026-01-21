
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class Signal:
    """
    Standardized Signal Object.
    
    Types:
    - DIRECTIONAL: Buy/Sell at market or limit.
    - GRID: Place a range of orders.
    - NEUTRAL: Do nothing / Close positions.
    """
    signal_type: str # 'LONG', 'SHORT', 'GRID', 'NEUTRAL'
    confidence: float # 0.0 to 1.0
    
    # Directional Fields
    entry_price: Optional[float] = None
    tp_price: Optional[float] = None
    sl_price: Optional[float] = None
    
    # Grid Fields
    grid_buy_level: Optional[float] = None
    grid_sell_level: Optional[float] = None
    
    # Metadata (Strategy Name, Reason, Features)
    metadata: Optional[Dict[str, Any]] = None

class BaseEngine:
    """Abstract Base Class for all Strategy Engines."""
    
    def initialize(self):
        """Load weights, configs, etc."""
        raise NotImplementedError
        
    def analyze(self, df) -> Signal:
        """
        Input: Pandas DataFrame (OHLCV + optional cols)
        Output: Signal object
        """
        raise NotImplementedError
