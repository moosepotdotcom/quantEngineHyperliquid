#!/bin/bash
# Quick Start Script for Live Trading

echo "🚀 AI Trading Bot - Live Trading Quick Start"
echo "=============================================="
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.live_trading .env
    echo "✅ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your private key!"
    echo "   Run: nano .env"
    echo "   Add your HYPERLIQUID_API_SECRET"
    echo ""
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install python-dotenv eth-account web3 --quiet

echo ""
echo "✅ Setup complete!"
echo ""
echo "🎯 Choose your mode:"
echo ""
echo "1️⃣  Paper Trading Only (No real money)"
echo "   python live_trading_engine.py"
echo ""
echo "2️⃣  Live Trading on TESTNET (Fake money, real testing)"
echo "   python live_trading_engine.py --live"
echo ""
echo "3️⃣  Live Trading on MAINNET (REAL MONEY - Be careful!)"
echo "   python live_trading_engine.py --live --mainnet"
echo ""
echo "💡 Recommendation: Start with option 2 (testnet) for 24 hours"
echo ""
echo "📖 Full guide: LIVE_TRADING_SETUP.md"
echo ""
