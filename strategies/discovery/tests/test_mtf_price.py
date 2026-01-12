#!/usr/bin/env python3
"""
Diagnostic script to test MTF Scalper price issue
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from quant_engine import TradingEngine

print("Testing MTF Scalper price capture...")
print("="*70)

engine = TradingEngine()

print("\nFetching 5M data and checking price...")
df_5m = engine.fetch_data('5m', 10)

if df_5m is not None:
    print(f"\n5M DataFrame shape: {df_5m.shape}")
    print(f"5M DataFrame columns: {list(df_5m.columns)}")
    print(f"\nLast 3 rows of 5M data:")
    print(df_5m[['timestamp', 'open', 'high', 'low', 'close', 'volume']].tail(3))
    
    print(f"\nLatest close price: ${df_5m.iloc[-1]['close']:,.2f}")
    
    # Test after setting index
    df_test = df_5m.copy()
    df_test.set_index('timestamp', inplace=True)
    print(f"\nAfter set_index, latest close: ${df_test.iloc[-1]['close']:,.2f}")
    
    # Test the actual MTF Scalper function
    print("\n" + "="*70)
    print("Testing actual MTF Scalper function...")
    signal, conf = engine.check_mtf_scalper()
    
    if signal:
        print(f"\n✅ Signal detected!")
        print(f"   Price: ${signal['price']:,.2f}")
        print(f"   Confidence: {signal['confidence']:.2%}")
        print(f"   RSI: {signal['rsi']:.1f}")
        print(f"   MACD: {signal['macd']:.2f}")
    else:
        print(f"\n❌ No signal (confidence: {conf:.2%})")
else:
    print("❌ Failed to fetch 5M data")

print("\n" + "="*70)
print("Diagnostic complete!")
