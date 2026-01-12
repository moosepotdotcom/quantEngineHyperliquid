"""
Test script to verify your setup is working correctly.
Run this before starting any trading bots.
"""

import sys

def test_imports():
    """Test if all required packages are installed"""
    print("🔍 Testing package imports...")
    
    required_packages = {
        'ccxt': 'ccxt',
        'pandas': 'pandas',
        'numpy': 'numpy',
        'schedule': 'schedule',
        'requests': 'requests',
        'eth_account': 'eth_account',
        'hyperliquid': 'hyperliquid',
        'pandas_ta': 'pandas_ta',
    }
    
    missing = []
    for package_name, import_name in required_packages.items():
        try:
            __import__(import_name)
            print(f"  ✅ {package_name}")
        except ImportError:
            print(f"  ❌ {package_name} - MISSING")
            missing.append(package_name)
    
    # Optional packages
    optional_packages = {
        'backtrader': 'backtrader',
        'talib': 'talib',
        'yfinance': 'yfinance',
    }
    
    print("\n📦 Optional packages:")
    for package_name, import_name in optional_packages.items():
        try:
            __import__(import_name)
            print(f"  ✅ {package_name}")
        except ImportError:
            print(f"  ⚠️  {package_name} - Optional (not required)")
    
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print("   Install with: pip install -r requirements.txt")
        return False
    else:
        print("\n✅ All required packages are installed!")
        return True

def test_config_files():
    """Test if config files exist and are configured"""
    print("\n🔐 Testing configuration files...")
    
    # Check dontshare.py
    try:
        import dontshare as d
        if hasattr(d, 'private_key') and d.private_key != 'YOUR_HYPERLIQUID_PRIVATE_KEY_HERE':
            print("  ✅ dontshare.py - Configured")
            return True
        else:
            print("  ⚠️  dontshare.py - Found but not configured")
            print("     Edit dontshare.py and add your HyperLiquid private key")
            return False
    except ImportError:
        print("  ❌ dontshare.py - File not found")
        print("     Create dontshare.py with your HyperLiquid private key")
        return False

def test_hyperliquid_connection():
    """Test HyperLiquid API connection"""
    print("\n🌐 Testing HyperLiquid connection...")
    
    try:
        import requests
        import json
        
        url = 'https://api.hyperliquid.xyz/info'
        headers = {'Content-Type': 'application/json'}
        data = {'type': 'meta'}
        
        response = requests.post(url, headers=headers, data=json.dumps(data))
        
        if response.status_code == 200:
            print("  ✅ HyperLiquid API - Connected")
            return True
        else:
            print(f"  ⚠️  HyperLiquid API - Status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ HyperLiquid API - Connection failed: {e}")
        return False

def main():
    print("=" * 50)
    print("🧪 ATC Bootcamp - Setup Test")
    print("=" * 50)
    print()
    
    # Test imports
    imports_ok = test_imports()
    
    # Test config
    config_ok = test_config_files()
    
    # Test connection
    connection_ok = test_hyperliquid_connection()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    
    if imports_ok and config_ok and connection_ok:
        print("✅ All tests passed! You're ready to run bots.")
        print("\nNext steps:")
        print("1. Review bot settings in the bot file")
        print("2. Start with small position sizes")
        print("3. Run: python 10_day10_bots/day10_hyperliquid/10_bollinger_bot.py")
        return 0
    else:
        print("⚠️  Some tests failed. Please fix the issues above.")
        print("\nSee SETUP_GUIDE.md for detailed instructions.")
        return 1

if __name__ == "__main__":
    sys.exit(main())



