# 🚀 Quick Deployment Guide

## Step-by-Step Deployment

### 1. Verify Package Contents

```bash
cd trio_deployment
ls -lh
```

**Expected files**:
- ✅ `models/` (4 files: XGB, LGB, Cat, metadata)
- ✅ `utils/` (7 Python modules)
- ✅ `monitoring/` (2 Python modules)
- ✅ `quant_engine.py`
- ✅ `requirements.txt`
- ✅ `README.md`
- ✅ `TRIO_BACKTEST_REPORT.md`

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**Required packages**:
- xgboost
- lightgbm
- catboost
- pandas
- numpy
- requests

### 3. Test Engine Initialization

```bash
python3 -c "from quant_engine import TradingEngine; engine = TradingEngine(); print('✅ Engine loaded successfully')"
```

**Expected output**:
```
📦 Loading Trio Ensemble Models...
   🤖 Loading MTF Scalper (5M) Trio Ensemble...
   🎯 MTF Scalper thresholds: L:55.69%, S:62.28%
   ✅ All systems initialized
✅ Engine loaded successfully
```

### 4. Run Monitoring Mode (24h Dry Run)

```bash
python3 quant_engine.py
```

This will:
- Monitor live market data
- Display confidence scores
- Show signals when detected
- **NOT execute trades** (monitoring only)

### 5. Monitor Performance

**Key metrics to watch**:
- Signal frequency: 2-5 per day
- Confidence levels: Should be > 55% for Long, > 62% for Short
- Disagreement rate: Should be < 10%

### 6. Deploy to Production (After 24h Dry Run)

**Only if**:
- ✅ No errors during dry run
- ✅ Signals match expected frequency
- ✅ Confidence levels are reasonable
- ✅ No model disagreement warnings

---

## 🎯 Expected Performance

Based on backtest (out-of-sample test set):

| Metric | Value |
|--------|-------|
| **Win Rate** | 98.1% |
| **Long Accuracy** | 97.1% (66/68) |
| **Short Accuracy** | 100% (38/38) |
| **Signal Rate** | 0.17% (106/63,037) |
| **Est. Daily Profit** | $5K-$10K (1.27 BTC position) |

---

## ⚠️ Important Reminders

1. **Start Small**: Use 0.5-1.0 BTC position size initially
2. **Monitor Slippage**: Track difference between signal price and fill price
3. **Set Stop Loss**: Always use stop loss (default: 0.8%)
4. **Daily Limits**: Set max daily loss limit (e.g., -2% of account)
5. **Track Disagreement**: High disagreement (>15%) = skip trade

---

## 📊 Model Details

- **Models**: XGBoost + LightGBM + CatBoost (Trio Ensemble)
- **Consensus**: Average of 3 model predictions
- **Thresholds**: Long 55.69%, Short 62.28%
- **Features**: 231 technical indicators (5M + 15M + 1H)
- **Backtest Win Rate**: 98.1%

---

## 🔧 Troubleshooting

### Error: "Module not found"
```bash
pip install -r requirements.txt
```

### Error: "Model file not found"
```bash
ls -lh models/
# Should show 4 files (xgb, lgb, cat, metadata)
```

### Error: "API connection failed"
- Check internet connection
- Verify Hyperliquid API is accessible
- Try: `curl https://api.hyperliquid.xyz/info`

---

## 📞 Support

For issues:
1. Check `README.md` for detailed documentation
2. Review `TRIO_BACKTEST_REPORT.md` for performance metrics
3. Verify all model files are present in `models/`

---

**Package Version**: 1.0.0  
**Last Updated**: 2026-01-09  
**Model**: MTF Scalper 5M Trio Ensemble
