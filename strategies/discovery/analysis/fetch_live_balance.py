#!/usr/bin/env python3
"""
💰 Live Balance Fetcher
Retrieves the current account value from Hyperliquid Mainnet.
"""
import os
import sys
import os
import sys

# Manual .env loader
def load_env(filepaths=[".env.live_trading", ".env"]):
    for filepath in filepaths:
        if os.path.exists(filepath):
            print(f"📂 Loading {filepath}...")
            with open(filepath, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip().strip("'").strip('"')
                        value = value.strip().strip("'").strip('"')
                        # Only set if not already set or if current value is placeholder
                        if not os.getenv(key) or "your_" in os.getenv(key).lower():
                            os.environ[key] = value

load_env()

from hyperliquid_live_trader import HyperliquidTrader

def fetch_balance():
    print("🔍 Connecting to Hyperliquid Mainnet...")
    
    # Safe Diagnostic
    pk = os.getenv('HYPERLIQUID_API_SECRET', '')
    if pk:
        print(f"📦 credential Check: Length={len(pk)}")
        # Check for invisible chars
        print(f"📦 Prefix Check: '{pk[:4]}...' | Suffix Check: '...{pk[-4:]}'")
    else:
        print("❌ HYPERLIQUID_API_SECRET not found in environment")
        
    try:
        # Initialize trader (testnet=False for Mainnet)
        trader = HyperliquidTrader(testnet=False)
        
        # Get account info
        account = trader.get_account_info()
        
        print("\n" + "="*40)
        print("🏦 HYPERLIQUID ACCOUNT SUMMARY")
        print("="*40)
        print(f"📍 Wallet:  {trader.wallet_address}")
        print(f"💰 Balance: ${account['balance']:,.2f}")
        print("="*40)
        
        if account['balance'] < 10:
            print("\n⚠️  Low balance detected. Ensure you have enough to cover initial orders.")
            
    except Exception as e:
        print(f"❌ Error fetching balance: {e}")

if __name__ == "__main__":
    fetch_balance()
