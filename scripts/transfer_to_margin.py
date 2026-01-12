#!/usr/bin/env python3
"""
Transfer USDC from spot to perpetual margin on Hyperliquid
This enables the bot to trade BTC perpetuals
"""

import os
import json
import time
from dotenv import load_dotenv
from eth_account import Account
from eth_account.signers.local import LocalAccount
import requests

# Load environment
load_dotenv()

# Configuration
WALLET_ADDRESS = "0xb01713a6fcdc9419f37db065f0274ea172e4689e"
PRIVATE_KEY = os.getenv('HYPERLIQUID_API_SECRET')
API_URL = "https://api.hyperliquid.xyz"
AMOUNT_TO_TRANSFER = 9.8  # USDC

print("💰 Transferring USDC to Perpetual Margin")
print("=" * 70)
print(f"Wallet: {WALLET_ADDRESS}")
print(f"Amount: ${AMOUNT_TO_TRANSFER} USDC")
print("=" * 70)

# Initialize account for signing
if not PRIVATE_KEY:
    print("❌ Error: HYPERLIQUID_API_SECRET not set in .env")
    exit(1)

if not PRIVATE_KEY.startswith('0x'):
    PRIVATE_KEY = '0x' + PRIVATE_KEY

account: LocalAccount = Account.from_key(PRIVATE_KEY)

print(f"\n✅ Account loaded: {account.address}")

# Create transfer action
print(f"\n📤 Creating transfer action...")

# Hyperliquid uses "usdTransfer" action to move USDC to margin
transfer_action = {
    "type": "usdTransfer",
    "hyperliquidChain": "Mainnet",
    "signatureChainId": "0xa4b1",  # Arbitrum chain ID
    "amount": str(AMOUNT_TO_TRANSFER),
    "time": int(time.time() * 1000),
    "destination": "perp"  # Transfer to perpetual margin
}

print(f"Transfer action: {json.dumps(transfer_action, indent=2)}")

try:
    # Sign the action
    print(f"\n🔐 Signing transaction...")
    
    # Create the message to sign
    message = json.dumps(transfer_action, separators=(',', ':'))
    message_hash = Account._hash_eip191_message(message.encode())
    signed = account.sign_message_hash(message_hash)
    
    # Prepare the request payload
    payload = {
        "action": transfer_action,
        "nonce": int(time.time() * 1000),
        "signature": {
            "r": hex(signed.r),
            "s": hex(signed.s),
            "v": signed.v
        }
    }
    
    print(f"✅ Transaction signed!")
    
    # Send to Hyperliquid
    print(f"\n📡 Sending to Hyperliquid API...")
    
    response = requests.post(
        f"{API_URL}/exchange",
        json=payload,
        headers={'Content-Type': 'application/json'},
        timeout=10
    )
    
    print(f"Response Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n" + "=" * 70)
        print(f"✅ TRANSFER SUCCESSFUL!")
        print(f"=" * 70)
        print(f"\n💰 ${AMOUNT_TO_TRANSFER} USDC transferred to perpetual margin!")
        print(f"\n🎉 Your bot can now trade BTC perpetuals!")
        print(f"=" * 70)
    else:
        print(f"\n❌ Transfer failed!")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Verify the transfer
print(f"\n\n🔍 Verifying margin balance...")
time.sleep(2)

try:
    response = requests.post(
        f"{API_URL}/info",
        json={
            "type": "clearinghouseState",
            "user": WALLET_ADDRESS
        },
        timeout=10
    )
    
    if response.status_code == 200:
        data = response.json()
        margin = data.get('marginSummary', {})
        balance = float(margin.get('accountValue', 0))
        
        print(f"\n💰 New Margin Balance: ${balance:,.2f}")
        
        if balance > 0:
            print(f"✅ Transfer confirmed! Bot is ready to trade!")
        else:
            print(f"⏳ Balance not updated yet. May take a few seconds...")
            
except Exception as e:
    print(f"Error checking balance: {e}")
