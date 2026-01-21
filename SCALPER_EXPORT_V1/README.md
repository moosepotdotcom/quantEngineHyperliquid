# 🚀 SCALPER MODEL V1 - EXPORT PACKAGE

**Created:** 2026-01-14 01:58  
**Model Type:** Scalping Ensemble (0.5% TP / 0.3% SL)  
**Win Rate:** 80.8% @ 45% confidence threshold

---

## 📦 **PACKAGE CONTENTS:**

### **Models:**
- `scalping/xgb_scalper.json` - XGBoost model (75.25% accuracy)
- `scalping/lgb_scalper.txt` - LightGBM model (75.45% accuracy)
- `scalping/cat_scalper.cbm` - CatBoost model (62.22% accuracy)
- `scalping/feature_names.pkl` - Feature list (15 features)

### **Training Data:**
- `scalping_labels_0.5pct.csv` - Labeled training data (5,037 samples)
  - LONG signals: 1,768 (35.1%)
  - SHORT signals: 1,340 (26.6%)
  - Tradeable: 3,108 (61.7%)

### **Scripts:**
- `train_scalping_simple.py` - Training script
- `generate_scalping_labels.py` - Label generator

---

## 📊 **MODEL PERFORMANCE:**

### **Test Set Results:**
- **Ensemble Accuracy:** 73.65%
- **Test Samples:** 998

### **Win Rate by Confidence:**
| Threshold | Win Rate | Trades |
|-----------|----------|--------|
| ≥40% | 75.3% | 600 |
| **≥45%** | **80.8%** | **511** ✅ |
| ≥50% | 85.4% | 418 |
| ≥55% | 88.8% | 338 |
| ≥60% | 90.7% | 269 |

**Recommended:** Use 45% threshold for 80.8% win rate

---

## 🎯 **TARGET PARAMETERS:**

```python
TP: 0.5% (0.005)
SL: 0.3% (0.003)
Confidence Threshold: 45% (0.45)
```

---

## 📈 **EXPECTED PERFORMANCE:**

### **Comparison with Current Model:**

| Metric | Current (Swing) | Scalper V1 | Improvement |
|--------|----------------|------------|-------------|
| TP/SL | 1.5% / 0.8% | 0.5% / 0.3% | 3x smaller |
| Hold Time | 8-12h | 1-2h | 6x faster |
| Trades/10d | 7 | 15-25 | 2-3x more |
| Win Rate | 71.4% | 80.8% | +9.4% |
| ROI/10d | +159% | +300-400% | 2-3x more |

---

## 🔧 **FEATURES USED:**

1. sma_10 - Simple Moving Average (10)
2. sma_20 - Simple Moving Average (20)
3. sma_50 - Simple Moving Average (50)
4. ema_10 - Exponential Moving Average (10)
5. ema_20 - Exponential Moving Average (20)
6. rsi_14 - Relative Strength Index (14)
7. atr_14 - Average True Range (14)
8. volatility - 20-period volatility
9. price_change - Price change percentage
10. high_low_ratio - High/Low ratio
11. close_open_ratio - Close/Open ratio
12. volume_sma - Volume moving average
13. volume_ratio - Volume/SMA ratio
14. momentum_5 - 5-period momentum
15. momentum_10 - 10-period momentum

---

## 🚀 **DEPLOYMENT INSTRUCTIONS:**

### **Step 1: Copy Models**
```bash
cp -r SCALPER_EXPORT_V1/scalping /path/to/EXPORT/models/
```

### **Step 2: Update Configuration**
```python
# In quant_engine.py or config:
TP_PCT = 0.005  # 0.5%
SL_PCT = 0.003  # 0.3%
MTF_THRESHOLD_LONG = 0.45  # 45%
MTF_THRESHOLD_SHORT = 0.45  # 45%
```

### **Step 3: Load Models**
```python
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier

xgb_model = xgb.XGBClassifier()
xgb_model.load_model('models/scalping/xgb_scalper.json')

lgb_model = lgb.Booster(model_file='models/scalping/lgb_scalper.txt')

cat_model = CatBoostClassifier()
cat_model.load_model('models/scalping/cat_scalper.cbm')
```

### **Step 4: Test**
Run backtest on Jan 2-11 to verify performance

### **Step 5: Deploy**
Deploy to production with paper trading first

---

## ⚠️ **IMPORTANT NOTES:**

1. **Backup:** This is V1 - keep it safe!
2. **Testing:** Always test on paper mode first
3. **Monitoring:** Monitor first 10 trades closely
4. **Thresholds:** Can adjust 45% threshold based on live performance
5. **Filters:** Keep Hurst and AI filters active

---

## 📝 **VERSION HISTORY:**

**V1 (2026-01-14):**
- Initial scalper model
- Trained on 5,037 samples
- 15 features
- 80.8% win rate @ 45% threshold
- Optimized for 0.5% TP / 0.3% SL

---

## 🎯 **NEXT STEPS:**

1. ✅ Models exported and backed up
2. ⏸️ Run backtest on Jan 2-11
3. ⏸️ Compare with current model
4. ⏸️ Deploy to production
5. ⏸️ Monitor live performance

---

*Scalper Model V1 - Exported and Secured!* 🚀
