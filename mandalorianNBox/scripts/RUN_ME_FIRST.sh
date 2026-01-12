#!/bin/bash
# 🚀 ONE-COMMAND SETUP - Run this to finish installation

echo "🔧 Finishing package installation..."
echo ""

cd "$(dirname "$0")/.."

# Activate and install
source algotrader/bin/activate

echo "📦 Installing/upgrading packages..."
./algotrader/bin/pip install --upgrade pip --quiet
./algotrader/bin/pip install ccxt pandas numpy schedule requests eth-account hyperliquid-python-sdk backtrader --quiet --no-cache-dir

echo ""
echo "✅ Installation complete!"
echo ""
echo "📝 Next steps:"
echo "1. Edit dontshare.py and add your HyperLiquid private key"
echo "2. Run: source activate_env.sh"
echo "3. Run: python test_setup.py"
echo "4. Run your bot: python 10_day10_bots/day10_hyperliquid/10_bollinger_bot.py"
echo ""



