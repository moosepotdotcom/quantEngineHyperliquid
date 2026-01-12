
import os
from dotenv import load_dotenv
from hyperliquid.info import Info
from hyperliquid.utils import constants

load_dotenv()

def test_history():
    address = os.getenv('HYPERLIQUID_WALLET_ADDRESS')
    print(f"Testing history for {address}...")
    
    info = Info(base_url=constants.MAINNET_API_URL)
    
    # Test Fills
    try:
        fills = info.user_fills(address)
        print(f"\n✅ Fills fetched: {len(fills)} records")
        if len(fills) > 0:
            print(f"Sample Fill: {fills[0]}")
    except Exception as e:
        print(f"\n❌ Fills Error: {e}")

    # Test Funding
    # The method might be 'user_funding_history' or just 'user_funding'
    # Try 'user_funding' first
    try:
        # Note: Official SDK usually has user_funding(user, start_time, end_time)
        # We'll try fetching recent
        import time
        start_time = int((time.time() - 86400 * 7) * 1000) # Last 7 days
        funding = info.user_funding_history(address, start_time=start_time)
        print(f"\n✅ Funding fetched: {len(funding)} records")
        if len(funding) > 0:
            print(f"Sample Funding: {funding[0]}")
    except Exception as e:
        print(f"\n❌ Funding Error (user_funding_history): {e}")
        
    # specific 'funding_history' check if previous failed
        
if __name__ == "__main__":
    test_history()
