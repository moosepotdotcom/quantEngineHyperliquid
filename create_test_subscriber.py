import requests
import sys
import os

# Add path to import auth locally
sys.path.append(os.path.join(os.getcwd(), 'WILLIAMS_ML_STRATEGY_V1'))
from auth import engine, SessionLocal, create_user, get_user

API_URL = "http://127.0.0.1:8000"

def create_test_data():
    print("🧪 Creating Test Subscriber Data...")
    
    # 1. Create User in Auth DB
    db = SessionLocal()
    if get_user(db, "test_user"):
        print("✅ Auth User 'test_user' already exists.")
    else:
        create_user(db, "test_user", "test@client.com", "password123", role="subscriber")
        print("✅ Created Auth User: test_user / password123")
    db.close()
    
    # 2. Configure Copy-Trading (via API as Admin)
    # First, login as Admin to get token
    try:
        login_resp = requests.post(f"{API_URL}/token", data={"username": "admin", "password": "admin123"})
        if login_resp.status_code != 200:
            print(f"❌ Admin Login Failed: {login_resp.text}")
            return
            
        token = login_resp.json()['access_token']
        headers = {"Authorization": f"Bearer {token}"}
        
        # Add Subscriber config to Copy Engine
        sub_data = {
            "user_id": "test_user",
            "wallet_address": "0x123...PLACEHOLDER_WALLET",
            "api_key": "0xABC...PLACEHOLDER_KEY",
            "risk_multiplier": 0.5 # 50% of master size
        }
        
        resp = requests.post(f"{API_URL}/saas/subscribe", json=sub_data, headers=headers)
        if resp.status_code == 200:
            print(f"✅ Copy-Trading Configured: {resp.json()['message']}")
        else:
            print(f"❌ Copy-Trading Config Failed: {resp.text}")
            
    except Exception as e:
        print(f"❌ API Error: {e}")

if __name__ == "__main__":
    create_test_data()
