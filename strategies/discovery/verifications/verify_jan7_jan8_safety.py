import pandas as pd
import numpy as np
import requests
from datetime import datetime, timezone, timedelta
import ta

# --- Re-use Hurst calculation ---
def calculate_hurst(series, max_window=20):
    try:
        lags = range(2, min(max_window, 20))
        tau = [np.sqrt(np.std(np.subtract(series[lag:], series[:-lag]))) for lag in lags]
        m = np.polyfit(np.log(lags), np.log(tau), 1)
        return m[0] * 2.0
    except:
        return 0.5

def get_data_around(target_time):
    start = target_time - timedelta(hours=5)
    end = target_time + timedelta(minutes=15)
    
    url = "https://api.hyperliquid.xyz/info"
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": "BTC",
            "interval": "5m",
            "startTime": int(start.timestamp() * 1000),
            "endTime": int(end.timestamp() * 1000)
        }
    }
    resp = requests.post(url, json=payload)
    df = pd.DataFrame(resp.json())
    df['t'] = pd.to_datetime(df['t'], unit='ms', utc=True)
    df['close'] = df['c'].astype(float)
    return df

print("🛡️ SAFETY CHECK: JAN 7 & JAN 8")
print("-" * 60)

checkpoints = [
    ("Jan 8 Win (Short)", datetime(2026, 1, 8, 2, 0, 0, tzinfo=timezone.utc), "SHORT"),
    ("Jan 7 Win (Short)", datetime(2026, 1, 7, 22, 15, 0, tzinfo=timezone.utc), "SHORT")
]

print(f"{'Date':<20} | {'Type':<6} | {'RSI':<6} | {'Hurst':<6} | {'Filter Action'}")
print("-" * 60)

for label, dt, direction in checkpoints:
    df = get_data_around(dt)
    
    # Calculate Indicators
    df['rsi'] = ta.momentum.rsi(df['close'], window=14)
    
    # Calculate Hurst
    series = df['close'].values
    # Get last 100 candles up to target
    target_idx = df[df['t'] <= dt].index[-1]
    chunk = series[max(0, target_idx-100):target_idx+1]
    hurst = calculate_hurst(chunk)
    
    rsi_val = df.iloc[target_idx]['rsi']
    
    # Logic Verification
    # Filter: if direction == 'LONG' and rsi < 30 and hurst > 0.50 -> BLOCK
    
    action = "✅ ALLOW"
    reason = ""
    
    if direction != 'LONG':
        reason = "(Not Long)"
    elif rsi_val >= 30:
        reason = "(RSI >= 30)"
    elif hurst <= 0.50:
        reason = "(Hurst <= 0.50)"
    else:
        action = "🛑 BLOCK"
        reason = "Falling Knife!"
        
    print(f"{label:<20} | {direction:<6} | {rsi_val:.1f}   | {hurst:.3f}  | {action} {reason}")

print("-" * 60)
print("VERDICT: The filter explicitly targets 'LONGDips'. It ignores Shorts completely.")
