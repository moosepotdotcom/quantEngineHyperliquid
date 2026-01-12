#!/usr/bin/env python3
"""
Deployment Verification Script
Ensures all files and configurations are correct before launch
"""

import os
import json
import sys

def check_models():
    """Verify model files exist and have correct sizes"""
    print("🔍 Checking Model Files...")
    
    models_required = [
        ("models/mtf_scalper_5m_trio_xgb.json", 6900000, 7100000),  # 6.9MB ±0.2MB
        ("models/mtf_scalper_5m_trio_lgb.json", 990000, 1010000),    # 992KB ±20KB
        ("models/mtf_scalper_5m_trio_cat.json", 200000, 210000),     # 206KB ±10KB
        ("models/mtf_scalper_5m_trio_metadata.json", 300, 500),      # ~405 bytes
        ("models/winner_hunter_1h_trio_xgb.json", 2000000, 2100000), # 2MB ±100KB
        ("models/winner_hunter_1h_trio_lgb.json", 160000, 170000),   # 166KB ±10KB
        ("models/winner_hunter_1h_trio_cat.json", 170000, 180000),   # 173KB ±10KB
        ("models/winner_hunter_1h_trio_metadata.json", 400, 500),    # ~457 bytes
    ]
    
    all_ok = True
    for filepath, min_size, max_size in models_required:
        if not os.path.exists(filepath):
            print(f"   ❌ MISSING: {filepath}")
            all_ok = False
        else:
            size = os.path.getsize(filepath)
            if min_size <= size <= max_size:
                print(f"   ✅ {filepath} ({size:,} bytes)")
            else:
                print(f"   ⚠️  {filepath} size mismatch ({size:,} bytes, expected {min_size:,}-{max_size:,})")
                all_ok = False
    
    return all_ok

def check_configuration():
    """Verify critical configuration values"""
    print("\n🔍 Checking Configuration...")
    
    # Check quant_engine.py for correct thresholds
    try:
        with open('quant_engine.py', 'r') as f:
            content = f.read()
            
        checks = [
            ("self.mtf_threshold_long = 0.4500", "MTF LONG threshold"),
            ("self.mtf_threshold_short = 0.4500", "MTF SHORT threshold"),
            ("Adaptive Volatility", "Adaptive Shield implementation"),
            ("CircuitBreaker", "Circuit Breaker class"),
        ]
        
        all_ok = True
        for check_str, desc in checks:
            if check_str in content:
                print(f"   ✅ {desc} verified")
            else:
                print(f"   ❌ {desc} NOT FOUND")
                all_ok = False
        
        return all_ok
    except FileNotFoundError:
        print("   ❌ quant_engine.py NOT FOUND")
        return False

def check_dependencies():
    """Check if required packages are installed"""
    print("\n🔍 Checking Dependencies...")
    
    required_packages = [
        "pandas", "numpy", "xgboost", "lightgbm", 
        "catboost", "sklearn", "requests", "ta"
    ]
    
    all_ok = True
    for package in required_packages:
        try:
            __import__(package)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} NOT INSTALLED")
            all_ok = False
    
    return all_ok

def check_environment():
    """Check if .env file is configured"""
    print("\n🔍 Checking Environment Configuration...")
    
    if not os.path.exists('.env'):
        print("   ⚠️  .env file NOT FOUND (copy .env.example and configure)")
        return False
    
    with open('.env', 'r') as f:
        content = f.read()
    
    if 'your_private_key_here' in content or 'HYPERLIQUID_PRIVATE_KEY=' not in content:
        print("   ⚠️  .env file not configured (update HYPERLIQUID_PRIVATE_KEY)")
        return False
    else:
        print("   ✅ .env file configured")
        return True

def main():
    print("=" * 60)
    print("🛡️  ADAPTIVE SHIELD V1 - DEPLOYMENT VERIFICATION")
    print("=" * 60)
    print()
    
    results = {}
    results['models'] = check_models()
    results['config'] = check_configuration()
    results['dependencies'] = check_dependencies()
    results['environment'] = check_environment()
    
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)
    
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {check.upper()}: {status}")
    
    if all(results.values()):
        print("\n✅ ALL CHECKS PASSED - READY FOR DEPLOYMENT")
        return 0
    else:
        print("\n❌ SOME CHECKS FAILED - RESOLVE ISSUES BEFORE DEPLOYMENT")
        return 1

if __name__ == "__main__":
    sys.exit(main())
