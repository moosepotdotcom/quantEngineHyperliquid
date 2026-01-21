# 🛡️ MANDALORIAN ENGINE

**83.5% Win Rate | +134.80% ROI | This is the Way**

## 📦 Complete Package

This directory contains everything needed to run the Mandalorian Engine with its themed dashboard.

### Package Contents

```
MANDALORIAN_ENGINE/
├── models/                    # 6 ML models (MTF Scalper + Winner Hunter)
├── utils/                     # Feature engineering & data fetching
├── dashboard/                 # Mandalorian-themed web dashboard
│   └── index.html            # Dashboard UI
├── trades/                    # Trade history & state (auto-created)
├── logs/                      # Log files (auto-created)
├── quant_engine.py           # Core ML engine
├── golden_config.json        # Verified configuration
├── mandalorian_state.py      # State management backend
├── dashboard_server.py       # Flask API server
├── live_paper_trading.py     # Live trading script
├── Dockerfile                # Cloud deployment
├── deploy.sh                 # Deployment script
├── requirements.txt          # Dependencies
└── README.md                 # This file
```

## 🎯 Dashboard Features

- **Live Trade Tracking**: Real-time position monitoring
- **Confidence Scores**: Separate gauges for LONG/SHORT signals
- **Trade History**: Last 20 trades with PnL
- **SL/TP Levels**: Live stop-loss and take-profit prices
- **Paper Mode Badge**: Clear indication of trading mode
- **Circuit Breaker Alert**: Visual warning when breaker is active
- **Mandalorian Theme**: Dark green terminal aesthetic

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start Dashboard Server
```bash
python dashboard_server.py
```

### 3. Open Dashboard
Navigate to: `http://localhost:5000`

### 4. Start Paper Trading (in another terminal)
```bash
python live_paper_trading.py
```

## ⚙️ Configuration

### Confidence Thresholds

Edit `mandalorian_state.py` to adjust:
```python
'thresholds': {
    'long': 0.45,   # 45% confidence for LONG
    'short': 0.45   # 45% confidence for SHORT
}
```

### Trading Parameters

Edit `live_paper_trading.py`:
- **Leverage**: 400x
- **Position Size**: 0.5 BTC
- **Take Profit**: 1.5%
- **Stop Loss**: 0.8%

## 🛡️ Shields & Protection

1. **Mandalorian Filter**: Blocks falling knife trades
2. **AI Smart Filter**: Blocks oversold shorts
3. **Circuit Breaker**: 4-hour cooldown after 2 losses

## 📊 Backtest Performance

- **Period**: Jan 2-16, 2026 (15 days)
- **Total Trades**: 300
- **Wins**: 217 ✅
- **Losses**: 43 ❌
- **Win Rate**: 83.5%
- **ROI**: +134.80%

## 🌐 Cloud Deployment

See `ML_ENGINE_DEPLOY/` directory for Google Cloud Run deployment.

## 📝 API Endpoints

- `GET /` - Dashboard UI
- `GET /api/state` - Current engine state
- `GET /api/trades` - Trade history
- `GET /api/health` - Health check

## 🎨 Dashboard Customization

The dashboard uses a Mandalorian theme with:
- **Primary Color**: `#00ff88` (green)
- **Background**: Dark blue gradient
- **Accents**: Gold (`#ffaa00`) for warnings
- **Font**: Courier New (monospace)

Edit `dashboard/index.html` to customize colors and layout.

---

**This is the Way** 🛡️

*Generated: 2026-01-16*
*Win Rate: 83.5%*
*ROI: +134.80%*
