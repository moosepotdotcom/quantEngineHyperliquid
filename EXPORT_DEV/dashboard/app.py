from flask import Flask, render_template, jsonify, request, session, redirect, url_for
import os
import secrets
from trading_thread import TradingThread

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Initialize Trading Thread (Global)
# Default to Testnet for safety. Can be changed via ENV or Args in production.
# For Dashboard, we assume Live=True (but Testnet) to show full capabilities.
# Default to Mainnet for Real Trading (User Requirement)
trading_thread = TradingThread(enable_live=True, testnet=False)
trading_thread.start()

# Mock Login Credentials (Change for Prod)
ADMIN_PASSWORD = "admin" 

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['password'] == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return "Incorrect Password", 401
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# --- API ENDPOINTS ---

@app.route('/api/status')
def get_status():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    state = trading_thread.get_state()
    return jsonify(state)

@app.route('/api/execute', methods=['POST'])
def execute_trade():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.json
    action = data.get('action') # 'buy' or 'sell'
    
    if action == 'buy':
        trading_thread.manual_buy()
        return jsonify({'status': 'Buy signal sent'})
    elif action == 'sell':
        trading_thread.manual_sell()
        return jsonify({'status': 'Sell signal sent'})
        
    return jsonify({'error': 'Invalid action'}), 400

@app.route('/api/close_all', methods=['POST'])
def close_all():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    trading_thread.emergency_close()
    return jsonify({'status': 'Emergency stop triggered'})

@app.route('/api/fetch_balance', methods=['POST'])
def fetch_balance():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Trigger a balance update log (The thread updates continuously, 
    # but we can log that a manual check was requested)
    trading_thread.add_log("🔄 Manual Balance Fetch Requested")
    
    # Return current state immediately
    state = trading_thread.get_state()
    return jsonify(state)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print("🚀 Web Dashboard Starting...")
    print(f"   Running on http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
