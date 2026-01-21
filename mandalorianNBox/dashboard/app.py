"""
Trading Bot Dashboard - Main Flask Application
Real-time monitoring and control interface for trading bots
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import json
import os
import sys
import threading
import time
from datetime import datetime

# Add root directory to path so we can import 'strategies'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from strategies_complete import STRATEGIES, get_strategy_info
from backtest_engine import run_backtest
from strategy_deployer import create_live_bot

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
socketio = SocketIO(app, cors_allowed_origins="*")

# Risk control settings (stored in memory, can be saved to file)
risk_settings = {
    'stop_loss_percent': 20,
    'take_profit_percent': 20,
    'max_leverage': 40,
    'daily_max_loss_percent': 50,
    'is_monitoring': False
}

# Trading log storage
trading_log = []
max_log_entries = 1000

# Live positions
live_positions = {}

# Liquidation data
liquidation_data = {
    'long_liquidations': 0,
    'short_liquidations': 0,
    'recent_liquidations': []
}

# Asset prices
asset_prices = {}

# Strategy testing and deployment
strategy_results = []  # Store backtest results
deployed_strategies = {}  # Strategies running live
strategy_status = {}  # Status of each strategy

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard_enhanced.html')

@app.route('/god_mode')
def god_mode():
    """God Mode Dashboard"""
    return render_template('god_mode.html')

@app.route('/api/risk-settings', methods=['GET', 'POST'])
def risk_settings_api():
    """Get or update risk control settings"""
    global risk_settings
    
    if request.method == 'POST':
        data = request.json
        risk_settings.update({
            'stop_loss_percent': float(data.get('stop_loss', 20)),
            'take_profit_percent': float(data.get('take_profit', 20)),
            'max_leverage': float(data.get('max_leverage', 40)),
            'daily_max_loss_percent': float(data.get('daily_max_loss', 50)),
            'is_monitoring': data.get('is_monitoring', False)
        })
        
        # Emit to all connected clients
        socketio.emit('risk_settings_updated', risk_settings)
        
        return jsonify({'status': 'success', 'settings': risk_settings})
    
    return jsonify(risk_settings)

@app.route('/api/trading-log', methods=['GET'])
def trading_log_api():
    """Get trading log entries"""
    return jsonify({
        'log': trading_log[-1000:],  # Last 1000 entries
        'total': len(trading_log)
    })

@app.route('/api/positions', methods=['GET'])
def positions_api():
    """Get current positions"""
    return jsonify(live_positions)

@app.route('/api/liquidations', methods=['GET'])
def liquidations_api():
    """Get liquidation data"""
    return jsonify(liquidation_data)

@app.route('/api/v8_enhanced_status', methods=['GET'])
def v8_enhanced_status():
    """Get V8 Enhanced strategy status"""
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

@app.route('/api/liquidation_heatmap_data', methods=['GET'])
def liquidation_heatmap_data():
    """Get liquidation heatmap data from V9 experiment"""
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
    try:
        heatmap_path = os.path.join(os.path.dirname(__file__), '..', '..', 'V9_LIQUIDATION_EXPERIMENT', 'liquidation_data', 'interactive_heatmap.html')
        with open(heatmap_path, 'r') as f:
            return f.read()
    except:
        return "Heatmap not available", 404

@app.route('/api/asset-prices', methods=['GET'])
def asset_prices_api():
    """Get current asset prices"""
    return jsonify(asset_prices)

@app.route('/api/add-log', methods=['POST'])
def add_log():
    """Add entry to trading log (called by bot)"""
    global trading_log
    
    data = request.json
    entry = {
        'timestamp': datetime.now().strftime('%H:%M:%S'),
        'type': data.get('type', 'INFO'),  # BUY, SELL, INFO, ERROR
        'symbol': data.get('symbol', ''),
        'message': data.get('message', ''),
        'price': data.get('price', None),
        'size': data.get('size', None)
    }
    
    trading_log.append(entry)
    if len(trading_log) > max_log_entries:
        trading_log.pop(0)
    
    # Emit to all connected clients
    socketio.emit('new_log_entry', entry)
    
    return jsonify({'status': 'success'})

@app.route('/api/add-liquidation', methods=['POST'])
def add_liquidation():
    """Add liquidation event (called by bot)"""
    global liquidation_data
    
    data = request.json
    liquidation = {
        'symbol': data.get('symbol', ''),
        'side': data.get('side', ''),  # LONG or SHORT
        'amount': data.get('amount', 0),
        'timestamp': datetime.now().strftime('%H:%M:%S')
    }
    
    if liquidation['side'] == 'LONG':
        liquidation_data['long_liquidations'] += liquidation['amount']
    else:
        liquidation_data['short_liquidations'] += liquidation['amount']
    
    liquidation_data['recent_liquidations'].append(liquidation)
    if len(liquidation_data['recent_liquidations']) > 50:
        liquidation_data['recent_liquidations'].pop(0)
    
    # Emit to all connected clients
    socketio.emit('new_liquidation', liquidation)
    
    return jsonify({'status': 'success'})

@app.route('/api/update-price', methods=['POST'])
def update_price():
    """Update asset price (called by bot)"""
    global asset_prices
    
    data = request.json
    asset_prices[data['symbol']] = {
        'price': data.get('price', 0),
        'change': data.get('change', 0),
        'timestamp': datetime.now().strftime('%H:%M:%S')
    }
    
    # Emit to all connected clients
    socketio.emit('price_update', asset_prices[data['symbol']])
    
    return jsonify({'status': 'success'})

# Strategy endpoints
@app.route('/api/strategies', methods=['GET'])
def get_strategies():
    """Get all available strategies"""
    return jsonify(get_strategy_info())

@app.route('/api/data-files', methods=['GET'])
def get_data_files():
    """Get all available data files"""
    import json
    data_files_path = os.path.join(os.path.dirname(__file__), 'data_files.json')
    try:
        with open(data_files_path, 'r') as f:
            data_files = json.load(f)
        return jsonify(data_files)
    except:
        # Fallback if file doesn't exist
        return jsonify({
            'data_files': [
                {'name': 'BTC Daily (1000 weeks)', 'file': 'BTCUSD-1d-1000wks-data.csv', 'symbol': 'BTC', 'timeframe': '1d'},
                {'name': 'BTC Hourly (500 weeks)', 'file': 'BTCUSD-1h-500wks-data.csv', 'symbol': 'BTC', 'timeframe': '1h'},
                {'name': 'BTC 6-Hour (500 weeks)', 'file': 'BTCUSD-6h-500wks-data.csv', 'symbol': 'BTC', 'timeframe': '6h'},
                {'name': 'BTC 15m (2022)', 'file': 'BTC-USD-15m-2022-1-01.csv', 'symbol': 'BTC', 'timeframe': '15m'},
                {'name': 'BTC 15m (2023)', 'file': 'BTC-USD-15m-2023-1-01T00_00 (1).csv', 'symbol': 'BTC', 'timeframe': '15m'},
                {'name': 'ETH 15m (2021)', 'file': 'ETH-USD-15m-2021-1-01T00_00.csv', 'symbol': 'ETH', 'timeframe': '15m'},
            ]
        })

@app.route('/api/backtest', methods=['POST'])
def run_backtest_api():
    """Run a backtest"""
    data = request.json
    
    strategy_name = data.get('strategy_name')
    params = data.get('params', {})
    data_file = data.get('data_file', 'BTCUSD-1d-1000wks-data.csv')
    start_date = data.get('start_date', '2020-01-01')
    end_date = data.get('end_date', '2024-12-31')
    initial_cash = data.get('initial_cash', 10000)
    commission = data.get('commission', 0.001)
    
    # Run backtest
    result = run_backtest(strategy_name, params, data_file, start_date, end_date, initial_cash, commission)
    
    # Store result
    if 'error' not in result:
        result['timestamp'] = datetime.now().isoformat()
        strategy_results.append(result)
        if len(strategy_results) > 50:
            strategy_results.pop(0)
        
        # Emit to clients
        socketio.emit('backtest_complete', result)
    
    return jsonify(result)

@app.route('/api/backtest-results', methods=['GET'])
def get_backtest_results():
    """Get all backtest results"""
    return jsonify(strategy_results)

@app.route('/api/deploy-strategy', methods=['POST'])
def deploy_strategy():
    """Deploy a strategy to live trading"""
    global deployed_strategies, strategy_status
    
    data = request.json
    strategy_id = data.get('strategy_id')
    strategy_name = data.get('strategy_name')
    params = data.get('params', {})
    symbol = data.get('symbol', 'BTC')
    size = data.get('size', 1)
    target = data.get('target', 5)
    max_loss = data.get('max_loss', -10)
    
    # Create live bot file
    try:
        bot_path = create_live_bot(strategy_name, params, symbol, size, target, max_loss)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
    
    # Create deployment record
    deployment = {
        'id': strategy_id,
        'strategy_name': strategy_name,
        'params': params,
        'symbol': symbol,
        'size': size,
        'target': target,
        'max_loss': max_loss,
        'bot_file': bot_path,
        'deployed_at': datetime.now().isoformat(),
        'status': 'active'
    }
    
    deployed_strategies[strategy_id] = deployment
    strategy_status[strategy_id] = {
        'status': 'active',
        'trades': 0,
        'profit': 0,
        'last_update': datetime.now().isoformat()
    }
    
    # Emit to clients
    socketio.emit('strategy_deployed', deployment)
    
    return jsonify({'status': 'success', 'deployment': deployment, 'bot_file': bot_path})

@app.route('/api/deployed-strategies', methods=['GET'])
def get_deployed_strategies():
    """Get all deployed strategies"""
    return jsonify({
        'strategies': deployed_strategies,
        'status': strategy_status
    })

@app.route('/api/stop-strategy', methods=['POST'])
def stop_strategy():
    """Stop a deployed strategy"""
    global deployed_strategies, strategy_status
    
    data = request.json
    strategy_id = data.get('strategy_id')
    
    if strategy_id in deployed_strategies:
        deployed_strategies[strategy_id]['status'] = 'stopped'
        if strategy_id in strategy_status:
            strategy_status[strategy_id]['status'] = 'stopped'
        
        socketio.emit('strategy_stopped', {'id': strategy_id})
        return jsonify({'status': 'success'})
    
    return jsonify({'status': 'error', 'message': 'Strategy not found'})

@app.route('/api/monitoring', methods=['GET'])
def get_monitoring_data():
    """Get all monitoring data"""
    return jsonify({
        'positions': live_positions,
        'liquidations': liquidation_data,
        'prices': asset_prices,
        'trading_log': trading_log[-50:],
        'deployed_strategies': deployed_strategies,
        'strategy_status': strategy_status,
        'risk_settings': risk_settings
    })

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('Client connected')
    emit('connected', {'status': 'connected'})
    # Send current state
    emit('risk_settings_updated', risk_settings)
    emit('initial_log', trading_log[-100:])
    emit('initial_positions', live_positions)
    emit('initial_liquidations', liquidation_data)
    emit('initial_prices', asset_prices)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')

def run_dashboard(host='0.0.0.0', port=8000, debug=False):
    """Run the dashboard server"""
    print(f"🚀 Starting Trading Bot Dashboard on http://{host}:{port}")
    print("📊 Open your browser to view the dashboard")
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)

# ... (previous code)

# --- LOG WATCHER ---
class LogWatcher(threading.Thread):
    def __init__(self, log_file):
        super().__init__()
        self.log_file = log_file
        self.running = True
        self.daemon = True
        self.health_state = {
            'core_last_seen': 0,
            'quantum_last_seen': 0,
            'news_last_seen': 0,
            'risk_last_seen': 0,
            'start_time': time.time()
        }

    def run(self):
        print(f"👀 Watching log file (Absolute): {os.path.abspath(self.log_file)}", flush=True)
        print(f"👀 File exists: {os.path.exists(self.log_file)}", flush=True)
        print(f"👀 Initial Size: {os.stat(self.log_file).st_size if os.path.exists(self.log_file) else 'N/A'}", flush=True)
        last_pos = 0
        try:
            # Initial read of last 100 lines
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines[-100:]:
                        self.parse_line(line.strip())
                    last_pos = f.tell()

            loop_count = 0
            while self.running:
                time.sleep(1) # Check every second
                loop_count += 1
                
                # Emit Health Check every second
                health_data = {
                    'core': self._param_status(self.health_state['core_last_seen'], 15),
                    'quantum': self._param_status(self.health_state['quantum_last_seen'], 60), # Slower updates
                    'news': self._param_status(self.health_state['news_last_seen'], 300), # Very slow
                    'risk': self._param_status(self.health_state['risk_last_seen'], 300),
                    'uptime': int(time.time() - self.health_state['start_time'])
                }
                with app.app_context():
                    socketio.emit('health_update', health_data)

                if loop_count % 5 == 0:
                    print(f"💓 Watcher Alive. Size: {os.stat(self.log_file).st_size} Last: {last_pos}", flush=True)
                
                if not os.path.exists(self.log_file):
                    continue

                try:
                    current_size = os.stat(self.log_file).st_size
                except FileNotFoundError:
                    continue

                # If file shrank, it was truncated; reset
                if current_size < last_pos:
                    print(f"📉 File shrank: {last_pos} -> {current_size}. Resetting.", flush=True)
                    last_pos = 0
                
                # If file grew, or we reset
                if current_size > last_pos:
                    print(f"📈 File grew: {last_pos} -> {current_size}. Reading delta.", flush=True)
                    with open(self.log_file, 'r') as f:
                        f.seek(last_pos)
                        new_lines = f.readlines()
                        last_pos = f.tell()
                        
                        print(f"📖 Read {len(new_lines)} new lines.", flush=True)
                        for line in new_lines:
                            self.parse_line(line.strip())
                            
        except Exception as e:
            print(f"❌ Log Watcher Error: {e}", flush=True)

    def parse_line(self, line):
        if not line: return
        
        # print(f"Processing: {line[:50]}...") # Too verbose?
        
        timestamp = datetime.now().strftime('%H:%M:%S') # Fallback if no time in log
        
        # Regex patterns could be more robust, but simple string matching works for now
        event_type = "INFO"
        data = {'raw': line, 'timestamp': timestamp}

        if "### 💓 Sandbox Trade: STATUS CHECK" in line:
            event_type = "HEARTBEAT"
            # Extract timestamp from line if possible
        elif "### 🚀 Sandbox Trade: BUY" in line:
            event_type = "TRADE_BUY"
        elif "### 🔻 Sandbox Trade: SELL" in line:
            event_type = "TRADE_SELL"
        elif "### 🌊 LIQUIDATION ALERT" in line:
            event_type = "LIQUIDATION"
        elif "### 💰 FUNDING ARB ALERT" in line:
            event_type = "ARB_ALERT"
        elif "### 📰 News Update" in line or "### 🚨 MARKET NEWS ALERT" in line:
            event_type = "NEWS"
        elif "🐢 TURTLE OPTIMIZED SIGNAl" in line:
            event_type = "TURTLE_SIGNAL"
        elif ">>> Turtle Entry" in line:
            event_type = "TURTLE_ENTRY"
        data['type'] = event_type
        
        # Update Health State
        now = time.time()
        if event_type == "HEARTBEAT":
            self.health_state['core_last_seen'] = now
            self.health_state['runtime'] = data['timestamp'] # Use log timestamp as proxy for "latest active time"
        elif event_type == "STATUS_DETAIL":
            self.health_state['quantum_last_seen'] = now
        elif event_type == "NEWS":
            self.health_state['news_last_seen'] = now
        elif event_type == "ARB_ALERT" or event_type == "LIQUIDATION":
            self.health_state['risk_last_seen'] = now

        # Store in global history
        with app.app_context():
            trading_log.append(data)
            if len(trading_log) > max_log_entries:
                trading_log.pop(0)

        # Emit to all clients
        try:
             with app.app_context():
                 # print(f"📡 Emitting: {event_type}")
                 socketio.emit('log_event', data)
        except Exception as e:
            print(f"❌ Socket Emit Error: {e}", flush=True)

    def _param_status(self, last_seen, threshold=30):
        if last_seen == 0: return "OFFLINE"
        return "ONLINE" if (time.time() - last_seen) < threshold else "STALLED"

def start_log_watcher():
    # Path relative to this file
    log_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'PROJECT_DEV_LOG.md'))
    watcher = LogWatcher(log_path)
    watcher.start()

# --- END LOG WATCHER ---

if __name__ == '__main__':
    start_log_watcher()
    run_dashboard()
