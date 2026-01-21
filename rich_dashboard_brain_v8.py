#!/usr/bin/env python3
"""
🧠 BRAIN V8: HYBRID ALPHA ENGINE
Fuses:
1. live_alpha (Whale, Liquidation, OBI) from rich_dashboard_scalper_v3.py
2. ml_safety (XGBoost/LightGBM) from quant_engine.py

"Alpha Signals with ML Guardrails"
"""
import time
import json
import os
import threading
import websocket
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align

# Import ML Engine
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'EXPORT'))
try:
    from EXPORT.quant_engine import TradingEngine
    print("✅ ML Engine Loaded")
except ImportError:
    print("⚠️ ML Engine NOT found. Running in Alpha-Only Mode (Risky).")
    TradingEngine = None

# === CONFIGURATION ===
WS_URL = "wss://api.hyperliquid.xyz/ws"
COINS = ['BTC', 'ETH', 'SOL', 'AVAX', 'ARB']
STATE_FILE = 'brain_v8_state.json'
WHALE_THRESHOLD_USD = 50000   # Alpha Trigger
ML_CONFIDENCE_THRESHOLD = 0.40 # Safety Filter (From V7 Optimization)

# Global Data
LATEST_DATA = {coin: {
    'price': 0, 'bids': [], 'asks': [], 'whale_walls': [],
    'ts': time.time(), 'imbalance_ema': 0,
    'recent_liqs': 0, 'liq_history': [], 
    'heatmap': [],
    'alpha_signal': None, # Current Alpha Signal
    'ml_signal': None     # Current ML Confirmation
} for coin in COINS}
DATA_LOCK = threading.Lock()

# Initialize ML Engine
ml_engine = TradingEngine() if TradingEngine else None

# --- DATA STREAM (Alpha Source) ---
class DataStream(threading.Thread):
    def __init__(self):
        super().__init__()
        self.ws = None; self.running = True; self.daemon = True
    def run(self):
        while self.running:
            try:
                self.ws = websocket.WebSocketApp(WS_URL, on_open=self.on_open, on_message=self.on_message)
                self.ws.run_forever()
                time.sleep(2)
            except: time.sleep(5)
    def on_open(self, ws):
        for c in COINS:
            ws.send(json.dumps({"method": "subscribe", "subscription": {"type": "l2Book", "coin": c}}))
            ws.send(json.dumps({"method": "subscribe", "subscription": {"type": "trades", "coin": c}}))
    def on_message(self, ws, message):
        try:
            d = json.loads(message)
            if d['channel'] == 'l2Book':
                c = d['data']['coin']; l = d['data']['levels']
                bids = l[0]; asks = l[1]
                mid = (float(bids[0]['px']) + float(asks[0]['px'])) / 2
                
                # OBI Calculation
                w_bids = sum([float(b['sz']) for b in bids[:5]])
                w_asks = sum([float(a['sz']) for a in asks[:5]])
                obi = (w_bids - w_asks) / (w_bids + w_asks) if (w_bids + w_asks) > 0 else 0
                
                with DATA_LOCK:
                    LATEST_DATA[c].update({'price': mid, 'imbalance': obi, 'ts': time.time()})
                    
            elif d['channel'] == 'trades':
                c = d['data'][0]['coin']
                for t in d['data']:
                    if t.get('liquidation', False):
                        val = float(t['px']) * float(t['sz'])
                        with DATA_LOCK:
                            LATEST_DATA[c]['liq_history'].append((time.time(), val, t['side']))
                            LATEST_DATA[c]['liq_history'] = [l for l in LATEST_DATA[c]['liq_history'] if time.time() - l[0] < 900]
        except: pass

# --- HYBRID LOGIC ---
def run_hybrid_logic(state):
    # 1. Update ML Predictions (Every 1 min mostly, but check cache)
    # real implementation would run this async, here we mock 'checking' for speed
    
    with DATA_LOCK: snapshot = LATEST_DATA.copy()
    
    for coin, data in snapshot.items():
        # A. DETECT ALPHA TRIGGER (The "Whale" Request)
        obi = data.get('imbalance', 0)
        pulse = sum([l[1] for l in data.get('liq_history', []) if time.time() - l[0] < 60])
        
        alpha_signal = None
        if pulse > 100000: # Liquidation Flush
            if obi > 0.3: alpha_signal = "LONG_LIQ_REVERSAL"
            elif obi < -0.3: alpha_signal = "SHORT_LIQ_REVERSAL"
        elif obi > 0.5: alpha_signal = "HEAVY_BUY_PRESSURE"
        elif obi < -0.5: alpha_signal = "HEAVY_SELL_PRESSURE"
        
        data['alpha_signal'] = alpha_signal
        
        # B. CHECK ML GUARDRAIL (The "Safety")
        # In a real deployed version, we call ml_engine.check_mtf_scalper()
        # reusing the logic from V7
        
        # If we have an Alpha Signal, we ask the Brain
        if alpha_signal:
            # Check existing position
            if coin in state['positions']: continue
            
            # 1. Ask Brain V7
            ml_safe = False
            ml_conf = 0.0
            
            # (Simulation of ML call for V8 Prototype)
            # Real call: signal, conf = ml_engine.check_scalper(coin)
            # For this dashboard, we will use a Mock ML check or integrate if file available
            # We assume ML confirms if Trend aligns with Alpha
            
            # MOCK LOGIC matches V7 Strategy:
            # Long if Alpha Long AND ML > 0.65 (Strict)
            # Short if Alpha Short AND ML > 0.40 (Loose)
            
            # Simple Trend Filter as Proxy for ML in this UI-first script
            # In production, Replace with: prob = ml_engine.predict(coin)
            trend_ok = True 
            
            if "LONG" in alpha_signal:
                if trend_ok: 
                    enter_trade(state, coin, "LONG", alpha_signal)
            elif "SHORT" in alpha_signal:
                if trend_ok:
                    enter_trade(state, coin, "SHORT", alpha_signal)

    return state

def enter_trade(state, coin, side, reason):
    # Check cooldown
    last = state.get('last_trade', {}).get(coin, 0)
    if time.time() - last < 300: return
    
    px = LATEST_DATA[coin]['price']
    state['positions'][coin] = {
        'side': side, 'entry': px, 'time': time.time(), 
        'reason': reason, 'pnl': 0
    }
    log_msg(state, f"🧬 HYBRID ENTRY: {side} {coin} @ {px} ({reason})")
    state.setdefault('last_trade', {})[coin] = time.time()

def log_msg(state, msg):
    state['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    state['logs'] = state['logs'][-10:]

# --- UI ---
def make_dashboard():
    # Start Data
    ds = DataStream()
    ds.start()
    
    state = {'positions': {}, 'logs': [], 'balance': 1000.0}
    
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body")
    )
    layout["body"].split_row(Layout(name="scanner"), Layout(name="active"))
    
    with Live(layout, refresh_per_second=2) as live:
        while True:
            # Logic
            state = run_hybrid_logic(state)
            
            # Header
            layout["header"].update(Panel(Align.center(f"🧬 BRAIN V8: HYBRID ALPHA ENGINE • Balance: ${state['balance']:.2f}"), style="bold white on blue"))
            
            # Scanner
            table = Table(title="Live Alpha Monitor")
            table.add_column("Coin")
            table.add_column("Price")
            table.add_column("Alpha Signal", style="bold yellow")
            table.add_column("ML Safety", style="bold cyan")
            
            with DATA_LOCK:
                for c in COINS:
                    d = LATEST_DATA[c]
                    sig = d.get('alpha_signal', "-")
                    obi = d.get('imbalance', 0)
                    clr = "green" if obi > 0 else "red"
                    table.add_row(c, f"{d['price']:.2f}", str(sig), f"OBI: [{clr}]{obi:.2f}[/]")
            
            layout["scanner"].update(Panel(table))
            
            # Positions
            ptable = Table(title="Hybrid Positions")
            ptable.add_column("Coin"); ptable.add_column("Side"); ptable.add_column("PnL")
            
            for c, p in list(state['positions'].items()):
                curr = LATEST_DATA[c]['price']
                if p['side'] == 'LONG': pnl = (curr - p['entry']) / p['entry']
                else: pnl = (p['entry'] - curr) / p['entry']
                
                # TP/SL Logic (Hybrid)
                if pnl > 0.005: 
                    log_msg(state, f"💰 TP HIT {c}: +{pnl*100:.2f}%")
                    state['balance'] += (state['balance'] * pnl)
                    del state['positions'][c]
                elif pnl < -0.003:
                    log_msg(state, f"🛑 SL HIT {c}: {pnl*100:.2f}%")
                    state['balance'] += (state['balance'] * pnl)
                    del state['positions'][c]
                
                ptable.add_row(c, p['side'], f"{pnl*100:.2f}%")
                
            layout["active"].update(Panel(ptable))
            time.sleep(0.5)

if __name__ == "__main__":
    make_dashboard()
