#!/bin/bash
# Complete setup script - installs all remaining packages

echo "🔧 Completing setup..."
echo ""

cd "$(dirname "$0")/.."

# Activate environment
source algotrader/bin/activate

# Upgrade pip first
echo "📦 Upgrading pip..."
./algotrader/bin/pip install --upgrade pip --quiet

# Install core packages (already installed, but ensuring they're there)
echo "📦 Installing core trading packages..."
./algotrader/bin/pip install ccxt pandas numpy schedule requests eth-account hyperliquid-python-sdk --quiet

# Install pandas-ta (might need special handling)
echo "📦 Installing pandas-ta..."
./algotrader/bin/pip install pandas-ta --quiet || echo "⚠️  pandas-ta installation failed - may need manual install"

# Install backtrader
echo "📦 Installing backtrader..."
./algotrader/bin/pip install backtrader --quiet

# Optional packages
echo "📦 Installing optional packages..."
./algotrader/bin/pip install yfinance scikit-learn matplotlib --quiet || echo "⚠️  Some optional packages failed - that's okay"

echo ""
echo "✅ Setup complete!"
echo ""
echo "Installed packages:"
./algotrader/bin/pip list | grep -E "(ccxt|pandas|numpy|schedule|requests|eth-account|hyperliquid|backtrader)" || echo "Run: ./algotrader/bin/pip list to see all packages"
echo ""
echo "Next steps:"
echo "1. Edit dontshare.py and add your HyperLiquid private key"
echo "2. Run: source activate_env.sh"
echo "3. Run: python test_setup.py"
echo "4. Run your bot!"



