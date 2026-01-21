
import requests
import json

def test_leaderboard():
    url = "https://api.hyperliquid.xyz/info"
    payload = {"type": "leaderboard"}
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"Leaderboard fetched successfully! Found {len(data)} entries.")
            # Print first entry to see format
            if data:
                print("Sample Entry:")
                print(json.dumps(data[0], indent=2))
        else:
            print(f"Failed to fetch leaderboard: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_leaderboard()
