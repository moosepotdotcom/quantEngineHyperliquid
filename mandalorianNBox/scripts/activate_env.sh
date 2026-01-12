#!/bin/bash
# Quick activation script for the trading bot environment

cd "$(dirname "$0")/.."
source algotrader/bin/activate
echo "✅ Environment activated!"
echo "You're now in the algotrader environment"
echo ""
echo "To run a bot:"
echo "  python 10_day10_bots/day10_hyperliquid/10_bollinger_bot.py"
echo ""
echo "To deactivate: type 'deactivate'"



