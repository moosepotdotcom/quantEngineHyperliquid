# Online Learning System - Quick Start Guide

## 🎯 Overview

The online learning system enables models to continuously improve based on live trading data.

## 📦 Components

### 1. TradeLogger (`utils/trade_logger.py`)
- Logs all predictions and trades
- Stores data to `logs/trades/`
- Provides training data for retraining

### 2. PerformanceTracker (`monitoring/performance_tracker.py`)
- Monitors model performance
- Detects concept drift
- Triggers retraining alerts

### 3. OnlineLearner (`ml/online_learner.py`)
- Trains models incrementally
- Uses sliding window (last 30 days)
- Versions and saves models
- Hot-swaps production models

### 4. RetrainingScheduler (`ml/retraining_scheduler.py`)
- Automatic retraining triggers
- Background execution
- Multiple trigger conditions

## 🚀 How It Works

```
Live Trading
    ↓
[TradeLogger] → Logs predictions & outcomes
    ↓
[PerformanceTracker] → Monitors performance
    ↓
[RetrainingScheduler] → Checks triggers
    ↓
[OnlineLearner] → Trains new model
    ↓
Production Model Updated (hot-swap)
```

## 🔄 Retraining Triggers

1. **Scheduled:** Every 7 days
2. **Performance:** Win rate < 25%
3. **Drift:** Performance drop > 15%
4. **Data:** 200+ new samples accumulated

## 💻 Usage

### Manual Retraining
```python
from ml.online_learner import get_learner
from utils.trade_logger import get_logger

# Get instances
learner = get_learner('winner_hunter_1h')
logger = get_logger()

# Run incremental update
success = learner.run_incremental_update(logger, force=False)
```

### Automatic Retraining
```python
from ml.retraining_scheduler import get_scheduler

# Get scheduler
scheduler = get_scheduler()

# Start background retraining (checks every 6 hours)
scheduler.run_background_retraining(
    model_name='winner_hunter_1h',
    logger=logger,
    tracker=tracker,
    learner=learner,
    interval_hours=6
)
```

## 📊 Model Versioning

Models are saved with timestamps:
```
training/online_learning/
├── winner_hunter_1h_v20251230_130000.pkl
├── winner_hunter_1h_v20251230_130000_metrics.json
├── winner_hunter_1h_history.json
└── mtf_scalper_5m_v20251230_140000.pkl
```

## ✅ Benefits

- **Continuous Improvement:** Models adapt to market changes
- **Automatic:** No manual intervention needed
- **Safe:** Only updates if new model is better
- **Versioned:** Can rollback if needed
- **Fast:** Incremental training (minutes, not hours)

## 🎯 Next Steps

1. Deploy online learning to Cloud Run
2. Monitor first automatic retraining
3. Implement ensemble methods (Phase 3)
4. Add A/B testing (Phase 4)
