
import requests
import pandas as pd
from datetime import datetime

def probe():
    url = 'https://api.hyperliquid.xyz/info'
    headers = {'Content-Type': 'application/json'}
    
    # Probe Period: Nov 1, 2025 to Nov 5, 2025
    start_ts = int(datetime(2025, 11, 1).timestamp() * 1000)
    end_ts = int(datetime(2025, 11, 5).timestamp() * 1000)
    
    payload = {
        'type': 'candleSnapshot',
        'req': {
            'coin': 'BTC',
            'interval': '5m',
            'startTime': start_ts,
            'endTime': end_ts 
        }
    }
    
    print(f"🕵️ Probing BTC 5m for Nov 1-5, 2025...")
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        data = resp.json()
        if data:
            print(f"✅ Received {len(data)} candles.")
            print(f"First: {datetime.fromtimestamp(data[0]['t']/1000)}")
            print(f"Last:  {datetime.fromtimestamp(data[-1]['t']/1000)}")
        else:
            print("⚠️ No data received (Empty List).")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == '__main__':
    probe()
