# 🎛️ Dashboard Quick Start

## 🚀 Start Your Dashboard (2 Steps)

### Step 1: Install Dashboard Dependencies

```bash
cd "/Users/alifiyaa/Downloads/ATC Bootcamp Code 2025"
source algotrader/bin/activate
pip install Flask flask-socketio python-socketio eventlet
```

### Step 2: Start the Dashboard

**Option A: Quick Script**
```bash
./START_DASHBOARD.sh
```

**Option B: Manual**
```bash
cd dashboard
python app.py
```

## 🌐 Access Your Dashboard

Once started, open your browser to:
**http://127.0.0.1:5000**

## 📊 What You'll See

- **Risk Control Setup Modal** - Configure stop loss, take profit, leverage
- **Live Trading Log** - Real-time BUY/SELL orders
- **Liquidation Monitor** - Track liquidations
- **Asset Prices** - Real-time price updates
- **Stats Dashboard** - Key metrics

## 🔌 Connect Your Bots

Add this to your trading bot code:

```python
from dashboard.bot_integration import log_trade, log_info, log_liquidation

# In your bot:
log_trade('BUY', 'BTC', price=45000, size=0.1)
log_info('Checking liquidations...')
log_liquidation('WIF', 'SHORT', 15580)
```

## 🛑 Stop the Dashboard

Press `Ctrl+C` in the terminal

## 📝 Dashboard Files

- `dashboard/app.py` - Main server
- `dashboard/templates/dashboard.html` - Web interface
- `dashboard/bot_integration.py` - Bot helper functions
- `START_DASHBOARD.sh` - Quick start script

## 🎯 Quick Commands

```bash
# Start dashboard
./START_DASHBOARD.sh

# Or manually
cd dashboard
python app.py
```

---

**Ready?** Run `./START_DASHBOARD.sh` and open http://127.0.0.1:5000 in your browser!

