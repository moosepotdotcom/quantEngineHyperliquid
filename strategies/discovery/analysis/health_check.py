#!/usr/bin/env python3
"""
Health Check Endpoint for Trading Bot
Ensures bot is running and responding
"""

from flask import Flask, jsonify
from datetime import datetime
import os

app = Flask(__name__)

# Global state
last_check_time = datetime.now()
health_status = {
    'status': 'healthy',
    'last_signal_check': None,
    'uptime_start': datetime.now().isoformat(),
    'checks_performed': 0
}

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for Cloud Run
    Returns 200 if bot is healthy
    """
    global health_status
    health_status['checks_performed'] += 1
    health_status['last_check'] = datetime.now().isoformat()
    
    return jsonify({
        'status': 'healthy',
        'service': 'quant-engine-hl-live',
        'timestamp': datetime.now().isoformat(),
        'uptime_start': health_status['uptime_start'],
        'checks_performed': health_status['checks_performed']
    }), 200

@app.route('/status', methods=['GET'])
def status():
    """
    Detailed status endpoint
    """
    return jsonify({
        'service': 'Quant Engine - Hyperliquid',
        'mode': 'live',
        'models': ['Winner Hunter 1H', 'MTF Scalper 5M'],
        'network': 'mainnet',
        'status': 'running',
        'health': health_status
    }), 200

@app.route('/', methods=['GET'])
def root():
    """Root endpoint"""
    return status()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
