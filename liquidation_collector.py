import websocket
import json
import csv
import os
import time
from datetime import datetime

# Configuration
SYMBOL = "BTC"
OUTPUT_FILE = "data/live_liquidations_session.csv"
WS_URL = "wss://api.hyperliquid.xyz/ws"

# Ensure data directory exists
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

# Initialize CSV
if not os.path.exists(OUTPUT_FILE):
    with open(OUTPUT_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'symbol', 'side', 'price', 'size', 'usd_value', 'liquidated_user', 'tid'])

def on_message(ws, message):
    try:
        data = json.loads(message)
        channel = data.get('channel')
        
        if channel == 'trades':
            trades = data.get('data', [])
            for trade in trades:
                # 🕵️ Check for Liquidation indicators
                # Based on research, look for 'liquidation' field or similar markers
                # We will log anything that looks suspicious or explicit
                
                is_liquidation = False
                liq_info = None
                
                # Check 1: Explicit 'liquidation' field (if API provides it)
                if 'liquidation' in trade:
                    is_liquidation = True
                    liq_info = trade.get('liquidation')
                
                # Check 2: Deduce from other fields if needed (omitted for now to be strict)
                
                if is_liquidation:
                    process_liquidation(trade)

    except Exception as e:
        pass

def process_liquidation(trade):
    try:
        ts = datetime.now()
        price = float(trade['px'])
        size = float(trade['sz'])
        usd_value = price * size
        side = trade['side'] # 'B' or 'A' (Buy/Sell)
        # Note: In Hyperliquid trades:
        # 'B' (Buy) in trade stream means the aggressor bought.
        # If it's a Short Liquidation, the engine BUYS to close the short. So 'B' = Short Liq.
        # If it's a Long Liquidation, the engine SELLS to close the long. So 'A' = Long Liq.
        
        liq_type = "SHORT LIQ 🟢" if side == 'B' else "LONG LIQ 🔴"
        
        print(f"💦 {liq_type}: ${usd_value:,.2f} @ {price}")
        
        with open(OUTPUT_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                ts.isoformat(),
                SYMBOL,
                side,
                price,
                size,
                usd_value,
                trade.get('users', [''])[0], # capture user if available
                trade.get('tid')
            ])
            
    except Exception as e:
        print(f"Error logging: {e}")

def on_error(ws, error):
    print(f"❌ Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("🔌 Disconnected. Reconnecting in 5s...")
    time.sleep(5)
    start_stream()

def on_open(ws):
    print(f"✅ Collecting {SYMBOL} liquidations to {OUTPUT_FILE}...")
    msg = {
        "method": "subscribe",
        "subscription": {
            "type": "trades", 
            "coin": SYMBOL
        }
    }
    ws.send(json.dumps(msg))

def start_stream():
    # Enable verbose logging to see why it closes
    websocket.enableTrace(True)
    ws = websocket.WebSocketApp(WS_URL,
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.run_forever()

if __name__ == "__main__":
    try:
        start_stream()
    except KeyboardInterrupt:
        print("\n👋 Stopped collection")
