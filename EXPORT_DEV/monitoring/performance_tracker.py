#!/usr/bin/env python3
"""
Performance Tracker - Monitor model performance and detect concept drift
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from collections import deque

class PerformanceTracker:
    """
    Track model performance metrics and detect concept drift
    """
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        
        # Rolling windows for metrics
        self.predictions_window = deque(maxlen=window_size)
        self.outcomes_window = deque(maxlen=window_size)
        self.confidences_window = deque(maxlen=window_size)
        self.timestamps_window = deque(maxlen=window_size)
        
        # Performance history
        self.performance_history = []
        
        # Drift detection
        self.baseline_performance = None
        self.drift_threshold = 0.15  # 15% performance drop triggers drift alert
    
    def add_prediction(self, confidence: float, actual_outcome: int, timestamp: datetime):
        """
        Add a prediction with its outcome
        
        Args:
            confidence: Model confidence (0-1)
            actual_outcome: Actual outcome (1=win, 0=loss)
            timestamp: Prediction timestamp
        """
        self.predictions_window.append(1 if confidence >= 0.5 else 0)
        self.outcomes_window.append(actual_outcome)
        self.confidences_window.append(confidence)
        self.timestamps_window.append(timestamp)
        
        # Update baseline if not set
        if self.baseline_performance is None and len(self.outcomes_window) >= 50:
            self.baseline_performance = self.get_win_rate()
    
    def get_win_rate(self) -> float:
        """Calculate current win rate"""
        if not self.outcomes_window:
            return 0.0
        return sum(self.outcomes_window) / len(self.outcomes_window)
    
    def get_sharpe_ratio(self, returns: List[float]) -> float:
        """
        Calculate Sharpe ratio
        
        Args:
            returns: List of trade returns
            
        Returns:
            Sharpe ratio
        """
        if len(returns) < 2:
            return 0.0
        
        returns_array = np.array(returns)
        if returns_array.std() == 0:
            return 0.0
        
        # Annualized Sharpe (assuming daily returns)
        return (returns_array.mean() / returns_array.std()) * np.sqrt(365)
    
    def get_calibration_error(self) -> float:
        """
        Calculate calibration error (Brier score)
        
        Returns:
            Brier score (lower is better)
        """
        if not self.confidences_window or not self.outcomes_window:
            return 0.0
        
        confidences = np.array(list(self.confidences_window))
        outcomes = np.array(list(self.outcomes_window))
        
        return np.mean((confidences - outcomes) ** 2)
    
    def detect_drift(self) -> Tuple[bool, float]:
        """
        Detect concept drift based on performance degradation
        
        Returns:
            (drift_detected, performance_drop)
        """
        if self.baseline_performance is None or len(self.outcomes_window) < 30:
            return False, 0.0
        
        current_performance = self.get_win_rate()
        performance_drop = self.baseline_performance - current_performance
        
        drift_detected = performance_drop > self.drift_threshold
        
        return drift_detected, performance_drop
    
    def get_confidence_distribution(self) -> Dict:
        """
        Get confidence distribution statistics
        
        Returns:
            Dictionary of confidence stats
        """
        if not self.confidences_window:
            return {
                'mean': 0.0,
                'median': 0.0,
                'std': 0.0,
                'min': 0.0,
                'max': 0.0
            }
        
        confidences = np.array(list(self.confidences_window))
        
        return {
            'mean': float(confidences.mean()),
            'median': float(np.median(confidences)),
            'std': float(confidences.std()),
            'min': float(confidences.min()),
            'max': float(confidences.max()),
            'p25': float(np.percentile(confidences, 25)),
            'p75': float(np.percentile(confidences, 75)),
            'p95': float(np.percentile(confidences, 95))
        }
    
    def get_performance_by_confidence_bucket(self) -> Dict:
        """
        Calculate win rate by confidence bucket
        
        Returns:
            Dictionary mapping confidence ranges to win rates
        """
        if not self.confidences_window or not self.outcomes_window:
            return {}
        
        confidences = np.array(list(self.confidences_window))
        outcomes = np.array(list(self.outcomes_window))
        
        buckets = {
            '0-20%': (0.0, 0.2),
            '20-40%': (0.2, 0.4),
            '40-60%': (0.4, 0.6),
            '60-80%': (0.6, 0.8),
            '80-100%': (0.8, 1.0)
        }
        
        results = {}
        for bucket_name, (low, high) in buckets.items():
            mask = (confidences >= low) & (confidences < high)
            if mask.sum() > 0:
                win_rate = outcomes[mask].mean()
                count = mask.sum()
                results[bucket_name] = {
                    'win_rate': float(win_rate),
                    'count': int(count)
                }
        
        return results
    
    def get_summary(self) -> Dict:
        """
        Get comprehensive performance summary
        
        Returns:
            Dictionary of all metrics
        """
        drift_detected, performance_drop = self.detect_drift()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'window_size': len(self.outcomes_window),
            'win_rate': self.get_win_rate(),
            'calibration_error': self.get_calibration_error(),
            'confidence_distribution': self.get_confidence_distribution(),
            'performance_by_bucket': self.get_performance_by_confidence_bucket(),
            'drift_detected': drift_detected,
            'performance_drop': float(performance_drop),
            'baseline_performance': self.baseline_performance
        }
    
    def should_retrain(self) -> Tuple[bool, str]:
        """
        Determine if model should be retrained
        
        Returns:
            (should_retrain, reason)
        """
        # Check drift
        drift_detected, performance_drop = self.detect_drift()
        if drift_detected:
            return True, f"Concept drift detected (performance drop: {performance_drop:.2%})"
        
        # Check if enough data accumulated
        if len(self.outcomes_window) >= self.window_size:
            win_rate = self.get_win_rate()
            if win_rate < 0.25:  # Below 25% win rate
                return True, f"Poor performance (win rate: {win_rate:.2%})"
        
        return False, ""

# Singleton instance
_tracker = None

def get_tracker() -> PerformanceTracker:
    """Get the global performance tracker instance"""
    global _tracker
    if _tracker is None:
        _tracker = PerformanceTracker()
    return _tracker
