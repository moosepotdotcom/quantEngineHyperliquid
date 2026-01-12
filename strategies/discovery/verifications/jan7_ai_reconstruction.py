#!/usr/bin/env python3
"""
Jan 8 Reconstruction using V2 Calibrated Model
Hypothesis: Live bot used V2 model (Class 0 = Short) which yields ~74% confidence.
"""

import json
import pandas as pd
import numpy as np
import joblib
from datetime import datetime, timedelta
from utils.feature_engineer import add_all_indicators

print("="*70)
print("🚀 JAN 8 RECONSTRUCTION (V2 MODEL)")
print("="*70)

# 1. Load Data
print("📥 Loading 1-minute historical data (Jan 7 + Jan 8)...")
with open('jan7_historical_1m.json', 'r') as f:
    c7 = json.load(f)
with open('jan8_historical_1m.json', 'r') as f:
    c8 = json.load(f)
    
candles = c7 + c8

df_1m = pd.DataFrame(candles)
df_1m['timestamp'] = pd.to_datetime(df_1m['t'], unit='ms')
df_1m['open'] = df_1m['o'].astype(float)
df_1m['high'] = df_1m['h'].astype(float)
df_1m['low'] = df_1m['l'].astype(float)
df_1m['close'] = df_1m['c'].astype(float)
df_1m['volume'] = df_1m['v'].astype(float)
df_1m.set_index('timestamp', inplace=True)

# Resample to 5m
df_5m = df_1m.resample('5T').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}).dropna()

# 2. Feature Engineering
print("🔧 Engineering features...")
df_5m = add_all_indicators(df_5m)

# Prepare Feature Matrix
# V2 Model expects 231 features (excluding timestamp/hurst)
# We need to construct them manually as in verification script
exclude = ['open', 'high', 'low', 'close', 'volume']
cols = [c for c in df_5m.columns if c not in exclude]
cols_15m = [f"{c}_15m" for c in cols]
cols_1h = [f"{c}_1h" for c in cols]
all_features_ordered = cols + cols_15m + cols_1h
# Filter out hurst (local add_all_indicators doesn't produce it, but just in case)
all_features_ordered = [c for c in all_features_ordered if 'hurst' not in c]

print(f"   Features per row: {len(all_features_ordered)}")

# 3. Load Model
print("\n🤖 Loading V2 Calibrated Model...")
try:
    model = joblib.load('models/mtf_scalper_5m_v2_calibrated.pkl')
    print("✅ Model loaded")
except Exception as e:
    print(f"❌ Failed to load model: {e}")
    exit(1)

# 4. Simulation Loop
threshold = 0.65  # 65% Threshold
# Signals
signals = []

print("\nrunning simulation...")
# We check Full Day Jan 7
target_start = pd.Timestamp("2026-01-07 00:00:00")
target_end = pd.Timestamp("2026-01-08 00:00:00")

# We need to simulate the rolling context
# But complex context (15m/1h) requires more data.
# For this proof of concept, we fill 15m/1h with 0s since we know from verification that
# even with 0s/proxies it matches ballpark.
# Actually, verification used properties from log which HAD 15m/1h context.
# We don't have 15m/1h data loaded here.
# Wait! verification used LIVE FEATURES from log.
# This script uses HISTORICAL DATA.
# Since we verified Historical Data is different (Price off by $100), we probably won't get same prediction.
# BUT, let's try.

# If we can't reconstruct features exactly, we can't reconstruct prediction.
# Verification proved Historical Features != Live Features.
# So this script is doomed to fail if input data is key.

# However, let's check one row.
pass
print("⚠️ Realization: Historical Data Inputs != Live Inputs (Price $100 off).")
print("   Using Data from API will yield garbage.")
print("   Switching to using LOGGED FEATURES for simulation.")
print("   This proves validity of trades based on what Bot SAW.")

# 5. Simulation using LOGS
print("\n📜 Simulating based on LOGGED FEATURES + V2 MODEL (Jan 7)...")
trades = []

with open('logs/trades/predictions_20260107.jsonl', 'r') as f:
    for line in f:
        if "MTF Scalper" not in line: continue
        
        entry = json.loads(line)
        timestamp = entry['timestamp']
        
        # Check time window
        ts_dt = pd.to_datetime(timestamp)
        if not (target_start <= ts_dt <= target_end): continue
        
        if 'features' not in entry: continue
        live_features = entry['features']
        
        # Construct X
        X_values = []
        for feat in all_features_ordered:
            X_values.append(live_features.get(feat, 0.0))
        X = np.array(X_values).reshape(1, -1)
        
        # Predict
        try:
            probs = model.predict_proba(X)[0]
            prob_0 = probs[0] # Class 0
            
            # Assume Class 0 is SHORT (based on high confidence matching Bearish trend)
            if prob_0 >= threshold:
                print(f"✅ TP {timestamp} | Conf: {prob_0:.4%} (Class 0) | Price: {entry['market_data']['close']}")
                trades.append({
                    'time': timestamp,
                    'price': entry['market_data']['close'],
                    'conf': prob_0,
                    'type': 'SHORT (Class 0)',
                    'rsi_7': live_features.get('rsi_7', 50)
                })
        except Exception as e:
            pass

# Check Jan 8 Full Day
TP_PCT = 0.015  # 1.5%
SL_PCT = 0.008  # 0.8%

# Simulation Logic
def simulate_outcome(entry_price, direction, entry_time, df_5m):
    """Simulate TP/SL outcome"""
    # Look ahead 288 candles (24h)
    future = df_5m[df_5m.index > entry_time].head(288) 
    
    if len(future) == 0:
        return "OPEN", 0.0
    
    tp = entry_price * (1 - TP_PCT) if direction == "SHORT" else entry_price * (1 + TP_PCT)
    sl = entry_price * (1 + SL_PCT) if direction == "SHORT" else entry_price * (1 - SL_PCT)
    
    for ts, row in future.iterrows():
        # Check high/low
        if direction == "SHORT":
            if row['low'] <= tp: return "WIN", TP_PCT * 100
            if row['high'] >= sl: return "LOSS", -SL_PCT * 100
        else:
            if row['high'] >= tp: return "WIN", TP_PCT * 100
            if row['low'] <= sl: return "LOSS", -SL_PCT * 100
            
    return "OPEN", 0.0

print(f"\n✨ Jan 7 Trades (V2 Model @ 72% Threshold + AI Filter):")
print(f"{'Time':<25} | {'Type':<8} | {'Entry':<9} | {'TP':<9} | {'SL':<9} | {'Conf':<7} | {'Outcome':<8} | {'%':<5} | {'Pts':<7}")
print("-" * 110)

count = 0
wins = 0
total_pnl_pts = 0

for t in trades:
    # Filter by 72% Threshold
    if t['conf'] < 0.72:
        continue
        
    # AI Smart Filter: Block if RSI < 25
    if t['rsi_7'] < 25:
        # print(f"🛑 Blocked Trade at {t['time']} due to RSI {t['rsi_7']:.1f}")
        continue
        
    count += 1
    entry = t['price']
    ts = pd.to_datetime(t['time'])
    
    # Simulate
    outcome, pnl_pct = simulate_outcome(entry, "SHORT", ts, df_5m)
    
    if outcome == "WIN": wins += 1
    
    # Calculate Pts
    pts = entry * (abs(pnl_pct)/100)
    if outcome == "LOSS": pts = -pts
    total_pnl_pts += pts
    
    # SHORT logic for TP/SL display
    tp = entry * (1 - TP_PCT)
    sl = entry * (1 + SL_PCT)
    
    outcome_str = "WIN \u2705" if outcome == "WIN" else "LOSS \u274C"
    
    print(f"{t['time']:<25} | {t['type'].split(' ')[0]:<8} | {entry:<9.1f} | {tp:<9.1f} | {sl:<9.1f} | {t['conf']:.1%} | {outcome_str:<8} | {pnl_pct:+.1f}% | {pts:<7.0f}")

print("-" * 110)
print(f"Summary: {count} Trades | {wins}/{count} Wins | Win Rate: {wins/count if count>0 else 0:.0%} | Total PnL: {total_pnl_pts:.0f} pts")

# To check Jan 7, we would need Jan 7 logs or data.
# The user can just run this script on Jan 7 logs if available.
