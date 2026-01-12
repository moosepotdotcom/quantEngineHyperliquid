#!/usr/bin/env python3
"""
Cloud Run Wrapper - Makes trading bot compatible with Cloud Run
"""
import os
import threading
import sys
from flask import Flask, jsonify
from dotenv import load_dotenv

# Load environment variables (Critical for Cloud Run which doesn't auto-load .env)
load_dotenv()

from live_trading_engine import LiveTradingEngine

app = Flask(__name__)

# Global trading engine
trading_engine = None
trading_thread = None

def run_trading_bot():
    """Run trading bot in background thread"""
    global trading_engine
    try:
        print("🚀 Starting Cloud Run Trading Bot...")
        # Force Enable Live Trading (controlled by internal logic and keys availability)
        # Note: LiveTradingEngine will fallback to paper if keys are missing
        trading_engine = LiveTradingEngine(enable_live=True, testnet=False)
        trading_engine.run_continuous()
    except Exception as e:
        print(f"❌ Trading bot error: {e}")
        import traceback
        traceback.print_exc()

@app.route('/')
def home():
    """Health check endpoint"""
    return jsonify({
        'status': 'running',
        'service': 'Adaptive Shield Trading Bot (V1 Production)',
        'version': '1.0.1',
        'win_rate': '92.9% (Trio Model)'
    })

@app.route('/health')
def health():
    """Health check for Cloud Run"""
    return jsonify({'status': 'healthy'})

@app.route('/status')
def status():
    """Get bot status"""
    global trading_engine
    if trading_engine:
        active_pos_count = 0
        mode = 'UNKNOWN'
        
        try:
            if trading_engine.enable_live and trading_engine.live_trader:
                mode = 'LIVE'
                active_pos_count = len(trading_engine.live_trader.active_positions)
            elif hasattr(trading_engine, 'paper_engine') and hasattr(trading_engine.paper_engine, 'exit_monitor'):
                mode = 'PAPER'
                active_pos_count = len(trading_engine.paper_engine.exit_monitor.open_trades)
        except Exception as e:
            print(f"⚠️ Error reading status: {e}")
            
        return jsonify({
            'bot_running': True,
            'mode': mode,
            'active_positions': active_pos_count
        })
    return jsonify({'bot_running': False})

if __name__ == '__main__':
    # Start trading bot in background thread
    trading_thread = threading.Thread(target=run_trading_bot, daemon=True)
    trading_thread.start()
    
    # Start Flask server for Cloud Run
    port = int(os.environ.get('PORT', 8080))
    print(f"🌍 Starting Web Server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
