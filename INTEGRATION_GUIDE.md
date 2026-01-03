# Quick integration guide for adding logging to quant_engine.py

## Step 1: Add imports at top of file
```python
from utils.trade_logger import get_logger
from monitoring.performance_tracker import get_tracker
```

## Step 2: Initialize in __init__
```python
def __init__(self):
    # ... existing code ...
    
    # Initialize logging
    self.logger = get_logger()
    self.tracker = get_tracker()
```

## Step 3: Log predictions in check_winner_hunter and check_mtf_scalper
```python
# After getting prediction
self.logger.log_prediction(
    model_name='Winner Hunter (1H)',
    timestamp=datetime.now(),
    features=dict(zip(feature_cols, X[0])),
    confidence=prob,
    signal='LONG' if prob >= self.winner_threshold else None,
    market_data={'close': df.iloc[-1]['close'], 'volume': df.iloc[-1]['volume']}
)
```

## Step 4: Log trades when signals trigger
```python
if signal:
    # Log trade entry
    self.logger.log_trade_entry(
        prediction_id=f"WinnerHunter_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        entry_price=current_price,
        entry_time=datetime.now(),
        position_size=1000,  # $1000 position
        tp_price=current_price * 1.015,  # 1.5% TP
        sl_price=current_price * 0.992   # 0.8% SL
    )
```

## Step 5: Display performance metrics
```python
# In monitoring loop, after displaying status
perf = self.tracker.get_summary()
print(f"\n📊 Performance Summary:")
print(f"   Win Rate: {perf['win_rate']:.2%}")
print(f"   Calibration Error: {perf['calibration_error']:.4f}")

drift_detected, drop = self.tracker.detect_drift()
if drift_detected:
    print(f"   ⚠️ DRIFT DETECTED! Performance drop: {drop:.2%}")
```
