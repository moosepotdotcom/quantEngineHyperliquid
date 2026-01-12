"""
Cloud Runner - Single entry point for Google Cloud Run

Runs:
1. Trading Bot (background thread)
2. Dashboard Monitor (Flask on PORT)

This allows the entire system to run as a single Cloud Run service.
"""

import os
import sys
import threading
import time

# Cloud Run requires a web server on the specified PORT
PORT = int(os.environ.get('PORT', 8080))


def run_trading_bot():
    """Run the trading bot in background"""
    print("🚀 Starting Trading Bot in background...")
    import trading_agent
    trading_agent.run_sandbox_mode()


def run_dashboard():
    """Run the dashboard on the Cloud Run port"""
    print(f"🖥️ Starting Dashboard on port {PORT}...")
    from dashboard.live_monitor import app, setup_templates
    setup_templates()
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)


if __name__ == '__main__':
    print("=" * 60)
    print("☁️  CLOUD RUNNER - AI Trading System")
    print("=" * 60)
    
    # Start trading bot in background thread
    bot_thread = threading.Thread(target=run_trading_bot, daemon=True)
    bot_thread.start()
    
    # Give bot a moment to initialize
    time.sleep(3)
    
    # Run dashboard in main thread (Cloud Run needs this)
    run_dashboard()
