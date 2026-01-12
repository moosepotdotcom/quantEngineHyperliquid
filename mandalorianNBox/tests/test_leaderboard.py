
import requests
import json

url = "https://api.hyperliquid.xyz/info"
headers = {'Content-Type': 'application/json'}

payloads = [
    {"type": "meta"}, # Control
    {"type": "leaderboard"}, # Failed before
    {"type": "leaderboard", "period": "allTime"},
    {"type": "leaderboard", "window": "1d"},
    {"type": "subAccounts", "user": "0xdfc74586345F5409E38E892FA71C2299C53703F0"} # Check user
]

for data in payloads:
    print(f"\nTesting: {data}")
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        if response.status_code == 200:
            print("✅ Success!")
            print(str(response.json())[:200])
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
