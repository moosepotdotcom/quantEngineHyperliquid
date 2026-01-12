import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta, timezone

def get_candles(start, end, interval='1m'):
    url = "https://api.hyperliquid.xyz/info"
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": "BTC",
            "interval": interval,
            "startTime": int(start.timestamp() * 1000),
            "endTime": int(end.timestamp() * 1000)
        }
    }
    resp = requests.post(url, json=payload)
    if not resp.ok: return pd.DataFrame()
    data = resp.json()
    if not data: return pd.DataFrame()
    df = pd.DataFrame(data)
    df['t'] = pd.to_datetime(df['t'], unit='ms', utc=True)
    df['c'] = df['c'].astype(float)
    df['l'] = df['l'].astype(float)
    df['h'] = df['h'].astype(float)
    return df

def simulate_trade_duration(entry_time, direction, entry_price):
    # Get 48h of data from entry
    end_time = entry_time + timedelta(hours=48)
    df = get_candles(entry_time, end_time)
    
    if df.empty: return None
    
    tp_pct = 0.015
    sl_pct = 0.008
    
    if direction == "LONG":
        tp = entry_price * (1 + tp_pct)
        sl = entry_price * (1 - sl_pct)
    else:
        tp = entry_price * (1 - tp_pct)
        sl = entry_price * (1 + sl_pct)
        
    for idx, row in df.iterrows():
        # Check Win
        if direction == "LONG":
            if row['h'] >= tp:
                duration = (row['t'] - entry_time).total_seconds() / 60
                return duration  # Mins
            if row['l'] <= sl:
                return -1 # Loss
        else:
             if row['l'] <= tp:
                duration = (row['t'] - entry_time).total_seconds() / 60
                return duration
             if row['h'] >= sl:
                return -1
                
    return None # Open

def check_trend_flip(start_time, end_time):
    # Check 1H trend
    url = "https://api.hyperliquid.xyz/info"
    # Need history for EMA
    hist_start = start_time - timedelta(hours=100)
    
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": "BTC",
            "interval": "1h",
            "startTime": int(hist_start.timestamp() * 1000),
            "endTime": int(end_time.timestamp() * 1000)
        }
    }
    resp = requests.post(url, json=payload)
    df = pd.DataFrame(resp.json())
    df['t'] = pd.to_datetime(df['t'], unit='ms', utc=True)
    df['c'] = df['c'].astype(float)
    
    df['ema20'] = df['c'].ewm(span=20).mean()
    df['ema50'] = df['c'].ewm(span=50).mean()
    df['trend'] = np.where(df['ema20'] > df['ema50'], 'BULL', 'BEAR')
    
    # Filter for the hold period
    period = df[(df['t'] >= start_time) & (df['t'] <= end_time)]
    
    last_trend = None
    flip_time = None
    
    for idx, row in period.iterrows():
        curr = row['trend']
        if last_trend and curr != last_trend:
            return row['t'], last_trend, curr
        last_trend = curr
        
    return None, None, None

print("⏱️ TRADE DURATION ANALYSIS")
print("-" * 60)

trades = [
    # Samples from the week
    ("2026-01-05 00:00:00", "LONG", 91797), # Jan 5 Start
    ("2026-01-05 14:00:00", "LONG", 92848), # Jan 5 Mid
    ("2026-01-06 21:05:00", "LONG", 92433), # Jan 6 Sniper
    ("2026-01-07 22:15:00", "SHORT", 93000), # Jan 7 Waterfall
    ("2026-01-08 02:00:00", "SHORT", 91000), # Jan 8 Cont
]

durations = []
for t in trades:
    entry = datetime.strptime(t[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    dur_min = simulate_trade_duration(entry, t[1], t[2])
    if dur_min and dur_min > 0:
        durations.append(dur_min)
        print(f"Trade {t[0]}: {dur_min:.1f} minutes")

avg_dur = sum(durations) / len(durations)
print(f"\nAverage WIN Duration: {avg_dur:.1f} minutes ({avg_dur/60:.1f} hours)")

print("\n📉 TREND FLIP ANALYSIS (Jan 5 Zombie Trades)")
print("-" * 60)
# Check if Trend flipped during the 23h hold of Jan 5 trades
# Entry: Jan 5 17:00. Stop Hit: Jan 6 16:15.
zombie_start = datetime(2026, 1, 5, 17, 0, 0, tzinfo=timezone.utc)
zombie_end = datetime(2026, 1, 6, 16, 0, 0, tzinfo=timezone.utc)

flip_time, from_t, to_t = check_trend_flip(zombie_start, zombie_end)
if flip_time:
    print(f"⚠️ TREND FLIPPED at {flip_time}!")
    print(f"   Changed from {from_t} to {to_t}")
    diff = (flip_time - zombie_start).total_seconds() / 3600
    print(f"   Time since entry: {diff:.1f} hours")
else:
    print("Trend did NOT flip during the hold.")
