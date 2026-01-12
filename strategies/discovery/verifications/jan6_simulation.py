#!/usr/bin/env python3
"""
JAN 6 RECONSTRUCTION (Simulation Mode)
Since no logs match, we simulate using local models on historical data.
Limitation: Local models are binary (Hold/Long), so we only check for LONG signals.
Context: Jan 6 was likely BULLISH, so Long signals are relevant.
"""
import sys
import os
import pandas as pd
import numpy as np
import joblib
import requests
from datetime import datetime, timedelta
import json

sys.path.insert(0, os.path.dirname(__file__))
from utils.feature_engineer import add_all_indicators

# Configuration
THRESHOLDS = {
    'MTF Scalper (5M)': {'LONG': 0.6500} # Only Long available locally
}
TP_PCT = 0.015
SL_PCT = 0.008

def download_data(start_date, end_date, interval='1h'):
    """Download BTC data"""
    url = "https://api.hyperliquid.xyz/info"
    start_ms = int(start_date.timestamp() * 1000)
    end_ms = int(end_date.timestamp() * 1000)
    
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": "BTC",
            "interval": interval,
            "startTime": start_ms,
            "endTime": end_ms
        }
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=30)
        data = resp.json()
        if data:
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
            df['open'] = df['o'].astype(float)
            df['high'] = df['h'].astype(float)
            df['low'] = df['l'].astype(float)
            df['close'] = df['c'].astype(float)
            df['volume'] = df['v'].astype(float)
            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def simulate_outcome(entry_price, direction, entry_time, df_1m):
    """Simulate TP/SL"""
    future = df_1m[df_1m['timestamp'] > entry_time].head(2880) # 48 hours
    
    if len(future) == 0:
        return "OPEN", 0.0, None
    
    if direction == "LONG":
        tp = entry_price * (1 + TP_PCT)
        sl = entry_price * (1 - SL_PCT)
    else:
        tp = entry_price * (1 - TP_PCT)
        sl = entry_price * (1 + SL_PCT)
    
    for _, candle in future.iterrows():
        if direction == "LONG":
            if candle['high'] >= tp:
                return "WIN", TP_PCT * 100, candle['timestamp']
            if candle['low'] <= sl:
                return "LOSS", -SL_PCT * 100, candle['timestamp']
        else:
            if candle['low'] <= tp:
                return "WIN", TP_PCT * 100, candle['timestamp']
            if candle['high'] >= sl:
                return "LOSS", -SL_PCT * 100, candle['timestamp']
    return "OPEN", 0.0, None

def calculate_trend(df_1h, target_time):
    """Calculate EMA20/50 trend at specific time"""
    # Get data up to target time
    mask = df_1h['timestamp'] <= target_time
    history = df_1h[mask].tail(100).copy() # Need enough for EMA
    
    if len(history) < 50:
        return "UNKNOWN"
        
    history['ema20'] = history['close'].ewm(span=20).mean()
    history['ema50'] = history['close'].ewm(span=50).mean()
    
    last = history.iloc[-1]
    if last['ema20'] > last['ema50']:
        return "BULLISH"
    else:
        return "BEARISH"

print("="*80)
print("🏗️ JAN 6 RECONSTRUCTION (SIMULATION MODE)")
print("="*80)

# Download data for Jan 6 (plus buffer for EMA/features)
start_buffer = datetime(2026, 1, 1, 0, 0, 0)
target_day_start = datetime(2026, 1, 6, 0, 0, 0)
target_day_end = datetime(2026, 1, 7, 0, 0, 0)
end_buffer = datetime(2026, 1, 8, 0, 0, 0) # For outcomes

print("Downloading historical data...")
df_5m = download_data(start_buffer, end_buffer, '5m')
df_15m = download_data(start_buffer, end_buffer, '15m')
df_1h = download_data(start_buffer, end_buffer, '1h')
df_1m = download_data(target_day_start, end_buffer, '1m')

if any(d is None for d in [df_5m, df_15m, df_1h, df_1m]):
    print("❌ Failed to download data")
    sys.exit(1)

print(f"  ✅ Data downloaded")

# Load model
print("Loading model...")
try:
    model = joblib.load('models/mtf_scalper_5m_v2_calibrated.pkl')
    print("  ✅ Model loaded")
except Exception as e:
    print(f"  ❌ Failed: {e}")
    sys.exit(1)

# Process Jan 6
print("\nProcessing Jan 6 candles...")
day_5m = df_5m[(df_5m['timestamp'] >= target_day_start) & (df_5m['timestamp'] < target_day_end)]
print(f"  Total 5m candles: {len(day_5m)}")

trades = []

for idx, row in day_5m.iterrows():
    timestamp = row['timestamp']
    
    # 1. Prepare features (Simplified for speed - full feature engine is heavy)
    try:
        # Get history
        hist_5m = df_5m[df_5m['timestamp'] <= timestamp].tail(500)
        hist_15m = df_15m[df_15m['timestamp'] <= timestamp].tail(500)
        hist_1h = df_1h[df_1h['timestamp'] <= timestamp].tail(500)
        
        if len(hist_5m) < 200: continue
        
        # Add indicators
        hist_5m_feat = add_all_indicators(hist_5m.copy())
        hist_15m_feat = add_all_indicators(hist_15m.copy())
        hist_1h_feat = add_all_indicators(hist_1h.copy())
        
        # Merge
        hist_5m_feat.set_index('timestamp', inplace=True)
        hist_15m_feat.set_index('timestamp', inplace=True)
        hist_1h_feat.set_index('timestamp', inplace=True)
        
        exclude = ['open', 'high', 'low', 'close', 'volume']
        
        # 15m merge
        ctx_15m = [c for c in hist_15m_feat.columns if c not in exclude]
        d15 = hist_15m_feat[ctx_15m].copy()
        d15.columns = [f"{c}_15m" for c in ctx_15m]
        d15 = d15.reindex(hist_5m_feat.index, method='ffill')
        
        # 1h merge
        ctx_1h = [c for c in hist_1h_feat.columns if c not in exclude]
        d1h = hist_1h_feat[ctx_1h].copy()
        d1h.columns = [f"{c}_1h" for c in ctx_1h]
        d1h = d1h.reindex(hist_5m_feat.index, method='ffill')
        
        full_df = pd.concat([hist_5m_feat, d15, d1h], axis=1)
        full_df.dropna(inplace=True)
        
        if len(full_df) == 0: continue
        
        latest = full_df.iloc[-1]
        feat_cols = [c for c in full_df.columns if c not in exclude]
        X = latest[feat_cols].values.reshape(1, -1)
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        
        # 2. Predict
        probas = model.predict_proba(X)[0]
        # Local model: Class 0=Hold, Class 1=Long. No Short.
        prob_long = float(probas[1])
        
        # 3. Check Signal (Lower threshold for logging)
        if prob_long >= 0.40:
            
            # 4. Check Trend
            trend = calculate_trend(df_1h, timestamp)
            
            # Trend Filter: Only Buy in Bullish
            if trend == "BULLISH":
                print(f"  POTENTIAL: {timestamp} LONG {prob_long:.1%} [Trend: {trend}]")
                
                # Check against Elastic Logic manually later
                if prob_long >= THRESHOLDS['MTF Scalper (5M)']['LONG']:
                    # 5. Simulate Outcome
                    outcome, pnl, exit_time = simulate_outcome(row['close'], "LONG", timestamp, df_1m)
                    
                    trade = {
                        'time': timestamp.strftime('%H:%M:%S'),
                        'direction': "LONG",
                        'confidence': prob_long,
                        'price': row['close'],
                        'trend': trend,
                        'outcome': outcome,
                        'pnl': pnl
                    }
                    trades.append(trade)
            else:
                # Filtered
                pass

    except Exception as e:
        continue

print(f"\n{'='*80}")
print("JAN 6 RESULTS")
print(f"{'='*80}")

if trades:
    wins = len([t for t in trades if t['outcome'] == 'WIN'])
    losses = len([t for t in trades if t['outcome'] == 'LOSS'])
    pnl = sum(t['pnl'] for t in trades)
    print(f"Trades: {len(trades)}")
    print(f"Wins: {wins} | Losses: {losses}")
    print(f"P&L: {pnl:+.2f}%")
else:
    print("No trades executed (at 65% threshold)")

# Check Trend for the day generally
print(f"\nOpening Trend (00:00): {calculate_trend(df_1h, target_day_start)}")
print(f"Closing Trend (23:59): {calculate_trend(df_1h, target_day_end)}")

EOF
