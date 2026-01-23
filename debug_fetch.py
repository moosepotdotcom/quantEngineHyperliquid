import requests
import pandas as pd
from datetime import datetime

url = 'https://api.hyperliquid.xyz/info'
start_time = int(datetime(2026, 1, 2).timestamp() * 1000)
end_time = int(datetime(2026, 1, 4).timestamp() * 1000)

print(f"Requesting: {datetime.fromtimestamp(start_time/1000)} to {datetime.fromtimestamp(end_time/1000)}")

payload = {
    'type': 'candleSnapshot',
    'req': {
        'coin': 'BTC',
        'interval': '5m',
        'startTime': start_time,
        'endTime': end_time
    }
}

resp = requests.post(url, json=payload)
data = resp.json()

print(f"Received {len(data)} candles")
if data:
    print(f"First: {pd.to_datetime(data[0]['t'], unit='ms')}")
    print(f"Last: {pd.to_datetime(data[-1]['t'], unit='ms')}")
