import sys
import os
import time
from datetime import datetime

print("🛑 PRE-DEPLOYMENT SAFETY CHECK")
print("============================")

def check_imports():
    print("1. Checking Imports...")
    try:
        import quant_engine
        import utils.fetch_data
        import utils.feature_engineer
        import utils.trend_filter
        import utils.advanced_features
        import hyperliquid_live_trader
        print("   ✅ All modules identifiable.")
    except Exception as e:
        print(f"   ❌ IMPORT ERROR: {e}")
        sys.exit(1)

def check_engine_init():
    print("2. Verifying Engine Initialization...")
    try:
        from quant_engine import TradingEngine
        # Dry run init
        engine = TradingEngine()
        print("   ✅ TradingEngine initializes correctly.")
    except Exception as e:
        print(f"   ❌ ENGINE INIT ERROR: {e}")
        sys.exit(1)

def check_required_files():
    print("3. Checking Critical Files...")
    required = [
        "quant_engine.py",
        "hyperliquid_live_trader.py",
        "utils/fetch_data.py",
        "utils/advanced_features.py"
    ]
    for f in required:
        if not os.path.exists(f):
            print(f"   ❌ MISSING FILE: {f}")
            sys.exit(1)
    print("   ✅ All critical files present.")

if __name__ == "__main__":
    try:
        check_required_files()
        check_imports()
        check_engine_init()
        print("\n✅ SAFETY CHECK PASSED. You may proceed with deployment.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        sys.exit(1)
