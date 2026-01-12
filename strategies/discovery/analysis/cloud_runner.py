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

# Global engine thread for health monitoring
engine_thread = None

@app.route('/health')
def health():
    """
    Health check endpoint for Cloud Run.
    Returns 500 if trading thread has died (CRITICAL SAFETY FEATURE).
    """
    global engine_thread
    
    # If thread hasn't started yet, we are starting up
    if engine_thread is None:
        return jsonify({"status": "starting"}), 200
        
    # Check if thread is alive
    if not engine_thread.is_alive():
        print("❌ CRITICAL: Trading thread is DEAD. Signaling unhealthy to Cloud Run.")
        return jsonify({
            "status": "unhealthy", 
            "reason": "Trading thread died",
            "action": "Cloud Run should restart this container"
        }), 500
        
    return jsonify({"status": "healthy", "thread": "alive"})

@app.route('/')
def index():
    return jsonify({
        "service": "Quant Engine - Hyperliquid",
        "status": "running",
        "mode": "live" if ENABLE_LIVE_TRADING else "paper",
        "network": "testnet" if USE_TESTNET else "mainnet",
        "models": ["Winner Hunter 1H", "MTF Scalper 5M"],
        "version": "1.2.0-elastic"
    })

@app.route('/learning_state')
def learning_state():
    """Expose the current state of the Elastic Threshold Engine"""
    global engine_instance
    if not engine_instance:
        return jsonify({"status": "Engine not initialized"}), 503
    
    # Extract engine from LiveTradingEngine wrapper if needed
    paper_engine = engine_instance.paper_engine if hasattr(engine_instance, 'paper_engine') else engine_instance
    
    return jsonify({
        "Winner Hunter (1H)": {
            "mode": paper_engine.wh_elastic.mode,
            "active_threshold_long": f"{paper_engine.wh_elastic.active_threshold_long:.2%}",
            "active_threshold_short": f"{paper_engine.wh_elastic.active_threshold_short:.2%}",
            "max_conf_24h_long": f"{paper_engine.wh_elastic.max_conf_24h_long:.2%}",
            "max_conf_24h_short": f"{paper_engine.wh_elastic.max_conf_24h_short:.2%}",
            "surgical_target_long": f"{paper_engine.winner_threshold_long:.2%}",
            "surgical_target_short": f"{paper_engine.winner_threshold_short:.2%}"
        },
        "MTF Scalper (5M)": {
            "mode": paper_engine.mtf_elastic.mode,
            "active_threshold_long": f"{paper_engine.mtf_elastic.active_threshold_long:.2%}",
            "active_threshold_short": f"{paper_engine.mtf_elastic.active_threshold_short:.2%}",
            "max_conf_24h_long": f"{paper_engine.mtf_elastic.max_conf_24h_long:.2%}",
            "max_conf_24h_short": f"{paper_engine.mtf_elastic.max_conf_24h_short:.2%}",
            "surgical_target_long": f"{paper_engine.mtf_threshold_long:.2%}",
            "surgical_target_short": f"{paper_engine.mtf_threshold_short:.2%}"
        },
        "last_trade_time": paper_engine.wh_elastic.last_trade_time.isoformat()
    })

@app.route('/balance')
def get_balance():
    """Fetch live balance from exchange"""
    try:
        from hyperliquid_live_trader import HyperliquidTrader
        trader = HyperliquidTrader(testnet=USE_TESTNET)
        account = trader.get_account_info()
        return jsonify({
            "balance": account['balance'],
            "wallet": trader.wallet_address,
            "network": "testnet" if USE_TESTNET else "mainnet"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/status')
def status():
    """Get current trading status"""
    return jsonify({
        "live_trading": ENABLE_LIVE_TRADING,
        "testnet": USE_TESTNET,
        "wallet": os.getenv('HYPERLIQUID_WALLET_ADDRESS', 'not_set'),
        "max_position": os.getenv('MAX_POSITION_SIZE', '0.01'),
        "daily_limit": os.getenv('DAILY_LOSS_LIMIT', '5.0'),
        "version": "1.1.0-bidirectional"
    })

@app.route('/confidence')
def confidence():
    """Show live model confidence analytics"""
    try:
        from utils.trade_logger import get_logger
        logger = get_logger()
        stats_24h = logger.get_confidence_stats(hours=24)
        stats_1h = logger.get_confidence_stats(hours=1)
        
        return jsonify({
            "last_24h": stats_24h,
            "last_1h": stats_1h,
            "thresholds": {
                "Winner Hunter (1H)": "L:34.1%, S:47.9%",
                "MTF Scalper (5M)": "L:59.9%, S:68.9%"
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/advisor')
def advisor():
    """Recommend threshold changes or show current Learning state"""
    global engine_instance
    if not engine_instance:
        return jsonify({"status": "Engine not initialized"}), 503
        
    paper_engine = engine_instance.paper_engine if hasattr(engine_instance, 'paper_engine') else engine_instance
    
    recommendations = {}
    for manager in [paper_engine.wh_elastic, paper_engine.mtf_elastic]:
        max_seen = max(manager.max_conf_24h_long, manager.max_conf_24h_short)
        recommendations[manager.model_name] = {
            "current_mode": manager.mode,
            "active_threshold_long": f"{manager.active_threshold_long:.2%}",
            "active_threshold_short": f"{manager.active_threshold_short:.2%}",
            "max_seen_24h": f"{max_seen:.2%}",
            "status": "Learning (Elastic)" if manager.mode == "ELASTIC" else "Surgical (Protecting Capital)"
        }
        
    return jsonify(recommendations)

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
    """Run the trading engine in background thread (In-Process)"""
    global engine_instance
    
    if ENABLE_LIVE_TRADING:
        from live_trading_engine import LiveTradingEngine
        print(f"🚀 Starting LIVE trading engine (In-Process, testnet={USE_TESTNET})")
        engine_instance = LiveTradingEngine(enable_live=True, testnet=USE_TESTNET)
        engine_instance.run_continuous()
    else:
        from quant_engine import TradingEngine
        print("📝 Starting PAPER trading engine (In-Process)")
        engine_instance = TradingEngine()
        # TradingEngine uses run_continuous_monitoring
        engine_instance.run_continuous_monitoring(max_hours=999999)

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

