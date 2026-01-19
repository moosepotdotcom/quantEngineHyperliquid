import time
import json
import os
import threading
import websocket
from datetime import datetime
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.console import Console
from rich.text import Text
from rich.align import Align

# === CONFIGURATION ===
WS_URL = "wss://api.hyperliquid.xyz/ws"
COINS = ['BTC', 'ETH', 'SOL', 'AVAX', 'ARB']
STATE_FILE = 'paper_trading_state_hybrid.json' 
# Fees
TAKER_FEE = 0.00035 # 0.035%
MAKER_REBATE = 0.0001 # 0.01%
# Net Cost = 0.00025 (0.025%)

# Global Data Store
LATEST_DATA = {coin: {'price': 0.0, 'best_bid': 0.0, 'best_ask': 0.0, 'imbalance': 0.0, 'ts': time.time()} for coin in COINS}
DATA_LOCK = threading.Lock()

# ... (WebSocket Class - Same as before) ...
class DataStream(threading.Thread):
    def __init__(self):
        super().__init__()
        self.ws = None; self.running = True; self.daemon = True
    def run(self):
        while self.running:
            try:
                self.ws = websocket.WebSocketApp(WS_URL, on_open=self.on_open, on_message=self.on_message)
                self.ws.run_forever(); time.sleep(2)
            except: time.sleep(5)
    def on_open(self, ws):
        for c in COINS: ws.send(json.dumps({"method": "subscribe", "subscription": {"type": "l2Book", "coin": c}}))
    def on_message(self, ws, message):
        try:
            d = json.loads(message)
            if d['channel'] == 'l2Book':
                c = d['data']['coin']; l = d['data']['levels']
                b = float(l[0][0]['px']); a = float(l[1][0]['px']); mid = (b+a)/2
                # Simple Imbalance
                bv = sum([float(x['sz']) for x in l[0][:5]])
                av = sum([float(x['sz']) for x in l[1][:5]])
                imb = (bv-av)/(bv+av) if (bv+av)>0 else 0
                with DATA_LOCK: LATEST_DATA[c] = {'price': mid, 'best_bid': b, 'best_ask': a, 'imbalance': imb, 'ts': time.time()}
        except: pass

# ... (Hybrid Trading Engine) ...
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f: return json.load(f)
        except: pass
    return {'balance': 10000.0, 'positions': {}, 'orders': {}, 'history': [], 'logs': []}

def save_state(s):
    with open(STATE_FILE, 'w') as f: json.dump(s, f, indent=2)

def log_msg(s, m):
    s['logs'].insert(0, f"[{datetime.now().strftime('%H:%M:%S')}] {m}")
    s['logs'] = s['logs'][:15]

def run_hybrid_logic(state):
    with DATA_LOCK: snapshot = LATEST_DATA.copy()
    
    for coin, data in snapshot.items():
        if time.time() - data['ts'] > 10: continue
        
        # 1. EXIT LOGIC (Maker Only)
        if coin in state['orders']:
            # Check for Fill
            o = state['orders'][coin]
            # SELL LIMIT gets filled if Best Bid >= Limit
            filled = False
            if o['side'] == 'SELL' and data['best_bid'] >= o['price']: filled = True
            elif o['side'] == 'BUY' and data['best_ask'] <= o['price']: filled = True
            
            if filled:
                # Calculate PnL
                pos = state['positions'][coin]
                raw = (o['price'] - pos['entry'])/pos['entry'] if o['side'] == 'SELL' else (pos['entry'] - o['price'])/pos['entry']
                # Cost: Taker Entry (0.035%) - Maker Exit Rebate (0.01%) = 0.025% Net Fee
                final_pnl = raw - TAKER_FEE + MAKER_REBATE 
                
                amt = state['balance'] * final_pnl
                state['balance'] += amt
                state['history'].insert(0, {'coin': coin, 'pnl': final_pnl, 'type': 'HYBRID'})
                log_msg(state, f"MAKER EXIT {coin} | Net: {final_pnl*100:+.3f}% (Hybrid Fee -0.025%)")
                del state['positions'][coin]
                del state['orders'][coin]
            else:
                # CHASE EXIT: Update Limit to front of queue to ensure exit
                if o['side'] == 'SELL' and o['price'] > data['best_ask']: 
                    o['price'] = data['best_ask'] # Walk down
                if o['side'] == 'BUY' and o['price'] < data['best_bid']: 
                    o['price'] = data['best_bid'] # Walk up
        
        # 2. POSITION MANAGEMENT
        if coin in state['positions'] and coin not in state['orders']:
            p = state['positions'][coin]
            pnl = (data['price'] - p['entry'])/p['entry'] if p['type'] == 'LONG' else (p['entry'] - data['price'])/p['entry']
            
            # Simple TP/SL
            if pnl > 0.01 or pnl < -0.005:
                side = 'SELL' if p['type'] == 'LONG' else 'BUY'
                px = data['best_ask'] if side == 'SELL' else data['best_bid']
                state['orders'][coin] = {'side': side, 'price': px}
                log_msg(state, f"POSTING EXIT {coin} @ {px}")

        # 3. ENTRY LOGIC (Taker Only)
        if coin not in state['positions'] and coin not in state['orders']:
            if data['imbalance'] > 0.5:
                # MARKET BUY (Taker)
                # Fill at Best Ask
                entry = data['best_ask']
                state['positions'][coin] = {'type': 'LONG', 'entry': entry}
                log_msg(state, f"TAKER ENTRY LONG {coin} @ {entry} (Imb {data['imbalance']:.2f})")
            elif data['imbalance'] < -0.5:
                # MARKET SELL (Taker)
                # Fill at Best Bid
                entry = data['best_bid']
                state['positions'][coin] = {'type': 'SHORT', 'entry': entry}
                log_msg(state, f"TAKER ENTRY SHORT {coin} @ {entry}")

    return state

# UI Wrapper ...
