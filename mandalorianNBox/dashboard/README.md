# 🎛️ Trading Bot Dashboard

Real-time web dashboard for monitoring and controlling your trading bots.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd dashboard
pip install -r requirements.txt
```

### 2. Start the Dashboard

```bash
python app.py
```

### 3. Open in Browser

Go to: **http://127.0.0.1:5000**

## 📊 Features

- ✅ **Risk Control Setup** - Configure stop loss, take profit, leverage limits
- ✅ **Live Trading Log** - Real-time BUY/SELL order tracking
- ✅ **Liquidation Monitoring** - Track liquidations in real-time
- ✅ **Asset Price Tracking** - Monitor prices for multiple assets
- ✅ **Position Monitoring** - View active positions
- ✅ **WebSocket Updates** - Real-time updates without page refresh

## 🔌 Integrating with Your Bots

Add this to your trading bot code:

```python
from dashboard.bot_integration import log_trade, log_info, log_liquidation, get_risk_settings

# Log a trade
log_trade('BUY', 'BTC', price=45000, size=0.1)

# Log info
log_info('Checking liquidations...')

# Log liquidation
log_liquidation('WIF', 'SHORT', 15580)

# Get risk settings
risk = get_risk_settings()
if risk:
    max_loss = risk['stop_loss_percent']
    target = risk['take_profit_percent']
```

## 🎨 Dashboard Components

### Risk Control Modal
- Stop Loss %
- Take Profit %
- Max Leverage
- Daily Max Loss %

### Trading Log
- Real-time order feed
- Color-coded by type (BUY/SELL/INFO/ERROR)
- Auto-scrolling

### Liquidation Monitor
- Recent liquidations
- Long vs Short tracking
- Total liquidation amounts

### Asset Prices
- Real-time price updates
- Multiple asset support
- Price change indicators

## 🔧 Configuration

Edit `app.py` to customize:
- Port (default: 5000)
- Host (default: 127.0.0.1)
- Log retention (default: 1000 entries)

## 📝 API Endpoints

- `GET /api/risk-settings` - Get risk settings
- `POST /api/risk-settings` - Update risk settings
- `GET /api/trading-log` - Get trading log
- `POST /api/add-log` - Add log entry
- `POST /api/add-liquidation` - Add liquidation
- `POST /api/update-price` - Update asset price
- `GET /api/positions` - Get positions
- `GET /api/liquidations` - Get liquidation data

## 🎯 Next Steps

1. Start the dashboard: `python app.py`
2. Configure risk settings in the modal
3. Integrate `bot_integration.py` into your bots
4. Monitor your trades in real-time!

---

**Need help?** Check the integration examples in `bot_integration.py`


