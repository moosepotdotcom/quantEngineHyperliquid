#!/usr/bin/env python3
"""
🛡️ MANDALORIAN ENGINE - Adaptive Shield V2
93% Win Rate Strategy with Dynamic ATR-Based Thresholds
Runs trading engine and dashboard in single process
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, send_from_directory, request, session
from flask_cors import CORS
from flask_socketio import SocketIO
from functools import wraps
import threading
import time
from datetime import datetime
import pandas as pd
import numpy as np

from mandalorian_state import MandalorianState
from quant_engine import TradingEngine, add_all_indicators, MTF_FEATURE_LIST, CircuitBreaker

# Flask app setup
app = Flask(__name__, static_folder='dashboard', static_url_path='')
app.secret_key = 'mandalorian-this-is-the-way-secret-key-2026'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

state_manager = MandalorianState()

# Login credentials
VALID_USERNAME = "mandalorian"
VALID_PASSWORD = "thisIsTheWay2026"

# Trading configuration
LEVERAGE = 400
POSITION_SIZE_BTC = 0.5
INITIAL_BALANCE = 100000.0
TP_PCT = 0.015  # 1.5%
SL_PCT = 0.008  # 0.8%

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

# ============================================================================
# POSITION TRACKER
# ============================================================================

class LivePositionTracker:
    def __init__(self, initial_balance):
        self.balance = initial_balance
        self.position = None
        self.trades = []
        
    def open_position(self, timestamp, direction, entry_price, confidence):
        if self.position:
            print(f"⚠️  Position already open, skipping")
            return False
        
        margin = (POSITION_SIZE_BTC * entry_price) / LEVERAGE
        tp_price = entry_price * (1 + TP_PCT) if direction == "LONG" else entry_price * (1 - TP_PCT)
        sl_price = entry_price * (1 - SL_PCT) if direction == "LONG" else entry_price * (1 + SL_PCT)
        
        self.position = {
            'timestamp': timestamp,
            'direction': direction,
            'entry_price': entry_price,
            'tp_price': tp_price,
            'sl_price': sl_price,
            'margin': margin,
            'confidence': confidence
        }
        
        self.balance -= margin
        print(f"📍 POSITION OPENED: {direction} @ ${entry_price:,.0f}")
        print(f"   TP: ${tp_price:,.0f} | SL: ${sl_price:,.0f}")
        print(f"   Margin: ${margin:,.2f} | Balance: ${self.balance:,.2f}")
        return True
    
    def check_exit(self, current_price, timestamp):
        if not self.position:
            return None
        
        pos = self.position
        hit_tp = False
        hit_sl = False
        
        if pos['direction'] == "LONG":
            if current_price >= pos['tp_price']:
                hit_tp = True
            elif current_price <= pos['sl_price']:
                hit_sl = True
        else:
            if current_price <= pos['tp_price']:
                hit_tp = True
            elif current_price >= pos['sl_price']:
                hit_sl = True
        
        if hit_tp or hit_sl:
            exit_reason = "TP" if hit_tp else "SL"
            return self._close_position(current_price, exit_reason, timestamp)
        
        return None
    
    def _close_position(self, exit_price, exit_reason, timestamp):
        pos = self.position
        
        if pos['direction'] == "LONG":
            price_change = exit_price - pos['entry_price']
        else:
            price_change = pos['entry_price'] - exit_price
        
        pnl_usd = price_change * POSITION_SIZE_BTC
        roe = (pnl_usd / pos['margin']) * 100
        
        self.balance += pos['margin']
        self.balance += pnl_usd
        
        duration = (timestamp - pos['timestamp']).total_seconds() / 60
        
        emoji = "✅" if exit_reason == "TP" else "❌"
        print(f"\n{emoji} POSITION CLOSED: {exit_reason}")
        print(f"   Entry: ${pos['entry_price']:,.0f} → Exit: ${exit_price:,.0f}")
        print(f"   PnL: ${pnl_usd:+,.2f} | ROE: {roe:+.1f}%")
        print(f"   Duration: {duration:.0f}m | Balance: ${self.balance:,.2f}\n")
        
        trade = {
            'timestamp': pos['timestamp'].isoformat() if hasattr(pos['timestamp'], 'isoformat') else str(pos['timestamp']),
            'exit_timestamp': timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp),
            'direction': pos['direction'],
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'exit_reason': exit_reason,
            'pnl': pnl_usd,
            'roe': roe,
            'balance': self.balance
        }
        
        self.trades.append(trade)
        self.position = None
        
        return trade

# Global tracker
tracker = None

# ============================================================================
# TRADING ENGINE BACKGROUND THREAD
# ============================================================================

def trading_engine_thread():
    """Background thread running the trading engine with full paper trading"""
    global tracker
    
    print("\n📊 Starting Trading Engine Thread...")
    
    engine = TradingEngine()
    tracker = LivePositionTracker(INITIAL_BALANCE)
    breaker = CircuitBreaker(max_losses=2, window_minutes=60, cooldown_hours=4)
    
    while True:
        try:
            # Fetch latest data
            df5 = engine.fetch_data('5m', limit=500)
            df15 = engine.fetch_data('15m', limit=500)
            df1h = engine.fetch_data('1h', limit=500)
            
            if df5 is None or len(df5) == 0:
                print("⚠️  Data fetch failed, retrying...")
                time.sleep(30)
                continue
            
            # Add indicators
            df5 = add_all_indicators(df5)
            df15 = add_all_indicators(df15)
            df1h = add_all_indicators(df1h)
            
            df5.set_index('timestamp', inplace=True)
            df15.set_index('timestamp', inplace=True)
            df1h.set_index('timestamp', inplace=True)
            
            # Merge
            exclude = ['open', 'high', 'low', 'close', 'volume']
            ctx15 = [c for c in df15.columns if c not in exclude]
            df15_renamed = df15[ctx15].copy().rename(columns={c: f"{c}_15m" for c in ctx15})
            df_merged = pd.concat([df5, df15_renamed.reindex(df5.index, method='ffill')], axis=1)
            
            ctx1h = [c for c in df1h.columns if c not in exclude]
            df1h_renamed = df1h[ctx1h].copy().rename(columns={c: f"{c}_1h" for c in ctx1h})
            df_merged = pd.concat([df_merged, df1h_renamed.reindex(df5.index, method='ffill')], axis=1)
            
            df_merged.dropna(inplace=True)
            
            # Get latest row
            latest = df_merged.iloc[-1]
            timestamp = df_merged.index[-1]
            current_price = float(latest['close'])
            
            # Check exits first
            closed_trade = tracker.check_exit(current_price, timestamp)
            if closed_trade:
                # Update state
                state_manager.close_position(
                    exit_price=closed_trade['exit_price'],
                    exit_reason=closed_trade['exit_reason'],
                    pnl=closed_trade['pnl']
                )
                
                # Update breaker
                if closed_trade['exit_reason'] == 'SL':
                    if not hasattr(breaker, 'sim_losses'): breaker.sim_losses = []
                    breaker.sim_losses = [t for t in breaker.sim_losses if (timestamp - t).total_seconds() < 3600]
                    breaker.sim_losses.append(timestamp)
                    if len(breaker.sim_losses) >= 2:
                        breaker.cooldown_until = timestamp + pd.Timedelta(hours=4)
                        print(f"🛑 CIRCUIT BREAKER ACTIVATED until {breaker.cooldown_until}")
            
            # Check for new signals (if no position)
            if not tracker.position:
                # Check circuit breaker
                if hasattr(breaker, 'cooldown_until') and breaker.cooldown_until and timestamp < breaker.cooldown_until:
                    print(f"⏸️  Circuit breaker active")
                    time.sleep(60)
                    continue
                
                # Prepare features
                X_dict = {c: latest.get(c, 0.0) for c in MTF_FEATURE_LIST}
                X = np.array([X_dict[c] for c in MTF_FEATURE_LIST]).reshape(1, -1)
                X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
                
                # Get prediction
                probas = engine.get_ensemble_proba('MTF', X)[0]
                prob_long, prob_short = float(probas[1]), float(probas[2])
                
                # === ADAPTIVE SHIELD V2: DYNAMIC ATR-BASED THRESHOLDS ===
                atr_val = latest.get('atr_14', 100)
                base_threshold = 0.45
                required_threshold = base_threshold
                
                if atr_val > 70:
                    # Increase threshold by 0.2% per ATR point above 70
                    excess_atr = atr_val - 70
                    penalty = excess_atr * 0.002
                    required_threshold = base_threshold + penalty
                    # Cap at 0.95
                    if required_threshold > 0.95:
                        required_threshold = 0.95
                
                direction = None
                confidence = 0.0
                
                if prob_long >= required_threshold:
                    direction = 'LONG'
                    confidence = prob_long
                elif prob_short >= required_threshold:
                    direction = 'SHORT'
                    confidence = prob_short
                
                # Update state with both confidence scores
                state_manager.update_signal(prob_long, prob_short, current_price)
                
                if direction:
                    # Apply shields (Adaptive Shield V2 filters)
                    hurst = latest.get('hurst', 0.5)
                    rsi = latest.get('rsi_14', 50)
                    rsi7 = latest.get('rsi_7', 50)
                    
                    # Mandalorian Filter: Block falling knife
                    if direction == 'LONG' and rsi < 30 and hurst > 0.5:
                        print(f"🛡️  Mandalorian Shield: Blocked falling knife (RSI:{rsi:.1f}, Hurst:{hurst:.2f})")
                        direction = None
                    
                    # AI Smart Filter: Block oversold short
                    if direction == 'SHORT' and rsi7 < 25:
                        print(f"🛡️  AI Smart Filter: Blocked oversold short (RSI7:{rsi7:.1f})")
                        direction = None
                    
                    if direction:
                        # Open position in tracker
                        if tracker.open_position(timestamp, direction, current_price, confidence):
                            # Calculate TP/SL
                            tp_price = current_price * (1 + TP_PCT) if direction == "LONG" else current_price * (1 - TP_PCT)
                            sl_price = current_price * (1 - SL_PCT) if direction == "LONG" else current_price * (1 + SL_PCT)
                            
                            # Update state with opened position
                            state_manager.open_position(
                                direction=direction,
                                entry_price=current_price,
                                tp_price=tp_price,
                                sl_price=sl_price,
                                confidence=confidence
                            )
                            
                            print(f"📍 OPEN {direction} @ ${current_price:,.0f} | Confidence: {confidence*100:.1f}% | ATR: {atr_val:.1f} | Threshold: {required_threshold*100:.1f}%")
                
                print(f"💤 Updated (Price: ${current_price:,.0f}) | LONG: {prob_long*100:.1f}% | SHORT: {prob_short*100:.1f}% | ATR: {atr_val:.1f} | Req: {required_threshold*100:.1f}%")
            
            # Sleep before next iteration
            time.sleep(5)
            
        except Exception as e:
            print(f"⚠️ Trading engine error: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(10)

# ============================================================================
# WEBSOCKET BACKGROUND THREAD
# ============================================================================

def websocket_broadcast_thread():
    """Background thread to push live state updates via WebSocket"""
    time.sleep(10)  # Wait for engine to initialize
    
    while True:
        try:
            time.sleep(2)
            state_manager.load_state()
            state = state_manager.get_state()
            socketio.emit('state_update', state)
        except Exception as e:
            print(f"⚠️ WebSocket broadcast error: {e}")
            time.sleep(5)

# ============================================================================
# API ROUTES
# ============================================================================

@app.route('/')
def index():
    if 'logged_in' not in session:
        return send_from_directory('dashboard', 'login.html')
    return send_from_directory('dashboard', 'index.html')

@app.route('/api/login', methods=['POST'])
def login():
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
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out'})

@app.route('/api/state')
@login_required
def get_state():
    state_manager.load_state()
    return jsonify(state_manager.get_state())

@app.route('/api/trades')
@login_required
def get_trades():
    state_manager.load_state()
    return jsonify(state_manager.get_trade_history())

@app.route('/api/performance')
@login_required
def get_performance():
    trades = state_manager.get_trade_history()
    
    if not trades:
        return jsonify({
            'total_pnl': 0, 'avg_win': 0, 'avg_loss': 0,
            'largest_win': 0, 'largest_loss': 0, 'avg_duration': 0,
            'daily_roi': 0, 'weekly_roi': 0, 'monthly_roi': 0
        })
    
    wins = [t for t in trades if t.get('exit_reason') == 'TP']
    losses = [t for t in trades if t.get('exit_reason') == 'SL']
    
    total_pnl = sum(t.get('pnl', 0) for t in trades)
    avg_win = sum(t.get('pnl', 0) for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t.get('pnl', 0) for t in losses) / len(losses) if losses else 0
    
    return jsonify({
        'total_pnl': total_pnl,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'largest_win': max((t.get('pnl', 0) for t in wins), default=0),
        'largest_loss': min((t.get('pnl', 0) for t in losses), default=0),
        'avg_duration': 0,
        'daily_roi': 0,
        'weekly_roi': 0,
        'monthly_roi': 0
    })

@app.route('/api/balance_history')
@login_required
def get_balance_history():
    trades = state_manager.get_trade_history()
    
    if not trades:
        return jsonify([])
    
    balance_history = []
    current_balance = INITIAL_BALANCE
    
    for trade in trades:
        if 'exit_timestamp' in trade and 'pnl' in trade:
            current_balance += trade['pnl']
            balance_history.append({
                'timestamp': trade['exit_timestamp'],
                'balance': current_balance,
                'pnl': trade['pnl']
            })
    
    return jsonify(balance_history)

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'engine': 'mandalorian'})

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    try:
        print("=" * 80)
        print("🛡️ MANDALORIAN ENGINE - Adaptive Shield V2 (93% Win Rate)")
        print("=" * 80)
        print(f"\n📡 Starting server on port {os.getenv('PORT', 5001)}")
        print(f"   Username: {VALID_USERNAME}")
        print(f"   Password: {VALID_PASSWORD}")
        print("\n🔴 LIVE WebSocket Feed: Enabled")
        print("📊 Paper Trading: ACTIVE (Adaptive Shield V2)")
        print(f"⚙️  Config: {LEVERAGE}x Leverage | {POSITION_SIZE_BTC} BTC | TP:{TP_PCT*100}% SL:{SL_PCT*100}%")
        print("🎯 Dynamic Thresholds: Base 45% + ATR penalty (0.2% per point > 70)")
        print("=" * 80)
        
        # Start trading engine thread
        engine_thread = threading.Thread(target=trading_engine_thread, daemon=True)
        engine_thread.start()
        
        # Start WebSocket broadcast thread
        ws_thread = threading.Thread(target=websocket_broadcast_thread, daemon=True)
        ws_thread.start()
        
        # Run server
        port = int(os.getenv('PORT', 5001))
        print(f"\n🚀 Launching SocketIO server on port {port}...")
        socketio.run(app, host='0.0.0.0', port=port, debug=False, use_reloader=False, log_output=True, allow_unsafe_werkzeug=True)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
