#!/usr/bin/env python3
"""
🛡️ MANDALORIAN ENGINE - Backend State Manager
Tracks live trades, confidence scores, and provides data for dashboard
"""

import json
import os
from datetime import datetime
from typing import Optional, Dict, List

# Use absolute paths based on script location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPT_DIR, "trades", "engine_state.json")
TRADES_FILE = os.path.join(SCRIPT_DIR, "trades", "trade_history.json")

class MandalorianState:
    def __init__(self):
        self.state = {
            'mode': 'PAPER',
            'balance': 100000.0,
            'current_position': None,
            'last_signal': None,
            'thresholds': {
                'long': 0.45,  # 45% confidence required for LONG
                'short': 0.45  # 45% confidence required for SHORT
            },
            'shields': {
                'mandalorian': True,
                'ai_smart': True,
                'circuit_breaker': True
            },
            'circuit_breaker': {
                'active': False,
                'until': None
            },
            'stats': {
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0.0
            }
        }
        self.load_state()
    
    def load_state(self):
        """Load state from file"""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    saved = json.load(f)
                    self.state.update(saved)
            except:
                pass
    
    def save_state(self):
        """Save state to file"""
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, 'w') as f:
            json.dump(self.state, f, indent=2, default=str)
    
    def update_signal(self, prob_long: float, prob_short: float, price: float):
        """Update latest confidence scores for both LONG and SHORT"""
        self.state['last_signal'] = {
            'timestamp': datetime.now().isoformat(),
            'long_confidence': prob_long,
            'short_confidence': prob_short,
            'price': price,
            'long_triggered': prob_long >= self.state['thresholds']['long'],
            'short_triggered': prob_short >= self.state['thresholds']['short']
        }
        self.save_state()
    
    def open_position(self, direction: str, entry_price: float, tp_price: float, sl_price: float, confidence: float):
        """Open a new position"""
        self.state['current_position'] = {
            'timestamp': datetime.now().isoformat(),
            'direction': direction,
            'entry_price': entry_price,
            'tp_price': tp_price,
            'sl_price': sl_price,
            'confidence': confidence,
            'status': 'OPEN'
        }
        self.save_state()
    
    def close_position(self, exit_price: float, exit_reason: str, pnl: float):
        """Close current position"""
        if not self.state['current_position']:
            return
        
        pos = self.state['current_position']
        pos['exit_price'] = exit_price
        pos['exit_reason'] = exit_reason
        pos['exit_timestamp'] = datetime.now().isoformat()
        pos['pnl'] = pnl
        pos['status'] = 'CLOSED'
        
        # Update balance
        self.state['balance'] += pnl
        
        # Update stats
        self.state['stats']['total_trades'] += 1
        if exit_reason == 'TP':
            self.state['stats']['wins'] += 1
        elif exit_reason == 'SL':
            self.state['stats']['losses'] += 1
        
        total = self.state['stats']['wins'] + self.state['stats']['losses']
        if total > 0:
            self.state['stats']['win_rate'] = (self.state['stats']['wins'] / total) * 100
        
        # Save to trade history
        self.save_trade(pos)
        
        # Clear current position
        self.state['current_position'] = None
        self.save_state()
    
    def save_trade(self, trade: Dict):
        """Save trade to history"""
        os.makedirs(os.path.dirname(TRADES_FILE), exist_ok=True)
        
        history = []
        if os.path.exists(TRADES_FILE):
            try:
                with open(TRADES_FILE, 'r') as f:
                    history = json.load(f)
            except:
                pass
        
        history.append(trade)
        
        # Keep last 100 trades
        history = history[-100:]
        
        with open(TRADES_FILE, 'w') as f:
            json.dump(history, f, indent=2, default=str)
    
    def activate_circuit_breaker(self, until: datetime):
        """Activate circuit breaker"""
        self.state['circuit_breaker'] = {
            'active': True,
            'until': until.isoformat()
        }
        self.save_state()
    
    def deactivate_circuit_breaker(self):
        """Deactivate circuit breaker"""
        self.state['circuit_breaker'] = {
            'active': False,
            'until': None
        }
        self.save_state()
    
    def get_state(self) -> Dict:
        """Get current state"""
        return self.state
    
    def get_trade_history(self) -> List[Dict]:
        """Get trade history"""
        if os.path.exists(TRADES_FILE):
            try:
                with open(TRADES_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return []

if __name__ == "__main__":
    # Test
    state = MandalorianState()
    print(json.dumps(state.get_state(), indent=2))
