#!/bin/bash
# Quick script to run backtest

cd "$(dirname "$0")/.."

echo "🚀 Starting Backtest..."
echo ""

# Activate environment
source algotrader/bin/activate

# Run backtest
python backtest_ready.py

echo ""
echo "✅ Done!"

