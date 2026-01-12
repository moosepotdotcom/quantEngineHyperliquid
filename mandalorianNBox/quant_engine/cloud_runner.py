#!/usr/bin/env python3
"""
🌐 Cloud Run Wrapper
Runs trading engine with HTTP health check endpoint for Cloud Run.
"""

import os
import threading
from flask import Flask, jsonify
import subprocess

app = Flask(__name__)

# Global status
status = {
    'running': True,
    'trades': 0,
    'last_check': None
}

@app.route('/')
def home():
    return jsonify({
        'service': 'Quant Engine',
        'status': 'running' if status['running'] else 'stopped',
        'trades_executed': status['trades'],
        'last_check': status['last_check']
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'}), 200

def run_trading_engine():
    """Run the trading engine in background"""
    subprocess.run(['python', 'quant_engine/research/full_sandbox.py'])

if __name__ == '__main__':
    # Start trading engine in background thread
    engine_thread = threading.Thread(target=run_trading_engine, daemon=True)
    engine_thread.start()
    
    # Run Flask server on PORT
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
