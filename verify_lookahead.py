
import pandas as pd
import numpy as np

def verify_lookahead():
    print("🕵️‍♂️ Auditing Feature Engineering for Time Travel (Lookahead Bias)...")
    
    # 1. Create Mock 15m Data (Start Time)
    # Candle 1: 12:00 -> 12:15. Close = 100.
    # Candle 2: 12:15 -> 12:30. Close = 200.
    ts_15m = pd.to_datetime(['2026-01-01 12:00', '2026-01-01 12:15'])
    df_15m = pd.DataFrame({
        'timestamp': ts_15m,
        'close_15m': [100, 200]
    }).set_index('timestamp')
    
    # 2. Create Mock 5m Data
    # 12:00, 12:05, 12:10, 12:15
    ts_5m = pd.to_datetime([
        '2026-01-01 12:00', # Should see Prev (None) or 100? Valid: None (12:00 just started). Leak: 100.
        '2026-01-01 12:05', # Should see Prev (None). Valid: None. Leak: 100.
        '2026-01-01 12:10', # Should see Prev (None). Valid: None. Leak: 100.
        '2026-01-01 12:15'  # Should see 12:00 (100). Valid: 100. Leak: 200.
    ])
    df_5m = pd.DataFrame({'timestamp': ts_5m, 'close_5m': [10, 11, 12, 13]}).set_index('timestamp')
    
    print("\n--- Mock Data ---\n")
    print("15m Data (Indexed by Start Time):")
    print(df_15m)
    print("\n5m Data:")
    print(df_5m)
    
    
    # 3. Apply NEW Logic (Shift 1)
    print("   Applying Fix: Shift(1)...")
    shifted = df_15m.shift(1)
    merged = shifted.reindex(df_5m.index, method='ffill')
    
    print("\n--- Merged Result (Simulating Current Logic) ---\n")
    print(merged)
    
    # 4. Analyze 12:05
    val_at_1205 = merged.loc['2026-01-01 12:05', 'close_15m']
    print(f"\nAt 12:05, the 15m feature is: {val_at_1205}")
    
    # 5. Verdict
    # Real Life: At 12:05, the 12:00-12:15 candle is NOT closed. 
    # Current Close is fluxing.
    # If we get 100 (which is the final Close of 12:00-12:15), we are trading on future info.
    
    if val_at_1205 == 100:
        print("\n❌ CRITICAL FAIL: LOOKAHEAD DETECTED.")
        print("   At 12:05, we are seeing the Final Close of the 12:00-12:15 candle.")
        print("   The model 'knows' how the 15m candle ends before it happens.")
    else:
        print("\n✅ PASS: No Lookahead.")

if __name__ == "__main__":
    verify_lookahead()
