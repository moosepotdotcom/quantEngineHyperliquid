import websocket
import json
import time

# Standard domain
WS_URL = "wss://api.hyperliquid.xyz/ws"

def on_message(ws, message):
    try:
        data = json.loads(message)
        channel = data.get('channel')
        
        if channel == 'trades':
            trades = data.get('data', [])
            if trades:
                print(f"✅ RECEIVED TRADE: {trades[0]}")
                # We only need to see one to confirm connection
                ws.close()
        elif channel == 'liquidations':
            print(f"✅ RECEIVED LIQUIDATION: {data}")
            ws.close()
        elif channel == 'error':
             print(f"❌ API Error: {data}")
             
    except Exception as e:
        print(f"Error parsing message: {e}")

def on_error(ws, error):
    print(f"❌ Connection Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("🔌 Connection Closed")

def on_open(ws):
    print(f"🔗 Connected to {WS_URL}")
    print("📤 Sending subscription...")
    msg = {
        "method": "subscribe",
        "subscription": {
            "type": "trades", 
            "coin": "BTC"
        }
    }
    ws.send(json.dumps(msg))

if __name__ == "__main__":
    # Enable verbose trace to see what's happening
    websocket.enableTrace(True)
    print(f"🚀 Attempting connection to {WS_URL}...")
    ws = websocket.WebSocketApp(WS_URL,
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.run_forever()
