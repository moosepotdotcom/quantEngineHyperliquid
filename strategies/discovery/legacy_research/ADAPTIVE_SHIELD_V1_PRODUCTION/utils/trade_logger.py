#!/usr/bin/env python3
"""
Trade Logger - Track all predictions and outcomes for online learning
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

class TradeLogger:
    """
    Logs all predictions, trades, and outcomes for continuous learning
    """
    
    def __init__(self, log_dir='logs/trades'):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # In-memory storage for current session
        self.predictions = []
        self.trades = []
        self.outcomes = []
        
        # Performance metrics
        self.metrics = {
            'total_predictions': 0,
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'total_pnl': 0.0
        }
    
    def log_prediction(self, 
                      model_name: str,
                      timestamp: datetime,
                      features: Dict,
                      confidence: float,
                      signal: Optional[str] = None,
                      market_data: Optional[Dict] = None,
                      is_silent: bool = False):
        """
        Log a model prediction
        
        Args:
            model_name: Name of the model
            timestamp: Prediction timestamp
            features: Feature values
            confidence: Model confidence (0-1)
            signal: Trade signal (LONG/SHORT/None)
            market_data: Current market conditions
            is_silent: If True, do not save features (saves disk space)
        """
        prediction = {
            'id': f"{model_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}",
            'model': model_name,
            'timestamp': timestamp.isoformat(),
            'confidence': float(confidence),
            'signal': signal,
            'market_data': market_data or {}
        }
        
        if not is_silent:
            prediction['features'] = {k: float(v) if isinstance(v, (int, float, np.number)) else v 
                                    for k, v in features.items()}
        
        self.predictions.append(prediction)
        self.metrics['total_predictions'] += 1
        
        # Save to disk periodically (more frequent for live monitoring)
        if len(self.predictions) >= 10:
            self._save_predictions()
    
    def log_trade_entry(self,
                       prediction_id: str,
                       entry_price: float,
                       entry_time: datetime,
                       position_size: float,
                       tp_price: float,
                       sl_price: float):
        """
        Log a trade entry
        
        Args:
            prediction_id: ID of the prediction that triggered this trade
            entry_price: Entry price
            entry_time: Entry timestamp
            position_size: Position size in USD
            tp_price: Take profit price
            sl_price: Stop loss price
        """
        trade = {
            'trade_id': f"TRADE_{entry_time.strftime('%Y%m%d_%H%M%S')}",
            'prediction_id': prediction_id,
            'entry_time': entry_time.isoformat(),
            'entry_price': float(entry_price),
            'position_size': float(position_size),
            'tp_price': float(tp_price),
            'sl_price': float(sl_price),
            'status': 'OPEN',
            'exit_price': None,
            'exit_time': None,
            'pnl': None,
            'outcome': None
        }
        
        self.trades.append(trade)
        self.metrics['total_trades'] += 1
        self._save_trades()
    
    def log_trade_exit(self,
                      trade_id: str,
                      exit_price: float,
                      exit_time: datetime,
                      outcome: str):
        """
        Log a trade exit
        
        Args:
            trade_id: ID of the trade
            exit_price: Exit price
            exit_time: Exit timestamp
            outcome: WIN/LOSS/NEUTRAL
        """
        # Find the trade
        for trade in self.trades:
            if trade['trade_id'] == trade_id:
                # Calculate P&L
                entry_price = trade['entry_price']
                position_size = trade['position_size']
                pnl = ((exit_price - entry_price) / entry_price) * position_size
                
                # Update trade
                trade['exit_price'] = float(exit_price)
                trade['exit_time'] = exit_time.isoformat()
                trade['pnl'] = float(pnl)
                trade['outcome'] = outcome
                trade['status'] = 'CLOSED'
                
                # Update metrics
                if outcome == 'WIN':
                    self.metrics['wins'] += 1
                elif outcome == 'LOSS':
                    self.metrics['losses'] += 1
                
                self.metrics['total_pnl'] += pnl
                
                # Create outcome record for training
                outcome_record = {
                    'trade_id': trade_id,
                    'prediction_id': trade['prediction_id'],
                    'outcome': outcome,
                    'pnl': pnl,
                    'duration_seconds': (exit_time - datetime.fromisoformat(trade['entry_time'])).total_seconds(),
                    'exit_time': exit_time.isoformat()
                }
                self.outcomes.append(outcome_record)
                
                self._save_trades()
                self._save_outcomes()
                break
    
    def get_recent_performance(self, hours: int = 24) -> Dict:
        """
        Get performance metrics for recent period
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary of performance metrics
        """
        cutoff = datetime.now().timestamp() - (hours * 3600)
        
        recent_trades = [
            t for t in self.trades
            if t['status'] == 'CLOSED' and 
            datetime.fromisoformat(t['exit_time']).timestamp() > cutoff
        ]
        
        if not recent_trades:
            return {
                'period_hours': hours,
                'total_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'avg_pnl': 0.0
            }
        
        wins = sum(1 for t in recent_trades if t['outcome'] == 'WIN')
        total_pnl = sum(t['pnl'] for t in recent_trades)
        
        return {
            'period_hours': hours,
            'total_trades': len(recent_trades),
            'win_rate': wins / len(recent_trades),
            'total_pnl': total_pnl,
            'avg_pnl': total_pnl / len(recent_trades),
            'wins': wins,
            'losses': len(recent_trades) - wins
        }
    
    def get_training_data(self, min_trades: int = 100) -> Optional[pd.DataFrame]:
        """
        Get labeled training data from logged trades
        
        Args:
            min_trades: Minimum number of closed trades required
            
        Returns:
            DataFrame with features and labels, or None if insufficient data
        """
        closed_trades = [t for t in self.trades if t['status'] == 'CLOSED']
        
        if len(closed_trades) < min_trades:
            return None
        
        # Match trades with predictions
        training_data = []
        for trade in closed_trades:
            pred_id = trade['prediction_id']
            
            # Find matching prediction
            pred = next((p for p in self.predictions if p['id'] == pred_id), None)
            if not pred:
                continue
            
            # Create training sample
            sample = {
                **pred['features'],
                'confidence': pred['confidence'],
                'label': 1 if trade['outcome'] == 'WIN' else 0,
                'pnl': trade['pnl'],
                'timestamp': trade['entry_time']
            }
            training_data.append(sample)
        
        return pd.DataFrame(training_data)
    
    def _save_predictions(self):
        """Save predictions to disk"""
        filename = os.path.join(self.log_dir, f"predictions_{datetime.now().strftime('%Y%m%d')}.jsonl")
        with open(filename, 'a') as f:
            for pred in self.predictions:
                f.write(json.dumps(pred) + '\n')
        self.predictions = []  # Clear in-memory storage
    
    def _save_trades(self):
        """Save trades to disk"""
        filename = os.path.join(self.log_dir, f"trades_{datetime.now().strftime('%Y%m%d')}.json")
        with open(filename, 'w') as f:
            json.dump(self.trades, f, indent=2)
    
    def _save_outcomes(self):
        """Save outcomes to disk"""
        filename = os.path.join(self.log_dir, f"outcomes_{datetime.now().strftime('%Y%m%d')}.json")
        with open(filename, 'w') as f:
            json.dump(self.outcomes, f, indent=2)
    
    def get_confidence_stats(self, hours: int = 24) -> Dict:
        """Analyze recent confidence levels to help optimize thresholds"""
        # Load from recent prediction files if needed
        all_preds = []
        files = sorted([f for f in os.listdir(self.log_dir) if f.startswith('predictions_')], reverse=True)
        
        cutoff = datetime.now().timestamp() - (hours * 3600)
        
        for file in files[:3]:  # Latest 3 files
            try:
                with open(os.path.join(self.log_dir, file), 'r') as f:
                    for line in f:
                        pred = json.loads(line)
                        if datetime.fromisoformat(pred['timestamp']).timestamp() > cutoff:
                            all_preds.append(pred)
            except Exception:
                continue

        stats = {}
        for model in ['Winner Hunter (1H)', 'MTF Scalper (5M)', 'Gem Sniper (ULTRA)']:
            model_preds = [p['confidence'] for p in all_preds if p['model'] == model]
            if model_preds:
                stats[model] = {
                    'max': float(np.max(model_preds)),
                    'avg': float(np.mean(model_preds)),
                    'p90': float(np.percentile(model_preds, 90)),
                    'samples': len(model_preds)
                }
        return stats

    def save_metrics(self):
        """Save current metrics"""
        filename = os.path.join(self.log_dir, 'metrics.json')
        self.metrics['last_updated'] = datetime.now().isoformat()
        with open(filename, 'w') as f:
            json.dump(self.metrics, f, indent=2)

# Singleton instance
_logger = None

def get_logger() -> TradeLogger:
    """Get the global trade logger instance"""
    global _logger
    if _logger is None:
        _logger = TradeLogger()
    return _logger
