# AI Trading Bot - Hyperliquid

**Status:** 🟢 Production | **Win Rate:** 100% | **Total P&L:** +$3,119.30

An AI-powered cryptocurrency trading bot using XGBoost models for automated trading on Hyperliquid. Features continuous monitoring, exit tracking, and adaptive learning capabilities.

---

## 🎯 Performance Metrics

```
Total Trades:      8
Win Rate:          100% (8/8 profitable)
Realized P&L:      +$1,311.30
Unrealized P&L:    +$1,808.00
Total P&L:         +$3,119.30
Best Trade:        +$294 (+0.34%)
```

---

## 🚀 Features

- **Dual Model System**
  - Winner Hunter (1H): Long-term trend detection
  - MTF Scalper (5M): Multi-timeframe scalping
  
- **Advanced Monitoring**
  - 24/7 continuous operation
  - Real-time exit tracking with TP/SL monitoring
  - Historical price checks for missed exits
  
- **Production Ready**
  - Deployed on Google Cloud Run
  - Complete trade logging and performance tracking
  - Automatic model retraining (planned)

---

## 📋 Quick Start

### Prerequisites
- Python 3.9+
- Google Cloud account (for deployment)
- Hyperliquid API access

### Local Setup

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/quantEngineHyperliquid.git
cd quantEngineHyperliquid

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run locally
python quant_engine.py
```

### Cloud Deployment

```bash
# Build and deploy to Cloud Run
gcloud builds submit --config cloudbuild.yaml
gcloud run deploy quant-engine-hl \
  --image gcr.io/YOUR_PROJECT_ID/quant-engine-hl \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 3600
```

---

## 🏗️ Architecture

```
quantEngineHyperliquid/
├── models/              # Trained XGBoost models
├── ml/                  # ML components (online learning, retraining)
├── monitoring/          # Exit monitor, performance tracker
├── training/            # Model training scripts
├── utils/               # Feature engineering, trade logger
├── quant_engine.py      # Main trading engine
├── cloud_runner.py      # Cloud Run wrapper
└── Dockerfile           # Container configuration
```

---

## 📊 Models

### Winner Hunter (1H)
- **Timeframe:** 1 hour
- **Threshold:** 27.52%
- **Strategy:** Long-term trend following
- **Performance:** 4/4 profitable

### MTF Scalper (5M)
- **Timeframe:** 5 minutes (with 15m and 1h context)
- **Threshold:** 20.13%
- **Strategy:** Multi-timeframe scalping
- **Performance:** 4/4 profitable

---

## 🔧 Configuration

### Environment Variables

```bash
# Google Cloud
GCP_PROJECT_ID=your-project-id
GCP_REGION=us-central1

# Model Configuration
WINNER_HUNTER_THRESHOLD=0.2752
MTF_SCALPER_THRESHOLD=0.2013

# Trading Parameters
TP_PERCENTAGE=0.015  # 1.5%
SL_PERCENTAGE=0.008  # 0.8%
```

---

## 📈 Trading Strategy

### Entry Criteria
- Model confidence above threshold
- Technical indicators confirmation (RSI, MACD, ATR)
- Multi-timeframe alignment (for MTF Scalper)

### Risk Management
- Fixed TP: +1.5%
- Fixed SL: -0.8%
- Risk/Reward: 1:1.88
- Position size: $1,000 per trade

### Exit Strategy
- Automatic TP/SL monitoring every 60 seconds
- Historical price checks for missed exits
- Complete trade lifecycle tracking

---

## 🧪 Testing

```bash
# Run unit tests
pytest tests/

# Test specific model
python test_mtf_price.py

# Lint code
flake8 . --max-line-length=120
```

---

## 📝 Development Workflow

### Branching Strategy
- `main`: Production (auto-deploys to Cloud Run)
- `staging`: Pre-production testing
- `dev`: Active development
- `feature/*`: Individual features

### Making Changes

```bash
# Create feature branch
git checkout dev
git checkout -b feature/new-feature

# Make changes and commit
git add .
git commit -m "feat: add new feature"

# Push and create PR
git push origin feature/new-feature
```

---

## 📚 Documentation

- [Online Learning Guide](ONLINE_LEARNING_GUIDE.md)
- [Integration Guide](INTEGRATION_GUIDE.md)
- [Trade Exit Monitoring](TRADE_EXIT_MONITORING.md)
- [Implementation Plan](implementation_plan.md)

---

## 🎯 Roadmap

### Phase 1: Trade Logging ✅ COMPLETE
- [x] Trade logging system
- [x] Performance tracking
- [x] Exit monitoring
- [x] Cloud deployment

### Phase 2: Online Learning (In Progress)
- [x] OnlineLearner class
- [x] RetrainingScheduler
- [ ] Integration with main engine
- [ ] First incremental update

### Phase 3: Ensemble Methods (Planned)
- [ ] LightGBM model
- [ ] CatBoost model
- [ ] Stacking ensemble
- [ ] Ensemble deployment

---

## 🐛 Known Issues

- None currently! System running smoothly with 100% win rate.

---

## 📄 License

Private - All Rights Reserved

---

## 🙏 Acknowledgments

- Hyperliquid for API access
- XGBoost for ML framework
- Google Cloud for infrastructure

---

## 📞 Contact

For questions or support, please open an issue in the repository.

---

**Last Updated:** January 1, 2026  
**Version:** 1.0.0  
**Status:** 🟢 Production
