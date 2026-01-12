# 📚 MODEL RETRAINING GUIDE

This guide explains how to retrain the Adaptive Shield models from scratch, achieving the same 92.9% win rate performance.

---

## 📊 Training Data

**File**: `training/data/BTC_5m_mtf_labeled.csv`
- **Size**: ~50 MB
- **Period**: Up to December 30, 2025 05:45 UTC
- **Rows**: ~60,000 5-minute candles
- **Features**: 239 columns (85 base + MTF context from 15m/1h)

**Schema**:
- `timestamp`: Candle timestamp
- `open`, `high`, `low`, `close`, `volume`: OHLCV data
- 85 technical indicators (RSI, MACD, Bollinger, ATR, etc.)
- MTF context: Indicators suffixed with `_15m` and `_1h`
- `label`: Target class (0=Neutral, 1=Long, 2=Short)

---

## 🔧 Step-by-Step Retraining

### Prerequisites
Ensure you have installed all dependencies:
```bash
pip install -r requirements.txt
```

### Step 1: Prepare Training Data (Optional - Already Included)

If you need to regenerate training data from scratch:

```bash
# Fetch fresh data from Hyperliquid
python utils/fetch_data.py --interval 5m --days 60 --output training/data/BTC_5m_raw.csv

# Generate features
python utils/feature_engineer.py --input training/data/BTC_5m_raw.csv --output training/data/BTC_5m_features.csv

# Add labels (TP: 1.5%, SL: 0.8%)
python training/label_generator.py --input training/data/BTC_5m_features.csv --tp 0.015 --sl 0.008 --output training/data/BTC_5m_mtf_labeled.csv
```

**⚠️ Note**: The included `BTC_5m_mtf_labeled.csv` is already properly formatted and labeled. Only regenerate if you want fresh data.

### Step 2: Train the Trio Ensemble Models

Run the training script:

```bash
python training/train_ultimate_trio.py
```

**What this does**:
1. Loads `training/data/BTC_5m_mtf_labeled.csv`
2. Regenerates advanced features (Hurst, Volatility, Wicks)
3. Splits data: 85% training, 15% validation (temporal split)
4. Trains 3 models:
   - **XGBoost**: 1000 estimators, max_depth=6, lr=0.01
   - **LightGBM**: 1000 rounds, num_leaves=31, lr=0.02
   - **CatBoost**: 1000 iterations, depth=6, lr=0.03
5. Saves models to `models/`:
   - `mtf_scalper_5m_trio_xgb.json`
   - `mtf_scalper_5m_trio_lgb.json`
   - `mtf_scalper_5m_trio_cat.json`
   - `mtf_scalper_5m_trio_metadata.json`

**Expected Output**:
```
🚀 STARTING ULTIMATE RETRAINING PROTOCOL
============================================================
📊 Loading dataset: training/data/BTC_5m_mtf_labeled.csv
🔧 Generating Advanced Features (Hurst, Volatility, Wicks)...
✅ Training Data (Cleaned): 58234 samples
⚖️ Class Weights: {0: 0.98, 1: 1.15, 2: 1.08}
📉 Train size: 49499 | Test size: 8735

🤖 Training XGBoost (Precision Optimized)...
[100] validation_0-mlogloss:0.68234
[200] validation_0-mlogloss:0.65891
...
✅ Training Complete!
```

**Training Time**: ~10-15 minutes on modern hardware

### Step 3: Verify Model Performance

Run the verification backtest:

```bash
python simulate_last_week.py
```

This simulates trading on Jan 2-9, 2026 using the newly trained models.

**Expected Results**:
- Win Rate: 92-93%
- Total Trades: 180-185
- Total PnL: +240-250%

If results deviate significantly, check:
- Training data integrity
- Feature generation (ensure Hurst is enabled)
- Model hyperparameters

### Step 4: Deploy Updated Models

Copy the retrained models to your live deployment:

```bash
cp models/mtf_scalper_5m_trio*.json ADAPTIVE_SHIELD_V1_PRODUCTION/models/
```

Restart your trading bot to load the new models.

---

## 🎛️ Hyperparameter Tuning (Advanced)

### Default Configuration (Verified)

The current hyperparameters are **optimized for precision**:

**XGBoost**:
```python
n_estimators=1000
learning_rate=0.01
max_depth=6
subsample=0.8
colsample_bytree=0.8
```

**LightGBM**:
```python
num_boost_round=1000
learning_rate=0.02
num_leaves=31
feature_fraction=0.8
bagging_fraction=0.8
```

**CatBoost**:
```python
iterations=1000
learning_rate=0.03
depth=6
class_weights='balanced'
```

### Tuning Guidelines

⚠️ **Warning**: Changing hyperparameters may degrade performance. Only modify if you understand the trade-offs.

**To increase precision** (fewer but more accurate trades):
- Increase `learning_rate` → Models converge faster, may overfit
- Decrease `max_depth/depth` → Simpler models, less overfitting
- Increase `n_estimators` → More training, diminishing returns

**To increase volume** (more trades):
- Decrease threshold in `quant_engine.py` (from 0.45 to 0.40)
- ⚠️ This will reduce win rate

---

## 🔍 Troubleshooting

### Issue: Training script fails with "inf" error
**Solution**: 
- Ensure `df.replace([np.inf, -np.inf], np.nan, inplace=True)` is present in training script
- Check for division by zero in feature engineering

### Issue: Model performance degrades after retraining
**Causes**:
1. **Data shift**: Market conditions changed
2. **Feature mismatch**: Ensure same feature engineering pipeline
3. **Overfitting**: Try reducing model complexity

**Solutions**:
- Use the **exact same training data** (`BTC_5m_mtf_labeled.csv` up to Dec 30, 2025)
- Verify feature count: Should be 239 features
- Check validation loss during training (should decrease steadily)

### Issue: "Feature shape mismatch" during prediction
**Solution**:
- Ensure `utils/feature_engineer.py` generates the same 85 base features
- Verify MTF context (15m, 1h) is being merged correctly
- Check `simulate_last_week.py` line 226: Feature slicing to 239

---

## 📈 Performance Validation

After retraining, validate your models meet the criteria:

### Minimum Acceptable Performance (Backtest Jan 2-9, 2026)
| Metric | Minimum | Target |
|--------|---------|--------|
| Win Rate | ≥88% | 92-93% |
| Total Trades | ≥150 |180-185 |
| Total PnL | ≥+200% | +240-250% |
| Longest Win Streak | ≥70 | 85-90 |

**If below minimum**: Do NOT deploy. Investigate data/feature issues.

### Advanced Validation

Run forensic analysis:
```bash
python analyze_forensics.py
```

Check:
- Disagreement Avg (Winners) < 0.09
- ATR Avg (Winners) < 75
- ATR Avg (Losers) > 85

---

## 🔄 Continuous Improvement

### Retraining Schedule (Recommended)

**Monthly Retraining**:
- Fetch latest 60 days of data
- Retrain models
- Backtest on most recent week
- Deploy if performance ≥92% WR

**After Market Regime Shifts**:
- Major volatility events (e.g., Jan 6-8 in our backtest)
- Regulatory changes
- Prolonged win rate degradation (<85% for 3+ days)

### Data Collection

To build your own training dataset:

```python
# Pseudo-code for data collection
from utils.fetch_data import fetch_live_data
import pandas as pd

# Fetch 60 days of 5m, 15m, 1h data
df_5m = fetch_live_data('5m', days=60)
df_15m = fetch_live_data('15m', days=60)
df_1h = fetch_live_data('1h', days=60)

# Generate features
from utils.feature_engineer import add_all_indicators
df_5m = add_all_indicators(df_5m)
df_15m = add_all_indicators(df_15m)
df_1h = add_all_indicators(df_1h)

# Merge MTF context
# ... (see train_ultimate_trio.py for full logic)

# Label data
# ... (see training/label_generator.py)
```

---

## ✅ Replication Checklist

To replicate the **exact** 92.9% win rate:

- [ ] Use the **exact** training data: `BTC_5m_mtf_labeled.csv` (up to Dec 30, 2025)
- [ ] Run `train_ultimate_trio.py` with **default** hyperparameters
- [ ] Verify 3 model files generated (XGB, LGB, Cat)
- [ ] Set threshold to **0.45** in `quant_engine.py`
- [ ] Enable **Adaptive Volatility Shield** (ATR penalty logic)
- [ ] Enable **Circuit Breaker** (2 losses, 4h cooldown)
- [ ] Test on Jan 2-9, 2026 data via `simulate_last_week.py`
- [ ] Confirm: Win Rate 92-93%, Total PnL +240-250%

---

## 📞 Support

If you encounter issues during retraining:

1. Check training script output for errors
2. Verify feature count (should be 239)
3. Ensure all dependencies installed
4. Review `PRODUCTION_CONFIG_VERIFIED.md` for configuration details

**Remember**: The included models are already trained and verified. Only retrain if:
- You want to update with fresh data
- You're experimenting with hyperparameters
- You're adapting to new market conditions

---

**Last Updated**: 2026-01-10  
**Training Data Version**: v1.0 (up to Dec 30, 2025)  
**Verified Models**: Jan 9, 2026 training run
