import sys
import os
import time
import requests
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Import local modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hyperliquid_live_trader import HyperliquidTrader

def get_current_price(coin="BTC"):
    """Fetch current price to build a valid signal"""
    url = "https://api.hyperliquid.xyz/info"
    payload = {"type": "allMids"}
    try:
        r = requests.post(url, json=payload, timeout=5)
        data = r.json()
        return float(data[coin])
    except Exception as e:
        print(f"❌ Failed to fetch price: {e}")
        return None

def test_live_execution_drill():
    print("\n🚨 LIVE ORDER EXECUTION DRILL 🚨")
    print("========================================")
    print("WARNING: This script will PLACE A REAL ORDER on Hyperliquid.")
    print("It will:")
    print("  1. Buy BTC (Market Order)")
    print("  2. Set Take Profit (+0.3%) and Stop Loss (-0.5%)")
    print("  3. Verify the position is open")
    print("  4. Wait 10 seconds")
    print("  5. SELL BTC (Market Close) to reset")
    print("========================================")
    
    # 1. Environment Check
    addr = os.getenv('HYPERLIQUID_WALLET_ADDRESS')
    key = os.getenv('HYPERLIQUID_API_SECRET')
    
    if not addr or not key:
        print("❌ CREDENTIALS MISSING!")
        print("   Please set HYPERLIQUID_WALLET_ADDRESS and HYPERLIQUID_API_SECRET in your .env")
        return

    print(f"   Wallet: {addr}")
    # print(f"   Key:    {key[:6]}...{key[-4:]}") # Don't print keys in logs
    
    # Ask for confirmation
    mode_input = input("\nType 'TESTNET' or 'MAINNET' to choose network: ").strip().upper()
    if mode_input not in ['TESTNET', 'MAINNET']:
        print("❌ Invalid mode. Aborting.")
        return
        
    is_testnet = (mode_input == 'TESTNET')
    
    confirm = input(f"\nType 'FIRE' to execute a REAL {'TESTNET' if is_testnet else 'MAINNET'} trade now: ")
    if confirm != 'FIRE':
        print("❌ Drill Aborted.")
        return

    print("\n🚀 INITIALIZING TRADER...")
    try:
        trader = HyperliquidTrader(testnet=is_testnet)
    except Exception as e:
        print(f"❌ Initialization Failed: {e}")
        return

    # 2. Check Balance
    info = trader.get_account_info()
    balance = info.get('balance', 0)
    print(f"💰 Account Balance: ${balance:.2f}")
    
    if balance < 5:
        print("❌ Insufficient balance for test (Need > $5). Aborting.")
        return

    # 3. Get Price & Build Singal
    price = get_current_price("BTC")
    if not price:
        return
        
    print(f"📉 Current BTC Price: ${price:,.2f}")
    
    signal = {
        'model': 'DRILL_TEST_SCRIPT',
        'price': price,
        'direction': 'LONG', # We test Long
        'confidence': 0.9999
    }
    
    # 4. Execute Signal
    print("\n👉 EXECUTING TEST ORDER NOW...")
    success = trader.execute_signal(signal)
    
    if not success:
        print("❌ Trade Execution Failed.")
        return
        
    print("\n✅ ORDER PLACED SUCCESSFULLY.")
    
    # 5. Verification Phase
    print("\n🔍 VERIFYING POSITION ON EXCHANGE...")
    time.sleep(3) # Wait for settlement
    
    info_post = trader.get_account_info()
    positions = info_post.get('positions', [])
    
    btc_pos = next((p for p in positions if p['coin'] == 'BTC'), None)
    
    if btc_pos and float(btc_pos['szi']) != 0:
        print(f"   ✅ Position Confirmed on Exchange!")
        print(f"      Size: {btc_pos['szi']} BTC")
        print(f"      Entry: ${float(btc_pos['entryPx']):,.2f}")
        print(f"      Unrealized PnL: ${float(btc_pos['unrealizedPnl']):,.2f}")
    else:
        print("   ⚠️  Warning: Position not found in account summary (might be closed or delayed).")

    # 6. Cleanup Phase
    print("\n⏳ Waiting 5 seconds before cleanup...")
    for i in range(5, 0, -1):
        print(f"   {i}...", end='\r')
        time.sleep(1)
    print("   Done.")
        
    print("\n🧹 CLEANING UP (Closing Position)...")
    trader.emergency_stop_all()
    
    print("\n✅ DRILL COMPLETE. Position Closed.")
    print(f"   Final Balance: ${trader.get_account_info().get('balance', 0):.2f}")

if __name__ == "__main__":
    test_live_execution_drill()
