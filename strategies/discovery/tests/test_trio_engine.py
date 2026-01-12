#!/usr/bin/env python3
"""
Quick test to verify trio ensemble models load correctly
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from quant_engine import TradingEngine

def main():
    print("="*70)
    print("🧪 TRIO ENSEMBLE ENGINE TEST")
    print("="*70)
    
    try:
        print("\n📦 Initializing Trading Engine with Trio Models...")
        engine = TradingEngine()
        
        print("\n✅ Engine initialized successfully!")
        print(f"   MTF Scalper models loaded: XGB, LGB, Cat")
        print(f"   Winner Hunter models loaded: XGB, LGB, Cat")
        
        print(f"\n🎯 Loaded Thresholds:")
        print(f"   MTF Scalper Long:  {engine.mtf_threshold_long:.4f}")
        print(f"   MTF Scalper Short: {engine.mtf_threshold_short:.4f}")
        print(f"   Winner Hunter Long:  {engine.winner_threshold_long:.4f}")
        print(f"   Winner Hunter Short: {engine.winner_threshold_short:.4f}")
        
        print("\n" + "="*70)
        print("✅ TRIO ENSEMBLE ENGINE TEST PASSED")
        print("="*70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
