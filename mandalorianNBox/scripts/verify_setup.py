"""
Quick Setup Verification Script
Run this to check if everything is ready for backtesting
"""

import sys
import os

print("=" * 60)
print("🔍 VERIFYING BACKTEST SETUP")
print("=" * 60)
print()

# Check 1: Python version
print("1. Checking Python version...")
python_version = sys.version_info
if python_version.major >= 3 and python_version.minor >= 8:
    print(f"   ✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
else:
    print(f"   ❌ Python {python_version.major}.{python_version.minor} - Need 3.8+")
    sys.exit(1)

# Check 2: Required packages
print("\n2. Checking required packages...")
required_packages = {
    'backtrader': 'backtrader',
    'pandas': 'pandas',
    'numpy': 'numpy'
}

missing_packages = []
for package_name, import_name in required_packages.items():
    try:
        __import__(import_name)
        print(f"   ✅ {package_name}")
    except ImportError:
        print(f"   ❌ {package_name} - MISSING")
        missing_packages.append(package_name)

if missing_packages:
    print(f"\n   ⚠️  Install missing packages:")
    print(f"   pip install {' '.join(missing_packages)}")
    sys.exit(1)

# Check 3: Data files
print("\n3. Checking historical data files...")
data_dir = os.path.join(os.path.dirname(__file__), 'datasets')
if os.path.exists(data_dir):
    csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
    if csv_files:
        print(f"   ✅ Found {len(csv_files)} data file(s):")
        for f in csv_files:
            file_path = os.path.join(data_dir, f)
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            print(f"      - {f} ({size_mb:.1f} MB)")
    else:
        print("   ❌ No CSV files found in datasets/")
        sys.exit(1)
else:
    print("   ❌ datasets/ directory not found")
    sys.exit(1)

# Check 4: Backtest script
print("\n4. Checking backtest script...")
script_path = os.path.join(os.path.dirname(__file__), 'backtest_ready.py')
if os.path.exists(script_path):
    print("   ✅ backtest_ready.py exists")
else:
    print("   ❌ backtest_ready.py not found")
    sys.exit(1)

# Check 5: Test backtrader import
print("\n5. Testing backtrader functionality...")
try:
    import backtrader as bt
    print("   ✅ Backtrader imports successfully")
    print(f"   ✅ Backtrader version: {bt.__version__ if hasattr(bt, '__version__') else 'Unknown'}")
except Exception as e:
    print(f"   ❌ Backtrader error: {e}")
    sys.exit(1)

# Final summary
print("\n" + "=" * 60)
print("✅ SETUP VERIFICATION COMPLETE")
print("=" * 60)
print()
print("🎉 Everything is ready for backtesting!")
print()
print("🚀 Next step: Run your backtest")
print("   python backtest_ready.py")
print()
print("📊 No APIs, no accounts, no external services needed!")
print("   Everything runs locally with your data files.")
print()

