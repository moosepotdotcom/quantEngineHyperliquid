import websocket
import json
import time
import pandas as pd
from datetime import datetime

# COINS to observe
COINS = ['BTC', 'ETH', 'SOL', 'AVAX', 'ARB']

data_log = []
latest_oi = {c: 0 for c in COINS}
cvd = {c: 0 for c in COINS}

def on_message(ws, message):
    try:
        d = json.loads(message)
        if 'channel' in d:
            # print(f"DEBUG: Channel {d['channel']}")
            pass
        if d['channel'] == 'l2Book':
            c = d['data']['coin']
            l = d['data']['levels']
            mid = (float(l[0][0]['px']) + float(l[1][0]['px'])) / 2
            
            # Simple Imbalance
            bv = sum([float(x['sz']) for x in l[0][:5]])
            av = sum([float(x['sz']) for x in l[1][:5]])
            imb = (bv-av)/(bv+av) if (bv+av)>0 else 0
            
            data_log.append({
                'ts': time.time(),
                'coin': c,
                'type': 'BOOK',
                'price': mid,
                'imbalance': imb
            })
            
        elif d['channel'] == 'trades':
            for t in d['data']:
                val = float(t['px']) * float(t['sz'])
                side_mult = 1 if t['side'] == 'B' else -1
                c = t['coin']
                
                # Update CVD
                cvd[c] += (val * side_mult)
                
                if t.get('liquidation', False):
                    print(f"🩸 LIQ: {c} | ${val:,.0f} | Side: {t['side']}")
                    data_log.append({
                        'ts': time.time(),
                        'coin': c,
                        'type': 'LIQ',
                        'price': float(t['px']),
                        'val_usd': val,
                        'side': t['side']
                    })
                
                # Log CVD every trade (filtered by significant size or time)
                data_log.append({
                    'ts': time.time(),
                    'coin': c,
                    'type': 'CVD',
                    'value': cvd[c],
                    'trade_val': val,
                    'side': t['side']
                })
        elif d['channel'] == 'meta':
            # Hyperliquid meta channel provides OI in some versions, 
            # but usually it's in 'activeAssetCtx' or regular REST.
            # We'll use 'webData2' or check for 'ctx' in L2 updates.
            pass
        elif 'channel' in d:
             if d['channel'] == 'activeAssetCtx':
                 # Standard way
                 c = d['data']['coin']
                 oi = float(d['data']['ctx'].get('openInterest', 0))
                 if c in latest_oi:
                     delta = oi - latest_oi[c]
                     latest_oi[c] = oi
                     if abs(delta) > 0:
                         data_log.append({
                             'ts': time.time(),
                             'coin': c,
                             'type': 'OI',
                             'value': oi,
                             'delta': delta
                         })
             else:
                 # print(f"Unknown channel: {d['channel']}")
                 pass
        elif 'ctx' in d: # Some versions/proxies
            c = d['coin']
            oi = float(d['ctx'].get('openInterest', 0))
            if c in latest_oi:
                delta = oi - latest_oi[c]
                latest_oi[c] = oi
                if abs(delta) > 0:
                    data_log.append({
                        'ts': time.time(),
                        'coin': c,
                        'type': 'OI',
                        'value': oi,
                        'delta': delta
                    })
    except: pass

def on_open(ws):
    print("🚀 Observer Started...")
    for c in COINS:
        ws.send(json.dumps({"method": "subscribe", "subscription": {"type": "l2Book", "coin": c}}))
        ws.send(json.dumps({"method": "subscribe", "subscription": {"type": "trades", "coin": c}}))
        ws.send(json.dumps({"method": "subscribe", "subscription": {"type": "activeAssetCtx", "coin": c}}))

if __name__ == "__main__":
    ws = websocket.WebSocketApp("wss://api.hyperliquid.xyz/ws", on_open=on_open, on_message=on_message)
    
    # Run for 5 minutes to gather 'Alpha'
    import threading
    t = threading.Thread(target=ws.run_forever)
    t.start()
    
    time.sleep(300)
    ws.close()
    
    # Save to CSV for Deep Analysis
    if data_log:
        df = pd.DataFrame(data_log)
        df.to_csv('patient_observer_data.csv', index=False)
        print(f"✅ Saved {len(data_log)} events. Analyzing...")
        
        # Quick summary
        liqs = df[df['type'] == 'LIQ']
        if not liqs.empty:
            print("\n--- LIQUIDATION SUMMARY ---")
            print(liqs.groupby(['coin', 'side'])['val_usd'].sum().to_string())
        else:
            print("\n❌ No liquidations during observation window.")
