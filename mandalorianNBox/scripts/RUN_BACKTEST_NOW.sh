#!/bin/bash
# 🚀 Quick script to get backtesting running immediately

echo "🧪 Setting up backtesting environment..."
echo ""

cd "$(dirname "$0")/.."

# Activate environment
if [ -d "algotrader" ]; then
    source algotrader/bin/activate
    echo "✅ Environment activated"
else
    echo "⚠️  Environment not found, using system Python"
fi

# Install backtesting packages
echo ""
echo "📦 Installing backtesting packages..."
pip install backtrader matplotlib pandas numpy --quiet

# Test setup
echo ""
echo "🧪 Testing backtesting setup..."
python test_backtest.py

# Run backtest
echo ""
echo "🚀 Running backtest..."
python 13_backtesting_fixed.py

echo ""
echo "✅ Done! Check results above."

