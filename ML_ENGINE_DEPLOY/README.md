# 🎯 ML Engine - Paper Trading Bot

**82.6% Win Rate | 400x Leverage | 0.5 BTC Position Size**

## 📊 Backtest Results (Jan 2-16, 2026)

- **Total Trades:** 322
- **Wins:** 190 ✅ | **Losses:** 40 ❌
- **Win Rate:** 82.6%
- **ROI:** +116.79% ($100k → $216k in 15 days)

## 🛡️ Shields & Protection

1. **Mandalorian Filter**: Blocks falling knife trades (RSI < 30 + Hurst > 0.5)
2. **AI Smart Filter**: Blocks oversold shorts (RSI_7 < 25)
3. **Circuit Breaker**: 4-hour cooldown after 2 consecutive losses

## 📦 Package Contents

```
ML_ENGINE_DEPLOY/
├── models/                    # ML models (6 files)
│   ├── mtf_scalper_5m_trio_xgb.json
│   ├── mtf_scalper_5m_trio_lgb.json
│   ├── mtf_scalper_5m_trio_cat.json
│   ├── winner_hunter_1h_trio_xgb.json
│   ├── winner_hunter_1h_trio_lgb.json
│   └── winner_hunter_1h_trio_cat.json
├── utils/                     # Utility modules
│   ├── feature_engineer.py
│   ├── advanced_features.py
│   ├── fetch_data.py
│   ├── trade_logger.py
│   └── trend_filter.py
├── quant_engine.py           # Core trading engine
├── golden_config.json        # Verified configuration
├── live_paper_trading.py     # Live trading script
├── Dockerfile                # Cloud Run container
├── deploy.sh                 # Deployment script
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## 🚀 Deployment to Google Cloud Run

### Prerequisites

1. Google Cloud SDK installed
2. Project ID configured
3. Cloud Run API enabled

### Steps

1. **Update Project ID**:
   ```bash
   # Edit deploy.sh and set your PROJECT_ID
   nano deploy.sh
   ```

2. **Make deployment script executable**:
   ```bash
   chmod +x deploy.sh
   ```

3. **Deploy**:
   ```bash
   ./deploy.sh
   ```

4. **Monitor logs**:
   ```bash
   gcloud run logs tail ml-engine-paperbot --region us-central1
   ```

## ⚙️ Configuration

- **Leverage**: 400x
- **Position Size**: 0.5 BTC
- **Initial Balance**: $100,000
- **Take Profit**: 1.5%
- **Stop Loss**: 0.8%
- **Mode**: Paper Trading (no real money)

## 📈 Expected Performance

Based on 15-day backtest:
- **Daily ROI**: ~7.8%
- **Trades per day**: ~21
- **Average win**: +$689 (+600% ROE)
- **Average loss**: -$367 (-320% ROE)

## 🔒 Safety Features

- Paper trading mode (no real money at risk)
- Circuit breaker protection
- Position size limits
- Automatic shield filters
- Error handling and retry logic

## 📝 Notes

- This is a PAPER TRADING bot - no real money is traded
- All trades are simulated for performance tracking
- Requires continuous internet connection
- Cloud Run will auto-restart on crashes

---

*Generated: 2026-01-16*
*Backtest Period: Jan 2-16, 2026*
*Win Rate: 82.6%*
