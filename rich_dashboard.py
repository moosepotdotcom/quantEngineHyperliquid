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
STATE_FILE = 'paper_trading_state.json'
LOG_FILE = 'dashboard_events.log'

# Global Data Store (Thread-Safe)
LATEST_DATA = {coin: {'price': 0.0, 'imbalance': 0.0, 'bids': 0, 'asks': 0, 'ts': time.time()} for coin in COINS}
DATA_LOCK = threading.Lock()

# === WEBSOCKET CLIENT ===
class DataStream(threading.Thread):
    def __init__(self):
        super().__init__()
        self.ws = None
        self.running = True
        self.daemon = True

    def run(self):
        while self.running:
            try:
                self.ws = websocket.WebSocketApp(
                    WS_URL,
                    on_open=self.on_open,
                    on_message=self.on_message,
                    on_error=self.on_error,
                    on_close=self.on_close
                )
                self.ws.run_forever()
                time.sleep(2) # Reconnect delay
            except Exception as e:
                time.sleep(5)

    def on_open(self, ws):
        # Subscribe to L2 Book for all coins
        for coin in COINS:
            msg = {
                "method": "subscribe",
                "subscription": {"type": "l2Book", "coin": coin}
            }
            ws.send(json.dumps(msg))

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            channel = data.get('channel')
            
            if channel == 'l2Book':
                coin = data['data']['coin']
                levels = data['data']['levels']
                bids = levels[0]
                asks = levels[1]
                
                # Analyze Order Flow
                if bids and asks:
                    best_bid = float(bids[0]['px'])
                    best_ask = float(asks[0]['px'])
                    mid_price = (best_bid + best_ask) / 2
                    
                    bid_vol = sum([float(x['sz']) for x in bids[:10]]) # Top 10 levels
                    ask_vol = sum([float(x['sz']) for x in asks[:10]])
                    
                    imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol) if (bid_vol + ask_vol) > 0 else 0
                    
                    # Whale Detection (Simplified for live stream)
                    # Count orders significantly larger than average in top levels
                    whale_b = len([x for x in bids[:5] if float(x['sz']) > bid_vol/10])
                    whale_a = len([x for x in asks[:5] if float(x['sz']) > ask_vol/10])

                    with DATA_LOCK:
                        LATEST_DATA[coin] = {
                            'price': mid_price,
                            'imbalance': imbalance,
                            'bids': whale_b,
                            'asks': whale_a,
                            'ts': time.time()
                        }
        except:
            pass

    def on_error(self, ws, error):
        pass

    def on_close(self, ws, status_code, msg):
        pass

# === PAPER TRADING ENGINE ===
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f: return json.load(f)
        except: pass
    return {'balance': 10000.0, 'positions': {}, 'history': [], 'logs': []}

def save_state(state):
    with open(STATE_FILE, 'w') as f: json.dump(state, f, indent=2)

def log_msg(state, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}"
    state['logs'].insert(0, entry)
    state['logs'] = state['logs'][:15] # Keep last 15
    # Also file log
    with open(LOG_FILE, 'a') as f: f.write(entry + "\n")

def run_trading_logic(state):
    with DATA_LOCK:
        snapshot = LATEST_DATA.copy()
    
    for coin, data in snapshot.items():
        if time.time() - data['ts'] > 10: continue # Stale data
        
        price = data['price']
        imb = data['imbalance']
        
        # Check Positions
        if coin in state['positions']:
            pos = state['positions'][coin]
            entry_px = pos['entry']
            
            pnl = 0
            if pos['type'] == 'LONG':
                pnl = (price - entry_px) / entry_px
                # Dynamic Exit: Imbalance Flip or Hard Stop/TP
                if imb < -0.1 or pnl > 0.012 or pnl < -0.006:
                    realized = state['balance'] * pnl
                    state['balance'] += realized
                    state['history'].insert(0, {'coin': coin, 'pnl': pnl, 'type': 'LONG', 'exit': price})
                    log_msg(state, f"EXIT LONG {coin} @ ${price:,.2f} | PnL: {pnl*100:+.2f}%")
                    del state['positions'][coin]
                    
            elif pos['type'] == 'SHORT':
                pnl = (entry_px - price) / entry_px
                # Dynamic Exit
                if imb > 0.1 or pnl > 0.012 or pnl < -0.006:
                    realized = state['balance'] * pnl
                    state['balance'] += realized
                    state['history'].insert(0, {'coin': coin, 'pnl': pnl, 'type': 'SHORT', 'exit': price})
                    log_msg(state, f"EXIT SHORT {coin} @ ${price:,.2f} | PnL: {pnl*100:+.2f}%")
                    del state['positions'][coin]
                    
        # Check Entries
        else:
            if imb > 0.4 and data['bids'] > 0:
                state['positions'][coin] = {'type': 'LONG', 'entry': price, 'ts': str(datetime.now())}
                log_msg(state, f"ENTER LONG {coin} @ ${price:,.2f} (Imb: {imb:.2f})")
                
            elif imb < -0.4 and data['asks'] > 0:
                state['positions'][coin] = {'type': 'SHORT', 'entry': price, 'ts': str(datetime.now())}
                log_msg(state, f"ENTER SHORT {coin} @ ${price:,.2f} (Imb: {imb:.2f})")
    
    return state

# === UI ===
def make_dashboard():
    # Start WS Thread
    stream = DataStream()
    stream.start()
    
    state = load_state()
    
    layout = Layout()
    layout.split(
        Layout(name="header", size=3),
        Layout(name="body", ratio=1)
    )
    layout["body"].split_row(
        Layout(name="scanner", ratio=6),
        Layout(name="trading", ratio=4)
    )
    layout["trading"].split_column(
        Layout(name="active", ratio=3),
        Layout(name="stats", ratio=2),
        Layout(name="logs", ratio=4)
    )

    with Live(layout, refresh_per_second=4, screen=True) as live:
        while True:
            # Update Logic
            state = run_trading_logic(state)
            save_state(state)
            
            # Header
            head = Table.grid(expand=True)
            head.add_column(justify="center")
            head.add_row(Text("⚡ HYPERLIQUID PHASE 4 • DIRECT FEED ⚡", style="bold white on blue"))
            layout["header"].update(Panel(head, style="white on blue"))
            
            # Scanner
            table = Table(title="LIVE MARKET FEED (ms)", expand=True, border_style="blue")
            table.add_column("Asset", style="cyan")
            table.add_column("Price", justify="right")
            table.add_column("Imbalance", justify="right")
            table.add_column("Order Flow", justify="center")
            
            with DATA_LOCK:
                snapshot = LATEST_DATA.copy()
                
            for coin in COINS:
                d = snapshot.get(coin, {})
                price = d.get('price', 0)
                imb = d.get('imbalance', 0)
                
                if price == 0:
                    table.add_row(coin, "Connecting...", "-", "-")
                    continue
                
                imb_color = "green" if imb > 0 else "red"
                flow = "🌊 BUY" if imb > 0.3 else "🩸 SELL" if imb < -0.3 else "⚪ CHOP"
                
                table.add_row(
                    coin, 
                    f"${price:,.2f}", 
                    Text(f"{imb:+.3f}", style=imb_color),
                    Text(flow, style="bold " + imb_color)
                )
            layout["scanner"].update(Panel(table))
            
            # Active Positions
            pos_table = Table(title="ACTIVE SCALPS", expand=True, border_style="yellow")
            pos_table.add_column("Coin")
            pos_table.add_column("PnL", justify="right")
            
            active_pnl = 0
            if state['positions']:
                for c, p in state['positions'].items():
                    curr = snapshot[c]['price']
                    if p['type'] == 'LONG': pn = (curr - p['entry'])/p['entry']
                    else: pn = (p['entry'] - curr)/p['entry']
                    active_pnl += (state['balance'] * pn)
                    
                    pos_table.add_row(c, Text(f"{pn*100:+.2f}%", style="green" if pn>0 else "red"))
            else:
                pos_table.add_row("No Positions", "-")
                
            layout["active"].update(Panel(pos_table))
            
            # Stats
            wins = len([x for x in state['history'] if x['pnl']>0])
            tot = len(state['history'])
            wr = (wins/tot*100) if tot>0 else 0
            
            stats = f"💰 Equity: ${state['balance']:,.2f}\n"
            stats += f"📈 Win Rate: {wr:.1f}%\n"
            stats += f"⚡ Open PnL: ${active_pnl:+.2f}"
            layout["stats"].update(Panel(Align.center(stats), title="PERFORMANCE"))
            
            # Logs
            log_t = Table.grid(expand=True)
            log_t.add_column()
            for l in state['logs']:
                log_t.add_row(Text(l, style="dim white" if "ENTER" in l else "bold white"))
            layout["logs"].update(Panel(log_t, title="ACTIVITY LOG"))
            
            time.sleep(0.1)

if __name__ == "__main__":
    make_dashboard()
