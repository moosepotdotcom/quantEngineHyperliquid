#!/usr/bin/env python3
"""
🛡️ MANDALORIAN ENGINE - Enhanced Dashboard Server
Flask server with login protection and advanced features
"""

from flask import Flask, jsonify, send_from_directory, request, session, redirect, url_for
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from functools import wraps
import requests
import sys
import os
import threading
import time
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mandalorian_state import MandalorianState

app = Flask(__name__, static_folder='dashboard', static_url_path='')
app.secret_key = 'mandalorian-this-is-the-way-secret-key-2026'  # Change this in production
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

state_manager = MandalorianState()

# Background thread to push live updates
def background_thread():
    """Background thread to push live state updates via WebSocket"""
    while True:
        time.sleep(2)  # Update every 2 seconds
        state_manager.load_state()
        state = state_manager.get_state()
        socketio.emit('state_update', state)

# Login credentials (in production, use environment variables or database)
VALID_USERNAME = "mandalorian"
VALID_PASSWORD = "thisIsTheWay2026"

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'logged_in' not in session:
        return send_from_directory('dashboard', 'login.html')
    return send_from_directory('dashboard', 'index.html')

@app.route('/api/login', methods=['POST'])
def login():
    """Login endpoint"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if username == VALID_USERNAME and password == VALID_PASSWORD:
        session['logged_in'] = True
        session['username'] = username
        return jsonify({'success': True, 'message': 'Login successful'})
    
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    """Logout endpoint"""
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out'})

@app.route('/api/state')
@login_required
def get_state():
    """Get current engine state"""
    state_manager.load_state()  # Reload fresh data from file
    return jsonify(state_manager.get_state())

@app.route('/api/trades')
@login_required
def get_trades():
    """Get trade history"""
    state_manager.load_state()  # Reload fresh data
    return jsonify(state_manager.get_trade_history())

@app.route('/api/performance')
@login_required
def get_performance():
    """Get performance metrics"""
    trades = state_manager.get_trade_history()
    
    if not trades:
        return jsonify({
            'total_pnl': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'largest_win': 0,
            'largest_loss': 0,
            'avg_duration': 0,
            'daily_roi': 0,
            'weekly_roi': 0,
            'monthly_roi': 0
        })
    
    wins = [t for t in trades if t.get('exit_reason') == 'TP']
    losses = [t for t in trades if t.get('exit_reason') == 'SL']
    
    total_pnl = sum(t.get('pnl', 0) for t in trades)
    avg_win = sum(t.get('pnl', 0) for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t.get('pnl', 0) for t in losses) / len(losses) if losses else 0
    largest_win = max((t.get('pnl', 0) for t in wins), default=0)
    largest_loss = min((t.get('pnl', 0) for t in losses), default=0)
    
    # Calculate average duration (in minutes)
    durations = []
    for t in trades:
        if 'timestamp' in t and 'exit_timestamp' in t:
            try:
                start = datetime.fromisoformat(t['timestamp'])
                end = datetime.fromisoformat(t['exit_timestamp'])
                durations.append((end - start).total_seconds() / 60)
            except:
                pass
    
    avg_duration = sum(durations) / len(durations) if durations else 0
    
    # Calculate ROI for different periods
    initial_balance = 100000.0
    current_balance = state_manager.get_state()['balance']
    
    # Simple ROI calculations (can be enhanced with time-based filtering)
    daily_roi = ((current_balance - initial_balance) / initial_balance) * 100 / 15  # Assuming 15 days
    weekly_roi = daily_roi * 7
    monthly_roi = daily_roi * 30
    
    return jsonify({
        'total_pnl': total_pnl,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'largest_win': largest_win,
        'largest_loss': largest_loss,
        'avg_duration': avg_duration,
        'daily_roi': daily_roi,
        'weekly_roi': weekly_roi,
        'monthly_roi': monthly_roi
    })

@app.route('/api/balance_history')
@login_required
def get_balance_history():
    """Get balance history for chart"""
    trades = state_manager.get_trade_history()
    
    if not trades:
        return jsonify([])
    
    # Build cumulative balance history
    balance_history = []
    current_balance = 100000.0
    
    for trade in trades:
        if 'exit_timestamp' in trade and 'pnl' in trade:
            current_balance += trade['pnl']
            balance_history.append({
                'timestamp': trade['exit_timestamp'],
                'balance': current_balance,
                'pnl': trade['pnl']
            })
    
    return jsonify(balance_history)

@app.route('/api/market_data')
@login_required
def get_market_data():
    """Get live market data"""
    try:
        # Fetch from Hyperliquid or other source
        url = "https://api.hyperliquid.xyz/info"
        payload = {
            "type": "metaAndAssetCtxs"
        }
        response = requests.post(url, json=payload, timeout=5)
        data = response.json()
        
        # Extract BTC data (simplified)
        btc_price = 95000  # Placeholder - parse from actual response
        price_24h_change = 2.5  # Placeholder
        
        return jsonify({
            'price': btc_price,
            'change_24h': price_24h_change,
            'timestamp': datetime.now().isoformat()
        })
    except:
        return jsonify({
            'price': 0,
            'change_24h': 0,
            'timestamp': datetime.now().isoformat()
        })

@app.route('/api/alerts')
@login_required
def get_alerts():
    """Get recent alerts (shield activations, circuit breaker)"""
    # This would be populated by the trading engine
    # For now, return empty list
    return jsonify([])

@app.route('/api/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Get or update settings"""
    if request.method == 'POST':
        data = request.get_json()
        state = state_manager.get_state()
        
        if 'thresholds' in data:
            state['thresholds'] = data['thresholds']
        if 'shields' in data:
            state['shields'] = data['shields']
        
        state_manager.save_state()
        return jsonify({'success': True})
    
    return jsonify(state_manager.get_state())

@app.route('/api/health')
def health():
    """Health check"""
    return jsonify({'status': 'ok', 'engine': 'mandalorian'})

if __name__ == '__main__':
    print("=" * 80)
    print("🛡️ MANDALORIAN ENGINE - Enhanced Dashboard Server")
    print("=" * 80)
    print("\n📡 Starting server on http://localhost:5001")
    print(f"   Username: {VALID_USERNAME}")
    print(f"   Password: {VALID_PASSWORD}")
    print("\n   🔴 LIVE WebSocket Feed: Enabled")
    print("   Open your browser and navigate to the URL above")
    print("\n   Press Ctrl+C to stop\n")
    
    # Start background thread for live updates
    thread = threading.Thread(target=background_thread, daemon=True)
    thread.start()
    
    # Use production settings for Cloud Run
    port = int(os.getenv('PORT', 5001))
    socketio.run(app, host='0.0.0.0', port=port, debug=False, use_reloader=False, log_output=True)
