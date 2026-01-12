# 🚀 Trio Ensemble Trading Engine - Deployment Package

**Version**: 1.0.0  
**Date**: 2026-01-09  
**Model**: MTF Scalper (5M) Trio Ensemble  
**Performance**: 98.1% Win Rate (Backtest)

---

## 📦 Package Contents

This deployment package contains everything needed to run the production-ready MTF Scalper trio ensemble trading engine.

### Directory Structure

```
trio_deployment/
├── models/                          # Trio ensemble models
│   ├── mtf_scalper_5m_trio_xgb.json    (3.9 MB)
│   ├── mtf_scalper_5m_trio_lgb.json    (832 KB)
│   ├── mtf_scalper_5m_trio_cat.json    (177 KB)
│   └── mtf_scalper_5m_trio_metadata.json
├── utils/                           # Utility modules
│   ├── fetch_data.py               # Live data fetching from Hyperliquid
│   ├── feature_engineer.py         # Technical indicator generation
│   ├── trade_logger.py             # Trade logging and tracking
│   └── trend_filter.py             # Market regime detection
├── monitoring/                      # Monitoring modules
│   ├── performance_tracker.py      # Performance metrics tracking
│   └── trade_exit_monitor.py       # TP/SL monitoring
├── quant_engine.py                 # Main trading engine
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variables template
└── README.md                       # This file
```

---

## ✅ Model Performance

**Backtest Results** (Out-of-sample test set):

| Metric | Value |
|--------|-------|
| **Win Rate** | **98.1%** |
| **Total Signals** | 106 |
| **Wins / Losses** | 104W / 2L |
| **Long Signals** | 68 (66W / 2L) - 97.1% accuracy |
| **Short Signals** | 38 (38W / 0L) - 100% accuracy |
| **Estimated Profit** | ~$186,443 (1.27 BTC position) |

---

## 🔧 Installation

### 1. Install Dependencies

```bash
cd trio_deployment
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys and settings
```

### 3. Verify Installation

```bash
python3 -c "import xgboost, lightgbm, catboost; print('✅ All dependencies installed')"
```

---

## 🚀 Quick Start

### Run in Monitoring Mode (Recommended First)

```bash
python3 quant_engine.py
```

This will:
- Load all 3 trio ensemble models (XGBoost, LightGBM, CatBoost)
- Monitor live market data from Hyperliquid
- Display confidence scores and signals
- **NOT execute trades** (monitoring only)

### Key Features

- **Consensus Mechanism**: Averages predictions from 3 models
- **Disagreement Detection**: Alerts when models disagree (std > 0.15)
- **Precision Thresholds**: Long 55.69%, Short 62.28%
- **Multi-Timeframe**: Uses 5M base + 15M + 1H context (231 features)

---

## 📊 Model Details

### Architecture
- **Ensemble Type**: Trio (XGBoost + LightGBM + CatBoost)
- **Prediction Method**: Average of 3 model probabilities
- **Classes**: Multi-class (0=Neutral, 1=Long, 2=Short)
- **Features**: 231 technical indicators with MTF context

### Training Details
- **Dataset**: 420,246 labeled 5M candles (10 years historical)
- **Class Weights**: Balanced (handles 30-38% imbalance)
- **Validation**: Chronological split (70% train, 15% val, 15% test)
- **Hyperparameters**:
  - XGBoost: 500 estimators, depth 7, lr 0.03
  - LightGBM: 800 estimators, depth 7, lr 0.02
  - CatBoost: 600 iterations, depth 7, lr 0.03

### Thresholds
- **Long Threshold**: 0.5569 (55.69%) - Targets 95.1% precision
- **Short Threshold**: 0.6228 (62.28%) - Targets 95.5% precision

---

## ⚙️ Configuration

### Environment Variables (.env)

```bash
# Hyperliquid API (if using live trading)
HYPERLIQUID_API_KEY=your_api_key_here
HYPERLIQUID_SECRET=your_secret_here

# Trading Parameters
POSITION_SIZE_BTC=1.27
TAKE_PROFIT_PCT=0.015  # 1.5%
STOP_LOSS_PCT=0.008    # 0.8%

# Risk Management
MAX_DAILY_TRADES=10
MAX_CONCURRENT_POSITIONS=3
```

### Model Configuration

Models automatically load thresholds from `models/mtf_scalper_5m_trio_metadata.json`:

```json
{
    "target_precision_threshold_long": 0.5569,
    "target_precision_threshold_short": 0.6228,
    "expected_precision_long": 0.9514,
    "expected_precision_short": 0.9545
}
```

---

## 🎯 Usage Examples

### Example 1: Monitor Live Signals

```python
from quant_engine import TradingEngine

engine = TradingEngine()
engine.run_continuous_monitoring(max_hours=24)
```

### Example 2: Check Single Prediction

```python
from quant_engine import TradingEngine

engine = TradingEngine()
signal, confidence = engine.check_mtf_scalper()

if signal:
    print(f"Signal: {signal['direction']} @ {signal['price']}")
    print(f"Confidence: {confidence:.2%}")
```

---

## 🛡️ Risk Management

### Built-in Safety Features

1. **Elastic Threshold Manager**: Adapts thresholds based on recent performance
2. **Trend Filter**: Blocks counter-trend trades in strong directional markets
3. **Hurst Exponent Filter**: Prevents "falling knife" trades (buying dips in downtrends)
4. **AI Smart Filter**: Blocks oversold shorts (RSI_7 < 25)
5. **Disagreement Detection**: Warns when trio models disagree

### Recommended Practices

- Start with **0.5-1.0 BTC position size** for first week
- Monitor **slippage** between signal price and fill price
- Track **disagreement frequency** (should be < 10% of signals)
- Run **24h dry run** before live trading
- Set **max daily loss limit** (e.g., -2% of account)

---

## 📈 Monitoring

### Key Metrics to Track

1. **Win Rate**: Should maintain > 90% in live trading
2. **Signal Frequency**: Expect 2-5 signals per day
3. **Disagreement Rate**: Should be < 10%
4. **Slippage**: Should be < 0.1% per trade
5. **Drawdown**: Should be < 3% of account

### Logs

- **Trade Logs**: Automatically saved to `logs/trades.json`
- **Performance Logs**: Saved to `logs/performance.json`
- **Prediction Logs**: Saved to `logs/predictions.json`

---

## 🔄 Updates and Maintenance

### When to Retrain

- **Win rate drops below 85%** for 7+ consecutive days
- **Market regime changes** (e.g., bull to bear market)
- **New data available** (collect 3-6 months, retrain)

### How to Retrain

```bash
# 1. Collect new data
python3 training/data_downloader.py

# 2. Generate features
python3 training/feature_generator.py

# 3. Label data
python3 training/label_generator.py

# 4. Train new models
python3 training/train_mtf_scalper.py

# 5. Backtest
python3 backtest_trio_models.py

# 6. Deploy if win rate > 90%
cp models/mtf_scalper_5m_trio_*.json trio_deployment/models/
```

---

## ⚠️ Important Notes

> [!WARNING]
> **Live Trading Risk**: This model achieved 98.1% win rate on historical data. Live trading performance may differ due to slippage, latency, and market conditions. Always start with small positions.

> [!IMPORTANT]
> **Model Limitations**: 
> - Only trained on BTC/USD 5M data
> - Requires stable internet connection for live data
> - Not tested in extreme volatility (e.g., flash crashes)

> [!CAUTION]
> **Not Financial Advice**: This is an experimental trading system. Use at your own risk. Never trade with money you can't afford to lose.

---

## 📞 Support

For issues or questions:
1. Check logs in `logs/` directory
2. Review backtest report: `TRIO_BACKTEST_REPORT.md`
3. Verify model files are not corrupted: `ls -lh models/`

---

## 📄 License

This deployment package is for personal use only. Do not redistribute without permission.

---

**Last Updated**: 2026-01-09  
**Model Version**: MTF Scalper 5M Trio v1.0  
**Backtest Win Rate**: 98.1%
