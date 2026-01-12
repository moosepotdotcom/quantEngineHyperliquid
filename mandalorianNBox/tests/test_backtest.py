"""
Quick test script to verify backtesting setup works
Run this to test your backtesting environment
"""

import sys

def test_imports():
    """Test if backtesting packages are installed"""
    print("🔍 Testing backtesting packages...")
    
    packages = {
        'backtrader': 'backtrader',
        'pandas': 'pandas',
        'numpy': 'numpy',
        'matplotlib': 'matplotlib',
    }
    
    missing = []
    for package_name, import_name in packages.items():
        try:
            __import__(import_name)
            print(f"  ✅ {package_name}")
        except ImportError:
            print(f"  ❌ {package_name} - MISSING")
            missing.append(package_name)
    
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print("   Install with: pip install " + " ".join(missing))
        return False
    else:
        print("\n✅ All backtesting packages installed!")
        return True

def test_data_files():
    """Test if data files exist"""
    print("\n📁 Testing data files...")
    
    import os
    
    data_files = [
        'datasets/BTCUSD-1d-1000wks-data.csv',
        'datasets/BTCUSD-1h-500wks-data.csv',
        'datasets/BTCUSD-6h-500wks-data.csv'
    ]
    
    found = []
    missing = []
    
    for file in data_files:
        if os.path.exists(file):
            print(f"  ✅ {file}")
            found.append(file)
        else:
            print(f"  ⚠️  {file} - Not found")
            missing.append(file)
    
    if missing:
        print(f"\n⚠️  Some data files missing (that's okay, you can download more)")
    else:
        print("\n✅ All data files found!")
    
    return len(found) > 0

def test_simple_backtest():
    """Run a simple backtest to verify it works"""
    print("\n🧪 Running simple backtest test...")
    
    try:
        import backtrader as bt
        import pandas as pd
        from datetime import datetime
        
        # Create a simple strategy
        class TestStrategy(bt.Strategy):
            def next(self):
                if not self.position:
                    if self.data.close[0] > self.data.close[-1]:
                        self.buy()
                else:
                    if self.data.close[0] < self.data.close[-1]:
                        self.sell()
        
        # Create cerebro
        cerebro = bt.Cerebro()
        cerebro.addstrategy(TestStrategy)
        
        # Try to load data (use first available file)
        import os
        data_files = [
            'datasets/BTCUSD-1d-1000wks-data.csv',
            'datasets/BTCUSD-1h-500wks-data.csv',
            'datasets/BTCUSD-6h-500wks-data.csv'
        ]
        
        data_file = None
        for file in data_files:
            if os.path.exists(file):
                data_file = file
                break
        
        if not data_file:
            print("  ⚠️  No data files found - skipping backtest test")
            print("     (You can still run backtests with your own data)")
            return True
        
        # Load data
        df = pd.read_csv(data_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        # Convert to backtrader format
        data = bt.feeds.PandasData(dataname=df)
        cerebro.adddata(data)
        
        # Set initial cash
        cerebro.broker.set_cash(100000)
        cerebro.broker.setcommission(commission=0.001)
        
        # Run backtest
        print(f"  📊 Testing with {data_file}...")
        cerebro.run()
        
        # Get final value
        final_value = cerebro.broker.getvalue()
        print(f"  ✅ Backtest completed!")
        print(f"     Final portfolio value: ${final_value:,.2f}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Backtest failed: {e}")
        print("     This might be okay - check the error above")
        return False

def main():
    print("=" * 60)
    print("🧪 Backtesting Setup Test")
    print("=" * 60)
    print()
    
    # Test imports
    imports_ok = test_imports()
    
    # Test data files
    data_ok = test_data_files()
    
    # Test backtest
    if imports_ok:
        backtest_ok = test_simple_backtest()
    else:
        backtest_ok = False
        print("\n⚠️  Skipping backtest test (packages missing)")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    if imports_ok and backtest_ok:
        print("✅ All tests passed! You're ready to backtest!")
        print("\nNext steps:")
        print("1. Run: python 13_backtesting.py")
        print("2. Modify strategies in the backtest file")
        print("3. Test different indicators and timeframes")
        return 0
    elif imports_ok:
        print("⚠️  Packages installed, but backtest had issues")
        print("   Check the error above and try running 13_backtesting.py")
        return 1
    else:
        print("❌ Some packages are missing")
        print("\nInstall missing packages:")
        print("  pip install backtrader matplotlib pandas numpy")
        return 1

if __name__ == "__main__":
    sys.exit(main())

