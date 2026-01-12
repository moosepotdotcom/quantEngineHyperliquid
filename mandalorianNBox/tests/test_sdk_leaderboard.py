
from hyperliquid.info import Info
from hyperliquid.utils import constants

try:
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    if hasattr(info, 'leaderboard'):
        print("✅ Message: SDK has leaderboard method!")
        # Try to call it? It might not exist or need args. I'll define a safe trial.
        # usually methods are like info.user_state(), so maybe info.leaderboard()
        # I will inspect the object dir first.
    
    # Inspect methods
    methods = [m for m in dir(info) if not m.startswith('_')]
    print(f"Available Methods: {methods}")
    
except Exception as e:
    print(f"❌ Error: {e}")
