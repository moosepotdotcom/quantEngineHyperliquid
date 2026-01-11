import sys
import os
import pandas as pd
import numpy as np
import warnings
from datetime import datetime, timedelta
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quant_engine import TradingEngine

def diagnose():
    print("🔍 DIAGNOSING 'OPEN' TRADES & DATA QUALITY")
    print("="*70)
    
    engine = TradingEngine()
    print("📥 Fetching Data (Limit 4000)...")
    df = engine.fetch_data('5m', 4000)
    
    if df is None or len(df) == 0:
        print("❌ Final verification fetch failed.")
        return
        
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.sort_values('timestamp', inplace=True)
    df.set_index('timestamp', inplace=True)
    
    print(f"   Range: {df.index.min()} to {df.index.max()}")
    print(f"   Total Rows: {len(df)}")
    
    # Check for Gaps > 10 mins
    time_diffs = df.index.to_series().diff().dropna()
    gaps = time_diffs[time_diffs > timedelta(minutes=10)]
    
    if len(gaps) > 0:
        print(f"\n⚠️  DATA GAPS DETECTED ({len(gaps)}):")
        for t, delta in gaps.head(10).items():
            print(f"   Gap at {t}: {delta}")
    else:
        print("\n✅ No significant data gaps detected.")

    # Inspect the OPEN trades behavior
    # Based on previous log: Jan 9 23:35 was OPEN.
    # Let's check price action from Jan 9 23:35 onwards.
    
    target_time = pd.Timestamp("2026-01-09 23:35:00")
    if target_time not in df.index:
        # Find closest
        target_time = df.index[df.index.get_indexer([target_time], method='nearest')[0]]
        print(f"   Adjusted target time to nearest: {target_time}")
        
    start_price = df.loc[target_time]['close']
    print(f"\n🧐 Analyzing Trade at {target_time} (Price: {start_price})")
    print(f"   Target: TP +1.5% ({start_price*1.015:.2f}) | SL -0.8% ({start_price*0.992:.2f})")
    
    future = df[df.index > target_time]
    
    hit_tp = False
    hit_sl = False
    
    for t, row in future.iterrows():
        h, l = row['high'], row['low']
        tp_p = start_price * 1.015
        sl_p = start_price * 0.992
        
        if h >= tp_p:
            print(f"   ✅ TP Hit at {t} (High: {h})")
            hit_tp = True
            break
        if l <= sl_p:
            print(f"   ❌ SL Hit at {t} (Low: {l})")
            hit_sl = True
            break
            
    if not hit_tp and not hit_sl:
        print("   ⚠️  Trade truly stays OPEN (Price remained in range)")
        max_h = future['high'].max()
        min_l = future['low'].min()
        print(f"       Max High: {max_h} ({(max_h/start_price-1)*100:.2f}%)")
        print(f"       Min Low:  {min_l} ({(min_l/start_price-1)*100:.2f}%)")

if __name__ == "__main__":
    diagnose()
