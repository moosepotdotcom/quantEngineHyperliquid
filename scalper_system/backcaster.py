"""
🔮 BACKCASTER (Observe & Build)
Replays recorded live data to tune strategy parameters.
"""
import pandas as pd
import numpy as np
import sys
import os

# Path Hack
sys.path.append('.')

from scalper_system import config

from scalper_system import config

DATA_FILE = config.LIQ_DATA_FILE

def run_backcast(threshold_usd=50000, window_sec=60, tp=0.003, sl=0.005):
    print(f"\n🔮 BACKCAST SETTINGS")
    print(f"   File:      {DATA_FILE}")
    print(f"   Threshold: ${threshold_usd:,.0f}")
    print(f"   Window:    {window_sec}s")
    print(f"   TP/SL:     {tp:.1%}/{sl:.1%}")
    print("-" * 40)
    
    if not os.path.exists(DATA_FILE):
        print("❌ No data file found yet.")
        return

    # Load Data
    try:
        df = pd.read_csv(DATA_FILE)
        if df.empty or len(df) < 2:
            print("⚠️ Not enough data yet. Accumulating...")
            return
            
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
    except Exception as e:
        print(f"❌ Read Error: {e}")
        return
        
    print(f"📊 Analyzing {len(df)} recorded events...")
    
    # Simulation State
    trades = []
    capital = 100.0
    
    # We need to simulate the 'window' logic
    # Ideally, we iterate and maintain a rolling sum.
    
    # Simplified Vectorized Approach for Speed:
    # 1. Separate Long/Short Liqs
    # 2. Resample to 1s to fill gaps? No, let's iterate.
    
    short_liqs = [] # (time, usd)
    long_liqs = []  # (time, usd)
    
    last_signal_time = df['timestamp'].iloc[0] - pd.Timedelta(seconds=300)
    
    for i, row in df.iterrows():
        now = row['timestamp']
        usd = row['usd']
        price = row['price']
        
        # Add to window
        if row['type'] == 'SHORT':
            short_liqs.append((now, usd))
        else:
            long_liqs.append((now, usd))
            
        # Cleanup
        cutoff = now - pd.Timedelta(seconds=window_sec)
        short_liqs = [x for x in short_liqs if x[0] > cutoff]
        long_liqs = [x for x in long_liqs if x[0] > cutoff]
        
        # Check Signal
        current_short_vol = sum(x[1] for x in short_liqs)
        current_long_vol = sum(x[1] for x in long_liqs)
        
        # Cooldown check
        if (now - last_signal_time).total_seconds() < 300:
            continue
            
        signal = None
        
        # LOGIC
        if current_long_vol > threshold_usd:
            signal = 'BUY'
        elif current_short_vol > threshold_usd:
            signal = 'SELL'
            
        if signal:
            # Record Trade
            trades.append({
                'time': now,
                'signal': signal,
                'price': price,
                'reason': f"Vol: ${max(current_long_vol, current_short_vol):,.0f}"
            })
            last_signal_time = now
            
    # Calculate Outcomes (Approximation)
    # Since we don't have future ticks *between* events, we look ahead in the dataframe
    # This is an approximation. Real backtest needs full price history.
    # For "Observe & Build", we just want to see Signal Frequency first.
    
    print(f"\n🚀 SIGNALS GENERATED: {len(trades)}")
    for t in trades[-5:]:
        print(f"   {t['time'].strftime('%H:%M:%S')} {t['signal']} @ {t['price']:.1f} ({t['reason']})")
        
    if len(trades) == 0:
        print("   (Try lowering the threshold?)")

if __name__ == "__main__":
    # Default run
    run_backcast(threshold_usd=10000) # Test with 10k
    
    # Parameter Sweep Example
    # run_backcast(threshold_usd=5000)
    # run_backcast(threshold_usd=50000)
