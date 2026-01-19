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
STATE_FILE = 'paper_trading_state_maker.json' # Separate state file
LOG_FILE = 'dashboard_events_maker.log'

# Maker Rebate (Standard VIP 0)
MAKER_REBATE = 0.0001 # +0.01%

# Global Data Store
LATEST_DATA = {coin: {'price': 0.0, 'best_bid': 0.0, 'best_ask': 0.0, 'imbalance': 0.0, 'bids': 0, 'asks': 0, 'ts': time.time()} for coin in COINS}
DATA_LOCK = threading.Lock()

# === WEBSOCKET CLIENT (Same structure, enhanced data) ===
class DataStream(threading.Thread):
    def __init__(self):
        super().__init__()
        self.ws = None
        self.running = True
        self.daemon = True

    def run(self):
        while self.running:
            try:
                self.ws = websocket.WebSocketApp(WS_URL, on_open=self.on_open, on_message=self.on_message)
                self.ws.run_forever()
                time.sleep(2)
            except: time.sleep(5)

    def on_open(self, ws):
        for coin in COINS: ws.send(json.dumps({"method": "subscribe", "subscription": {"type": "l2Book", "coin": coin}}))

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            if data.get('channel') == 'l2Book':
                coin = data['data']['coin']
                levels = data['data']['levels']
                if levels[0] and levels[1]:
                    bids = levels[0]; asks = levels[1]
                    best_bid = float(bids[0]['px'])
                    best_ask = float(asks[0]['px'])
                    mid = (best_bid + best_ask) / 2
                    
                    bid_vol = sum([float(x['sz']) for x in bids[:10]])
                    ask_vol = sum([float(x['sz']) for x in asks[:10]])
                    imb = (bid_vol - ask_vol) / (bid_vol + ask_vol) if (bid_vol+ask_vol)>0 else 0
                    
                    wb = len([x for x in bids[:5] if float(x['sz']) > bid_vol/10])
                    wa = len([x for x in asks[:5] if float(x['sz']) > ask_vol/10])

                    with DATA_LOCK:
                        LATEST_DATA[coin] = {
                            'price': mid, 'best_bid': best_bid, 'best_ask': best_ask,
                            'imbalance': imb, 'bids': wb, 'asks': wa, 'ts': time.time()
                        }
        except: pass

# === MAKER TRADING ENGINE ===
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f: return json.load(f)
        except: pass
    return {'balance': 10000.0, 'positions': {}, 'orders': {}, 'history': [], 'logs': []}

def save_state(state):
    with open(STATE_FILE, 'w') as f: json.dump(state, f, indent=2)

def log_msg(state, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}"
    state['logs'].insert(0, entry)
    state['logs'] = state['logs'][:15]

def run_trading_logic(state):
    with DATA_LOCK:
        snapshot = LATEST_DATA.copy()
    
    for coin, data in snapshot.items():
        if time.time() - data['ts'] > 10: continue
        
        # 1. Manage Active Orders (Simulate Fills)
        # We assume orders are placed at Best Bid (Long) or Best Ask (Short) of the PREVIOUS tick
        # Fill happens if current Low < My Bid (Long) or current High > My Ask (Short)
        # For simplicity in simulation: Check if limit price was crossed
        
        if coin in state['orders']:
            order = state['orders'][coin]
            limit_px = order['price']
            
            filled = False
            if order['side'] == 'BUY':
                # Filled if Best Ask hits our Limit (someone sold into us) OR Best Bid moves below us
                if data['best_ask'] <= limit_px or data['best_bid'] < limit_px:
                    filled = True
            elif order['side'] == 'SELL':
                if data['best_bid'] >= limit_px or data['best_ask'] > limit_px:
                    filled = True
            
            if filled:
                # ENTRY FILL
                if order['type'] == 'ENTRY':
                    state['positions'][coin] = {
                        'type': 'LONG' if order['side'] == 'BUY' else 'SHORT',
                        'entry': limit_px,
                        'ts': str(datetime.now())
                    }
                    log_msg(state, f"MAKER FILL {order['side']} {coin} @ ${limit_px:,.2f} (+Rebate)")
                
                # EXIT FILL
                elif order['type'] == 'EXIT':
                    pos = state['positions'].get(coin)
                    if pos:
                        entry_px = pos['entry']
                        # PnL + Entry Rebate + Exit Rebate
                        raw_pnl = (limit_px - entry_px)/entry_px if order['side'] == 'SELL' else (entry_px - limit_px)/entry_px
                        final_pnl = raw_pnl + MAKER_REBATE + MAKER_REBATE # Double Rebate!
                        
                        realized = state['balance'] * final_pnl
                        state['balance'] += realized
                        state['history'].insert(0, {'coin': coin, 'pnl': final_pnl, 'type': 'MAKER', 'exit': limit_px})
                        log_msg(state, f"MAKER EXIT {coin} @ ${limit_px:,.2f} | PnL: {final_pnl*100:+.3f}% (inc. +0.02% Rebate)")
                        del state['positions'][coin]
                
                del state['orders'][coin]
            
            else:
                # CHASE LOGIC: If price moves away, update limit order to new Best Bid/Ask
                # This ensures we get filled eventually, but always as Maker
                if order['side'] == 'BUY' and data['best_bid'] > limit_px:
                    order['price'] = data['best_bid'] # Move up
                if order['side'] == 'SELL' and data['best_ask'] < limit_px:
                    order['price'] = data['best_ask'] # Move down

        # 2. Logic to Place Orders
        # Check Exits first
        if coin in state['positions'] and coin not in state['orders']:
            pos = state['positions'][coin]
            entry_px = pos['entry']
            imb = data['imbalance']
            
            pnl = (data['price'] - entry_px)/entry_px if pos['type'] == 'LONG' else (entry_px - data['price'])/entry_px
            
            # Exit Signal
            should_exit = False
            if pos['type'] == 'LONG' and (imb < -0.1 or pnl > 0.012 or pnl < -0.006): should_exit = True
            if pos['type'] == 'SHORT' and (imb > 0.1 or pnl > 0.012 or pnl < -0.006): should_exit = True
            
            if should_exit:
                side = 'SELL' if pos['type'] == 'LONG' else 'BUY'
                px = data['best_ask'] if side == 'SELL' else data['best_bid'] # Place at queue
                state['orders'][coin] = {'type': 'EXIT', 'side': side, 'price': px, 'ts': time.time()}
                log_msg(state, f"POSTING EXIT {side} {coin} @ ${px:,.2f}")

        # Check Entries
        if coin not in state['positions'] and coin not in state['orders']:
            imb = data['imbalance']
            if imb > 0.4 and data['bids'] > 0:
                state['orders'][coin] = {'type': 'ENTRY', 'side': 'BUY', 'price': data['best_bid'], 'ts': time.time()}
                log_msg(state, f"POSTING BUY {coin} @ ${data['best_bid']:,.2f}")
            elif imb < -0.4 and data['asks'] > 0:
                state['orders'][coin] = {'type': 'ENTRY', 'side': 'SELL', 'price': data['best_ask'], 'ts': time.time()}
                log_msg(state, f"POSTING SELL {coin} @ ${data['best_ask']:,.2f}")

    return state

# === UI (Modified for Maker Info) ===
def make_dashboard():
    stream = DataStream()
    stream.start()
    state = load_state()
    layout = Layout()
    layout.split(Layout(name="header", size=3), Layout(name="body", ratio=1))
    layout["body"].split_row(Layout(name="scanner", ratio=6), Layout(name="trading", ratio=4))
    layout["trading"].split_column(Layout(name="active", ratio=3), Layout(name="stats", ratio=2), Layout(name="logs", ratio=4))

    with Live(layout, refresh_per_second=4, screen=True) as live:
        while True:
            state = run_trading_logic(state)
            save_state(state)
            
            # Header
            head = Table.grid(expand=True)
            head.add_column(justify="center")
            head.add_row(Text("🛡️ MAKER/MAKER STRATEGY • REBATE FARMING 🛡️", style="bold white on green"))
            layout["header"].update(Panel(head, style="white on green"))
            
            # Scanner
            table = Table(title="MARKET FEED (Post-Only)", expand=True, border_style="green")
            table.add_column("Asset", style="cyan")
            table.add_column("Spread", justify="center")
            table.add_column("Imbalance", justify="right")
            table.add_column("Signal")
            
            with DATA_LOCK: snapshot = LATEST_DATA.copy()
            for coin in COINS:
                d = snapshot.get(coin, {})
                px = d.get('price', 0)
                spread = d.get('best_ask',0) - d.get('best_bid',0)
                imb = d.get('imbalance', 0)
                
                status = "WAIT"
                if coin in state['positions']: status = "IN POS"
                elif coin in state['orders']: status = "ORDER OPEN"
                
                table.add_row(
                    coin, 
                    f"${spread:.2f}",
                    Text(f"{imb:+.3f}", style="green" if imb>0 else "red"),
                    Text(status, style="yellow" if "ORDER" in status else "dim")
                )
            layout["scanner"].update(Panel(table))
            
            # Active
            active_t = Table(title="ACTIVE POSITIONS (+0.01% ENTRY LOCKED)", expand=True, border_style="yellow")
            active_t.add_column("Coin")
            active_t.add_column("PnL (w/ Rebates)", justify="right")
            
            active_pnl = 0
            if state['positions']:
                for c, p in state['positions'].items():
                    curr = snapshot[c]['price']
                    if p['type'] == 'LONG': pn = (curr - p['entry'])/p['entry']
                    else: pn = (p['entry'] - curr)/p['entry']
                    
                    # Add Estimated Exit Rebate (+0.01 already captured on Entry)
                    total_proj = pn + MAKER_REBATE + MAKER_REBATE
                    active_pnl += (state['balance'] * total_proj)
                    
                    active_t.add_row(c, Text(f"{total_proj*100:+.3f}%", style="green" if total_proj>0 else "red"))
            else:
                active_t.add_row("No Positions", "-")
            layout["active"].update(Panel(active_t))
            
            # Stats
            wins = len([x for x in state['history'] if x['pnl']>0])
            tot = len(state['history'])
            wr = (wins/tot*100) if tot>0 else 0
            stats = f"💰 Equity: ${state['balance']:,.2f}\n📈 Win Rate: {wr:.1f}%\n⚡ Open PnL: ${active_pnl:+.2f}"
            layout["stats"].update(Panel(Align.center(stats), title="MAKER PERFORMANCE"))
            
            # Logs
            log_t = Table.grid(expand=True)
            log_t.add_column()
            for l in state['logs']:
                log_t.add_row(Text(l, style="green" if "Fill" in l else "dim" if "POSTING" in l else "white"))
            layout["logs"].update(Panel(log_t, title="ORDER LOG"))
            
            time.sleep(0.1)

if __name__ == "__main__":
    make_dashboard()
