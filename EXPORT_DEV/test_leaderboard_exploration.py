
import requests
import json

def get_leaderboard():
    url = "https://api.hyperliquid.xyz/info"
    headers = {"Content-Type": "application/json"}
    
    # Try different potential payload types for leaderboard
    payloads = [
        {"type": "clearinghouseState", "user": "0x..."}, # Not it
        {"type": "meta"}, # maybe
        {"type": "spotMeta"},
    ]
    
    # Function to hit raw endpoint since SDK might not cover it
    # Leaderboard is often a separate API or a specific 'type' in /info
    
    # According to community docs, 'u' (User) or 'userState' is common.
    # But for GLOBAL leaderboard...
    
    # Let's try to mimic the web request if possible, or just look for standard endpoints.
    # We will try a known unofficial method or standard 'info' types.
    
    print("Testing generic INFO types...")
    try:
        # 1. Recent Trades (Whale Prints?) -> "l2Book" is orderbook. "trades" is history.
        
        # 2. Check if there's a specific 'leaderboard' type (Unlikely to be documented but worth a try)
        # Often these are just processed from all user stats, but that's impossible for public API.
        
        # Let's try to fetch large Recent Trades (The "Movements" part of the request)
        # This is easier and maybe more "Whale Movement" than a static leaderboard.
        
        body = {
            "type": "l2Book",
            "coin": "BTC"
        }
        res = requests.post(url, json=body, headers=headers)
        print(f"L2 Book status: {res.status_code}")
        
    except Exception as e:
        print(e)
        
    print("\nAttempting to find Leaderboard...")
    # There isn't a documented public API for the "Leaderboard" page specifically that is stable.
    # User might want "Whale Movements" meaning LARGE TRADES.
    
    # Let's fetch the L2 snapshots or recent fills for BTC and filter for LARGE size.
    # "Whale Movements" usually means "Big Buys/Sells".
    
    # We can use "l2Book" to see big liquidity? No.
    # We want executed trades.
    
    # SDK doesn't expose public trade history for all users easily.
    # BUT, we can use the websocket or polling 'l2Book' isn't trades.
    
    # Let's try looking for the leaderboard endpoint specifically.
    # Most likely: POST https://api.hyperliquid.xyz/info { "type": "leaderboard" } ??
    try:
        res = requests.post(url, json={"type": "clientStats"}, headers=headers) # maybe?
        # print(res.text[:200])
    except:
        pass

if __name__ == "__main__":
    get_leaderboard()
