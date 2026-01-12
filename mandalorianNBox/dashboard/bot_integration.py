"""
Bot Integration Helper
Use this in your trading bots to send data to the dashboard
"""

import requests
import json
from datetime import datetime

DASHBOARD_URL = "http://127.0.0.1:5000"

def log_trade(order_type, symbol, price=None, size=None, message=""):
    """Log a trade to the dashboard"""
    try:
        requests.post(
            f"{DASHBOARD_URL}/api/add-log",
            json={
                'type': order_type,  # 'BUY' or 'SELL'
                'symbol': symbol,
                'price': price,
                'size': size,
                'message': message
            },
            timeout=1
        )
    except:
        pass  # Dashboard might not be running

def log_info(message):
    """Log an info message"""
    try:
        requests.post(
            f"{DASHBOARD_URL}/api/add-log",
            json={
                'type': 'INFO',
                'message': message
            },
            timeout=1
        )
    except:
        pass

def log_liquidation(symbol, side, amount):
    """Log a liquidation event"""
    try:
        requests.post(
            f"{DASHBOARD_URL}/api/add-liquidation",
            json={
                'symbol': symbol,
                'side': side,  # 'LONG' or 'SHORT'
                'amount': amount
            },
            timeout=1
        )
    except:
        pass

def update_price(symbol, price, change=0):
    """Update asset price"""
    try:
        requests.post(
            f"{DASHBOARD_URL}/api/update-price",
            json={
                'symbol': symbol,
                'price': price,
                'change': change
            },
            timeout=1
        )
    except:
        pass

def get_risk_settings():
    """Get current risk settings from dashboard"""
    try:
        response = requests.get(f"{DASHBOARD_URL}/api/risk-settings", timeout=1)
        return response.json()
    except:
        return None

# Example usage in your bot:
"""
from dashboard.bot_integration import log_trade, log_info, log_liquidation, get_risk_settings

# In your bot code:
log_trade('BUY', 'BTC', price=45000, size=0.1)
log_info('Checking liquidations...')
log_liquidation('WIF', 'SHORT', 15580)

# Get risk settings
risk = get_risk_settings()
if risk:
    max_loss = risk['stop_loss_percent']
    target = risk['take_profit_percent']
"""


