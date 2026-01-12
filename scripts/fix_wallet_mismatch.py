
import os
import requests
from dotenv import load_dotenv
from eth_account import Account

# Load EXPORT/.env
load_dotenv('EXPORT/.env')

print("🔍 WALLET MISMATCH DIAGNOSIS")
print("="*70)

# 1. Get Configured Values
conf_addr = os.getenv('HYPERLIQUID_WALLET_ADDRESS')
priv_key = os.getenv('HYPERLIQUID_API_SECRET')

if not priv_key:
    print("❌ ERROR: No Private Key found in .env")
    exit(1)

# 2. Derive Actual Address
if not priv_key.startswith('0x'): priv_key = '0x' + priv_key
account = Account.from_key(priv_key)
derived_addr = account.address

print(f"🔑 Configured Address: {conf_addr}")
print(f"🗝️ Derived Address:    {derived_addr}")

match = (conf_addr.lower() == derived_addr.lower())
if match:
    print("✅ Addresses MATCH. The config is consistent.")
else:
    print("❌ MISMATCH DETECTED! The Private Key belongs to a DIFFERENT wallet.")

# 3. Check Balance of DERIVED Address
print(f"\n📡 Checking balance for DERIVED address: {derived_addr}...")
try:
    url = "https://api.hyperliquid.xyz/info"
    payload = {"type": "clearinghouseState", "user": derived_addr}
    resp = requests.post(url, json=payload, timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        margin = data.get('marginSummary', {})
        bal = float(margin.get('accountValue', 0))
        print(f"💰 BALANCE: ${bal:.2f}")
        
        if bal > 1:
            print("\n🎉 FOUND IT! This wallet has funds.")
            print(f"Action: Update .env to use {derived_addr}")
            
            # Auto-fix logic can go here or be manual
        else:
            print("\n⚠️  Derived wallet is also empty ($0.00).")
    else:
        print(f"❌ API Error: {resp.status_code}")

except Exception as e:
    print(f"❌ Error checking balance: {e}")

print("="*70)
