#!/usr/bin/env python3
"""
Flask wrapper for Cloud Run compatibility
Runs trading engine in background thread while serving health endpoint
Supports both paper trading and live trading modes
"""

import os
import threading
import subprocess
from flask import Flask, jsonify

app = Flask(__name__)

# Get configuration from environment
ENABLE_LIVE_TRADING = os.getenv('ENABLE_LIVE_TRADING', 'false').lower() == 'true'
USE_TESTNET = os.getenv('USE_TESTNET', 'true').lower() == 'true'

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/')
def index():
    return jsonify({
        "service": "Quant Engine - Hyperliquid",
        "status": "running",
        "mode": "live" if ENABLE_LIVE_TRADING else "paper",
        "network": "testnet" if USE_TESTNET else "mainnet",
        "models": ["Winner Hunter 1H", "MTF Scalper 5M"]
    })

@app.route('/status')
def status():
    """Get current trading status"""
    return jsonify({
        "live_trading": ENABLE_LIVE_TRADING,
        "testnet": USE_TESTNET,
        "wallet": os.getenv('HYPERLIQUID_WALLET_ADDRESS', 'not_set'),
        "max_position": os.getenv('MAX_POSITION_SIZE', '0.01'),
        "daily_limit": os.getenv('DAILY_LOSS_LIMIT', '5.0')
    })

@app.route('/test_trade')
def test_trade():
    """Execute a test trade to verify system works"""
    if not ENABLE_LIVE_TRADING:
        return jsonify({"error": "Live trading not enabled"}), 400
    
    try:
        from hyperliquid_live_trader import HyperliquidTrader
        import time
        
        # Initialize trader
        trader = HyperliquidTrader(testnet=USE_TESTNET)
        
        # Check balance
        account = trader.get_account_info()
        if account['balance'] < 1:
            return jsonify({"error": "Insufficient balance", "balance": account['balance']}), 400
        
        # Execute test trade
        buy_order = trader.place_market_order('BTC', True, 0.001)
        if not buy_order:
            return jsonify({"error": "Buy order failed"}), 500
        
        time.sleep(3)
        
        sell_order = trader.place_market_order('BTC', False, 0.001)
        if not sell_order:
            return jsonify({"error": "Sell order failed", "warning": "Position may still be open"}), 500
        
        return jsonify({
            "status": "success",
            "message": "Test trade completed",
            "buy_order": buy_order,
            "sell_order": sell_order
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def run_trading_engine():
    """Run the trading engine in background"""
    if ENABLE_LIVE_TRADING:
        # Run live trading engine
        print(f"🚀 Starting LIVE trading engine (testnet={USE_TESTNET})")
        cmd = ['python', 'live_trading_engine.py', '--live']
        if not USE_TESTNET:
            cmd.append('--mainnet')
        subprocess.run(cmd)
    else:
        # Run paper trading only
        print("📝 Starting PAPER trading engine")
        subprocess.run(['python', 'quant_engine.py'])

if __name__ == '__main__':
    print("="*70)
    print("🚀 Quant Engine - Cloud Run")
    print("="*70)
    print(f"Mode: {'LIVE TRADING' if ENABLE_LIVE_TRADING else 'PAPER TRADING'}")
    print(f"Network: {'TESTNET' if USE_TESTNET else 'MAINNET'}")
    print(f"Wallet: {os.getenv('HYPERLIQUID_WALLET_ADDRESS', 'not_set')}")
    print("="*70)
    
    # Start trading engine in background thread
    engine_thread = threading.Thread(target=run_trading_engine, daemon=True)
    engine_thread.start()
    
    # Start Flask server
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

