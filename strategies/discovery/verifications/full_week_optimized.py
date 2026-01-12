#!/usr/bin/env python3
"""
FULL WEEK OPTIMIZED BOT RECONSTRUCTION - Jan 1-8, 2026
Simulates what revision 00016 would have done with:
- Real ML models
- 65% thresholds
- Trend filter ACTIVE
- Market regime detection
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
from utils.trend_filter import get_market_regime, should_trade

# Configuration
THRESHOLDS = {
    'MTF Scalper (5M)': {'LONG': 0.6500, 'SHORT': 0.6891}
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
    future = df_1m[df_1m['timestamp'] > entry_time].head(2880)
    
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

print("="*80)
print("🚀 FULL WEEK OPTIMIZED BOT RECONSTRUCTION - Jan 1-8, 2026")
print("="*80)
print("\nConfiguration:")
print("  ✅ Thresholds: 65% (MTF Scalper)")
print("  ✅ Trend Filter: ACTIVE")
print("  ✅ Models: Real calibrated models")
print()

# Download data
start = datetime(2026, 1, 1, 0, 0, 0)
end = datetime(2026, 1, 9, 0, 0, 0)

print("Downloading historical data...")
df_5m = download_data(start, end, '5m')
df_15m = download_data(start, end, '15m')
df_1h = download_data(start, end, '1h')
df_1m = download_data(start, end, '1m')

if df_5m is None or df_15m is None or df_1h is None or df_1m is None:
    print("❌ Failed to download data")
    sys.exit(1)

print(f"  ✅ 5M: {len(df_5m)} candles")
print(f"  ✅ 15M: {len(df_15m)} candles")
print(f"  ✅ 1H: {len(df_1h)} candles")
print(f"  ✅ 1M: {len(df_1m)} candles")

# Load model
print("\nLoading MTF Scalper model...")
try:
    mtf_model = joblib.load('models/mtf_scalper_5m_v2_calibrated.pkl')
    print("  ✅ Model loaded")
except Exception as e:
    print(f"  ❌ Failed: {e}")
    sys.exit(1)

# Process day by day
all_trades = []

for day_offset in range(8):  # Jan 1-8
    day_date = start + timedelta(days=day_offset)
    day_str = day_date.strftime('%Y-%m-%d')
    day_start = datetime(day_date.year, day_date.month, day_date.day, 0, 0, 0)
    day_end = day_start + timedelta(days=1)
    
    print(f"\n{'='*80}")
    print(f"📅 {day_str}")
    print(f"{'='*80}")
    
    # Get day's 5M candles
    day_5m = df_5m[(df_5m['timestamp'] >= day_start) & (df_5m['timestamp'] < day_end)]
    
    if len(day_5m) == 0:
        print("  No data")
        continue
    
    day_trades = []
    
    # Process each 5M candle
    for idx, row in day_5m.iterrows():
        timestamp = row['timestamp']
        
        # Get historical data up to this point
        hist_5m = df_5m[df_5m['timestamp'] <= timestamp].tail(500)
        hist_15m = df_15m[df_15m['timestamp'] <= timestamp].tail(500)
        hist_1h = df_1h[df_1h['timestamp'] <= timestamp].tail(500)
        
        if len(hist_5m) < 200 or len(hist_15m) < 50 or len(hist_1h) < 50:
            continue
        
        try:
            # Add indicators
            hist_5m_feat = add_all_indicators(hist_5m.copy())
            hist_15m_feat = add_all_indicators(hist_15m.copy())
            hist_1h_feat = add_all_indicators(hist_1h.copy())
            
            hist_5m_feat.set_index('timestamp', inplace=True)
            hist_15m_feat.set_index('timestamp', inplace=True)
            hist_1h_feat.set_index('timestamp', inplace=True)
            
            # Merge timeframes
            exclude = ['open', 'high', 'low', 'close', 'volume']
            
            # 15M context
            ctx_15m = [c for c in hist_15m_feat.columns if c not in exclude]
            df_15m_renamed = hist_15m_feat[ctx_15m].copy()
            df_15m_renamed.columns = [f"{c}_15m" for c in ctx_15m]
            df_15m_resampled = df_15m_renamed.reindex(hist_5m_feat.index, method='ffill')
            hist_5m_feat = pd.concat([hist_5m_feat, df_15m_resampled], axis=1)
            
            # 1H context
            ctx_1h = [c for c in hist_1h_feat.columns if c not in exclude]
            df_1h_renamed = hist_1h_feat[ctx_1h].copy()
            df_1h_renamed.columns = [f"{c}_1h" for c in ctx_1h]
            df_1h_resampled = df_1h_renamed.reindex(hist_5m_feat.index, method='ffill')
            hist_5m_feat = pd.concat([hist_5m_feat, df_1h_resampled], axis=1)
            
            # Get latest
            hist_5m_feat.dropna(inplace=True)
            if len(hist_5m_feat) == 0:
                continue
            
            latest = hist_5m_feat.iloc[-1]
            
            # Prepare features
            feature_cols = [c for c in hist_5m_feat.columns if c not in exclude]
            X = latest[feature_cols].values.reshape(1, -1)
            X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
            
            # Predict
            probas = mtf_model.predict_proba(X)[0]
            prob_long = float(probas[1])
            prob_short = float(probas[2])
            
            # Check threshold
            direction = None
            confidence = 0.0
            
            if prob_short >= THRESHOLDS['MTF Scalper (5M)']['SHORT']:
                direction = "SHORT"
                confidence = prob_short
            elif prob_long >= THRESHOLDS['MTF Scalper (5M)']['LONG']:
                direction = "LONG"
                confidence = prob_long
            
            if direction:
                # Check trend filter
                regime = get_market_regime(hist_1h_feat[['close']])
                
                if should_trade(direction, regime):
                    # Simulate outcome
                    outcome, pnl, exit_time = simulate_outcome(
                        row['close'], direction, timestamp, df_1m
                    )
                    
                    trade = {
                        'date': day_str,
                        'entry_time': timestamp.isoformat(),
                        'model': 'MTF Scalper (5M)',
                        'direction': direction,
                        'confidence': confidence,
                        'entry_price': row['close'],
                        'regime': regime,
                        'outcome': outcome,
                        'pnl': pnl,
                        'exit_time': exit_time.isoformat() if exit_time else None
                    }
                    day_trades.append(trade)
                    all_trades.append(trade)
                    
        except Exception as e:
            continue
    
    # Day summary
    if day_trades:
        wins = len([t for t in day_trades if t['outcome'] == 'WIN'])
        losses = len([t for t in day_trades if t['outcome'] == 'LOSS'])
        pnl = sum(t['pnl'] for t in day_trades)
        print(f"  📊 {len(day_trades)} trades | {wins}W-{losses}L | {pnl:+.2f}% P&L")
    else:
        print(f"  No trades")

# Final summary
print(f"\n{'='*80}")
print("📈 WEEK SUMMARY")
print(f"{'='*80}")

if all_trades:
    wins = [t for t in all_trades if t['outcome'] == 'WIN']
    losses = [t for t in all_trades if t['outcome'] == 'LOSS']
    
    print(f"\nTotal Trades: {len(all_trades)}")
    print(f"  Wins: {len(wins)} ✅")
    print(f"  Losses: {len(losses)} ❌")
    if len(wins) + len(losses) > 0:
        print(f"  Win Rate: {len(wins)/(len(wins)+len(losses))*100:.1f}%")
    print(f"  Total P&L: {sum(t['pnl'] for t in all_trades):+.2f}%")
    
    # Save
    with open('FULL_WEEK_OPTIMIZED_TRADES.json', 'w') as f:
        json.dump(all_trades, f, indent=2, default=str)
    
    print(f"\n✅ Saved to FULL_WEEK_OPTIMIZED_TRADES.json")
else:
    print("\n❌ No trades")

print(f"\n{'='*80}")
