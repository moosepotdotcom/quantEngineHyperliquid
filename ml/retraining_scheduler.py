#!/usr/bin/env python3
"""
Retraining Scheduler - Automatic model retraining triggers
"""
from datetime import datetime, timedelta
from typing import Dict, Tuple
import threading
import time

class RetrainingScheduler:
    """
    Manages automatic retraining triggers
    """
    
    def __init__(self):
        self.last_retrain = {}  # model_name -> timestamp
        self.retrain_config = {
            'min_samples': 100,  # Minimum new samples needed
            'max_days': 7,  # Maximum days between retraining
            'performance_threshold': 0.25,  # Min win rate
            'drift_threshold': 0.15  # Max performance drop
        }
    
    def should_retrain(self, 
                      model_name: str,
                      logger,
                      tracker) -> Tuple[bool, str]:
        """
        Determine if model should be retrained
        
        Args:
            model_name: Name of the model
            logger: TradeLogger instance
            tracker: PerformanceTracker instance
            
        Returns:
            (should_retrain, reason)
        """
        reasons = []
        
        # Check 1: Time since last retrain
        last_retrain_time = self.last_retrain.get(model_name)
        if last_retrain_time:
            days_since = (datetime.now() - last_retrain_time).days
            if days_since >= self.retrain_config['max_days']:
                reasons.append(f"Scheduled retraining ({days_since} days since last)")
        else:
            # Never retrained - check if enough data
            training_data = logger.get_training_data(min_trades=self.retrain_config['min_samples'])
            if training_data is not None and len(training_data) >= self.retrain_config['min_samples']:
                reasons.append(f"Initial retraining ({len(training_data)} samples available)")
        
        # Check 2: Performance degradation
        should_retrain_perf, perf_reason = tracker.should_retrain()
        if should_retrain_perf:
            reasons.append(perf_reason)
        
        # Check 3: Data accumulation
        training_data = logger.get_training_data(min_trades=1)
        if training_data is not None:
            # Count new samples since last retrain
            if last_retrain_time:
                new_samples = len(training_data[training_data['timestamp'] > last_retrain_time.isoformat()])
                if new_samples >= self.retrain_config['min_samples'] * 2:  # 2x threshold
                    reasons.append(f"Data accumulation ({new_samples} new samples)")
        
        if reasons:
            return True, "; ".join(reasons)
        return False, ""
    
    def mark_retrained(self, model_name: str):
        """Mark that model was retrained"""
        self.last_retrain[model_name] = datetime.now()
    
    def run_background_retraining(self, 
                                  model_name: str,
                                  logger,
                                  tracker,
                                  learner,
                                  interval_hours: int = 6):
        """
        Run background retraining check
        
        Args:
            model_name: Name of model
            logger: TradeLogger instance
            tracker: PerformanceTracker instance
            learner: OnlineLearner instance
            interval_hours: Hours between checks
        """
        def check_and_retrain():
            while True:
                try:
                    # Check if should retrain
                    should_retrain, reason = self.should_retrain(model_name, logger, tracker)
                    
                    if should_retrain:
                        print(f"\n🔄 AUTO-RETRAIN TRIGGERED: {reason}")
                        
                        # Run incremental update
                        success = learner.run_incremental_update(logger, force=False)
                        
                        if success:
                            self.mark_retrained(model_name)
                            print(f"✅ Auto-retrain complete for {model_name}")
                        else:
                            print(f"⚠️ Auto-retrain failed for {model_name}")
                    
                except Exception as e:
                    print(f"❌ Error in background retraining: {e}")
                
                # Wait before next check
                time.sleep(interval_hours * 3600)
        
        # Start background thread
        thread = threading.Thread(target=check_and_retrain, daemon=True)
        thread.start()
        print(f"🔄 Background retraining started for {model_name} (check every {interval_hours}h)")

# Singleton instance
_scheduler = None

def get_scheduler() -> RetrainingScheduler:
    """Get the global retraining scheduler"""
    global _scheduler
    if _scheduler is None:
        _scheduler = RetrainingScheduler()
    return _scheduler
