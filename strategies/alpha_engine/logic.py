
import time
from datetime import datetime

class AlphaEngine:
    """
    Alpha Strategy Engine (Phase 4)
    Handles high-frequency logic for Whale Walls and Liquidity Pops.
    Run parallel strategies: 'The Anvil' and 'The Battering Ram'.
    """
    
    def __init__(self):
        self.strategies = {
            'ANVIL': {
                'enabled': False, 
                'desc': 'Wall Front-Running',
                'threshold': 500000  # Default $500k
            },
            'RAM': {
                'enabled': False, 
                'desc': 'Pop Momentum Breakout',
                'threshold': 50000   # Default $50k
            }
        }
        print("🚀 Alpha Engine Initialized")

    def toggle_strategy(self, strategy_id, state: bool):
        if strategy_id in self.strategies:
            self.strategies[strategy_id]['enabled'] = state
            print(f"⚙️ Alpha Strategy {strategy_id} set to {state}")
            return True
        return False

    def update_setting(self, strategy_id, val):
        if strategy_id in self.strategies:
            self.strategies[strategy_id]['threshold'] = float(val)
            print(f"⚙️ Alpha Setting {strategy_id} threshold -> ${val}")
            return True
        return False

    def evaluate(self, market_data):
        """
        Evaluate all enabled strategies in parallel.
        market_data: {
            'l2_walls': [],   # from get_whale_walls
            'l2_pops': [],    # from get_whale_walls
            'current_price': float
        }
        Returns: List of Signal objects
        """
        signals = []
        
        if self.strategies['ANVIL']['enabled']:
            s = self._avail_strategy(market_data)
            if s: signals.append(s)
            
        if self.strategies['RAM']['enabled']:
            s = self._ram_strategy(market_data)
            if s: signals.append(s)
            
        return signals

    def _avail_strategy(self, data):
        """
        Strategy A: 'The Anvil'
        Logic: If price is close to a HUGE Buy Wall, Front-run it.
        """
        walls = data.get('l2_walls', [])
        current_price = data.get('current_price', 0)
        threshold = self.strategies['ANVIL']['threshold']
        
        if current_price == 0: return None
        
        # Filter for BUY Walls > threshold
        buy_walls = [w for w in walls if w['side'] == 'BID' and w['val'] > threshold]
        
        for wall in buy_walls:
            wall_px = wall['px']
            # Distance check: Within 0.5%
            dist_pct = (current_price - wall_px) / current_price
            
            if 0 < dist_pct < 0.005: 
                # TRIGGER
                return {
                    'strategy_id': 'ANVIL',
                    'direction': 'LONG',
                    'price': wall_px + 10, # Front-run by $10
                    'limit': True,
                    'confidence': 0.95,
                    'reason': f"Front-running ${wall['val']/1000:.0f}k Wall (>{threshold/1000:.0f}k)"
                }
        return None

    def _ram_strategy(self, data):
        """
        Strategy B: 'The Battering Ram'
        Logic: If a large BID POP appears, ride the momentum.
        """
        pops = data.get('l2_pops', [])
        threshold = self.strategies['RAM']['threshold']
        
        # Filter for BID POPS > threshold
        # These represent eager buying energy
        bid_pops = [p for p in pops if p['side'] == 'BID' and p['val'] > threshold]
        
        if bid_pops:
            # Get the largest active pop
            best_pop = bid_pops[0]
            
            return {
                'strategy_id': 'RAM',
                'direction': 'LONG',
                'price': best_pop['px'],
                'limit': False, # Market Order for speed
                'confidence': 0.85,
                'reason': f"Chasing ${best_pop['val']/1000:.0f}k Bid Pop (>{threshold/1000:.0f}k)"
            }
            
        return None
