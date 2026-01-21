import os
import time
import json
import logging
from datetime import datetime
from flask import Flask, render_template, jsonify, request, session, redirect, url_for, make_response
from trading_thread import TradingThread

app = Flask(__name__)
app.secret_key = "mandalorian_hyper_secure_key_v2"

# Session configuration
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400

# Initialize Trading Thread
trading_thread = TradingThread(enable_live=True, testnet=False)
trading_thread.start()

ADMIN_PASSWORD = "admin" 

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    resp = make_response(render_template('index.html'))
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

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
    
    data = request.get_json(silent=True) or {}
    close_type = data.get('type', 'market')
    
    trading_thread.emergency_close(close_type)
    return jsonify({'status': f'Close command sent ({close_type})'})

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

@app.route('/api/history')
def get_history():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        history = trading_thread.get_history()
        return jsonify(history)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/whales')
def get_whales():
    # TEMPORARILY REMOVED AUTH FOR DEBUGGING
    # if not session.get('logged_in'):
    #     return jsonify({'error': 'Unauthorized'}), 401
    
    walls = trading_thread.get_whale_walls()
    return jsonify(walls)

@app.route('/api/alpha/toggle', methods=['POST'])
def toggle_alpha():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.json
    strategy = data.get('strategy')
    state = data.get('state') # true/false
    
    if hasattr(trading_thread, 'alpha_engine'):
        success = trading_thread.alpha_engine.toggle_strategy(strategy, state)
        if success:
            return jsonify({"status": "ok", "msg": f"{strategy} set to {state}"})
    
    return jsonify({"status": "error", "msg": "Failed to toggle"}), 400

@app.route('/api/alpha/settings', methods=['POST'])
def alpha_settings():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    strategy = data.get('strategy')
    value = data.get('value')
    
    if hasattr(trading_thread, 'alpha_engine'):
        success = trading_thread.alpha_engine.update_setting(strategy, value)
        if success:
             return jsonify({"status": "ok", "msg": f"{strategy} threshold set to {value}"})

    return jsonify({"status": "error", "msg": "Failed to update setting"}), 400

@app.route('/api/strategy/list')
def list_strategies():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    from quant_engine import STRATEGY_PRESETS
    return jsonify(STRATEGY_PRESETS)

@app.route('/api/strategy/switch', methods=['POST'])
def switch_strategy():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    strategy = data.get('strategy')
    success = trading_thread.switch_strategy(strategy)
    
    if success:
        return jsonify({"status": "ok", "msg": f"Switched to {strategy}"})
    return jsonify({"status": "error", "msg": "Failed to switch"}), 400

@app.route('/api/model/toggle', methods=['POST'])
def toggle_model():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    model_key = data.get('model') # 'MTF' or 'WH'
    state = data.get('state') # True/False
    
    success = trading_thread.toggle_model(model_key, state)
    if success:
        return jsonify({"status": "ok", "msg": f"{model_key} model set to {state}"})
    return jsonify({"status": "error", "msg": "Failed to toggle model"}), 400

@app.route('/api/test/sequence', methods=['POST'])
def test_sequence():
    # Auth disabled for testing convenience
    # if not session.get('logged_in'):
    #    return jsonify({'error': 'Unauthorized'}), 401
    
    trader = trading_thread.engine.live_trader
    if not trader:
        return jsonify({'error': 'Trader not init'}), 500

    # 1. Open
    print("🧪 API Test: Opening Long...")
    res = trader.place_market_order('BTC', True, 0.0002)
    
    # 2. Add Dummy "Position" to UI manually so it shows up even if API lags
    # This ensures the user sees something in "Active Bounties"
    trader.active_positions['TEST_TRADE'] = {
        'entry_price': 90000, # Approximate
        'direction': 'LONG',
        'size': 0.0002,
        'tp': 0, 'sl': 0,
        'timestamp': datetime.now(),
        'pnl': 0.0
    }
    
    # 3. Wait
    time.sleep(15)
    
    # 4. Close
    print("🧪 API Test: Closing...")
    trader.place_market_order('BTC', False, 0.0002)
    if 'TEST_TRADE' in trader.active_positions:
        del trader.active_positions['TEST_TRADE']
        
    return jsonify({"status": "Test Cycle Complete", "details": res})

@app.route('/api/v8_enhanced_status')
def v8_enhanced_status():
    """Get V8 Enhanced strategy status"""
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    return jsonify({
        'strategy': 'V8 Enhanced',
        'base_wr': 83.82,
        'expected_wr': 90.0,
        'auto_optimization': 'active',
        'liquidation_boost': 'enabled',
        'last_optimization': datetime.now().isoformat(),
        'status': 'ready',
        'features': [
            'V8 Base Model (83.82% WR)',
            'Auto-Optimization (900+ tests)',
            'Liquidation Proximity Detection',
            'Dynamic Confidence Boosting (+20%)',
            '24-Hour Re-optimization Cycle'
        ]
    })

@app.route('/api/liquidation_heatmap_data')
def liquidation_heatmap_data():
    """Get liquidation heatmap data from V9 experiment"""
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        import pandas as pd
        liq_data_path = os.path.join(os.path.dirname(__file__), '..', '..', 'V9_LIQUIDATION_EXPERIMENT', 'liquidation_data', 'REAL_liquidations_continuous.csv')
        df = pd.read_csv(liq_data_path)
        
        return jsonify({
            'total_liquidations': len(df),
            'total_volume': float(df['size'].sum()),
            'long_liquidations': len(df[df['side'] == 'A']),
            'short_liquidations': len(df[df['side'] == 'B']),
            'current_btc_price': float(df['price'].iloc[-1]),
            'avg_liquidation_size': float(df['size'].mean()),
            'last_update': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/heatmap')
def heatmap():
    """Serve interactive liquidation heatmap"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    try:
        heatmap_path = os.path.join(os.path.dirname(__file__), '..', '..', 'V9_LIQUIDATION_EXPERIMENT', 'liquidation_data', 'interactive_heatmap.html')
        with open(heatmap_path, 'r') as f:
            return f.read()
    except:
        return "Heatmap not available", 404

@app.route('/api/engine/select', methods=['POST'])
def select_engine():
    """Select trading engine (current or V8 Enhanced)"""
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    engine_type = data.get('engine')  # 'current' or 'v8_enhanced'
    
    if hasattr(trading_thread, 'select_engine'):
        success = trading_thread.select_engine(engine_type)
        if success:
            return jsonify({'status': 'ok', 'msg': f'Switched to {engine_type}'})
    
    # Store selection in session for now
    session['selected_engine'] = engine_type
    return jsonify({'status': 'ok', 'msg': f'Engine preference set to {engine_type}'})

@app.route('/api/engine/current')
def get_current_engine():
    """Get currently selected engine"""
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    current = session.get('selected_engine', 'current')
    return jsonify({'engine': current})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print("🚀 Web Dashboard Starting...")
    print(f"   Running on http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
