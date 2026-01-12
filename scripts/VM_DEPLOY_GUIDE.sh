#!/bin/bash
# Adaptive Shield Trading Bot - VM Startup Script

echo "🚀 Starting Adaptive Shield Trading Bot Installation"

# Update system
apt-get update
apt-get install -y python3-pip git

# Clone or create working directory
mkdir -p /opt/trading-bot
cd /opt/trading-bot

# Copy files (you'll upload these separately)
# Files should be in /opt/trading-bot/

# Install Python dependencies
pip3 install pandas numpy xgboost lightgbm catboost scikit-learn requests python-dotenv ta joblib eth-account

# Install Hyperliquid SDK
pip3 install hyperliquid-python-sdk

# Create environment file
cat > .env << 'EOF'
HYPERLIQUID_WALLET_ADDRESS=0xb01713a6fcdc9419f37db065f0274ea172e4689e
HYPERLIQUID_API_SECRET=f06f4fd2a7516373cc4c8e99afd8c7445b4db0735de0fbe860cfa2b343bfc086
MAX_POSITION_SIZE=0.02
USE_TESTNET=false
EOF

# Create systemd service
cat > /etc/systemd/system/adaptive-shield.service << 'EOFSVC'
[Unit]
Description=Adaptive Shield Trading Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/trading-bot
ExecStart=/usr/bin/python3 live_trading_engine.py --live --mainnet
Restart=always
RestartSec=10
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
EOFSVC

# Enable and start service
systemctl daemon-reload
systemctl enable adaptive-shield
systemctl start adaptive-shield

echo "✅ Trading bot installed and started"
echo "Check logs with: journalctl -u adaptive-shield -f"
