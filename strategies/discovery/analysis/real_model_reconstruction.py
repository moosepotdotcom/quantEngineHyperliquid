#!/usr/bin/env python3
"""
REAL MODEL RECONSTRUCTION - Jan 2-8, 2026
Downloads historical data and runs ACTUAL ML models to generate predictions
"""
import sys
import os
import pandas as pd
import numpy as np
import requests
import joblib
from datetime import datetime, timedelta
import json

# Add paths
sys.path.insert(0, os.path.dirname(__file__))

from utils.feature_engineer import add_all_indicators
from utils.trend_filter import get_market_regime, should_trade

# Configuration
NEW_THRESHOLDS = {
    'Winner Hunter (1H)': {'LONG': 0.5000, 'SHORT': 0.4789},
    'MTF Scalper (5M)': {'LONG': 0.6500, 'SHORT': 0.6891}
}

TP_PCT = 0.015
SL_PCT = 0.008

def download_data(start_date, end_date, interval='1h'):
    """Download BTC data from Hyperliquid"""
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
    
    print(f"  Downloading {interval} data from {start_date.date()} to {end_date.date()}...")
    
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
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            print(f"  ✅ Downloaded {len(df)} {interval} candles")
            return df
        return None
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None

def simulate_outcome(entry_price, direction, entry_time, df_1m):
    """Simulate TP/SL with exact exit time"""
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
print("🔬 REAL MODEL RECONSTRUCTION - Jan 2-8, 2026")
print("="*80)
print("\nStep 1: Downloading historical data...")

# Download data
start = datetime(2026, 1, 2, 0, 0, 0)
end = datetime(2026, 1, 9, 0, 0, 0)

df_1h = download_data(start, end, '1h')
df_5m = download_data(start, end, '5m')
df_15m = download_data(start, end, '15m')
df_1m = download_data(start, end, '1m')

if df_1h is None or df_5m is None or df_15m is None or df_1m is None:
    print("\n❌ Failed to download data")
    sys.exit(1)

print("\n✅ Data downloaded successfully")
print(f"   1H: {len(df_1h)} candles")
print(f"   5M: {len(df_5m)} candles")
print(f"   15M: {len(df_15m)} candles")
print(f"   1M: {len(df_1m)} candles")

# Load models
print("\nStep 2: Loading ML models...")

try:
    wh_model = joblib.load('models/winner_hunter_1h_v2_calibrated.pkl')
    print("  ✅ Loaded Winner Hunter (1H) model")
except Exception as e:
    print(f"  ❌ Failed to load Winner Hunter: {e}")
    wh_model = None

try:
    mtf_model = joblib.load('models/mtf_scalper_5m_v2_calibrated.pkl')
    print("  ✅ Loaded MTF Scalper (5M) model")
except Exception as e:
    print(f"  ❌ Failed to load MTF Scalper: {e}")
    mtf_model = None

if wh_model is None and mtf_model is None:
    print("\n❌ No models loaded, cannot proceed")
    sys.exit(1)

# Generate predictions day by day
print("\nStep 3: Generating predictions with real models...")

all_trades = []

for day_offset in range(7):
    day_date = start + timedelta(days=day_offset)
    day_str = day_date.strftime('%Y-%m-%d')
    day_start = datetime(day_date.year, day_date.month, day_date.day, 0, 0, 0)
    day_end = day_start + timedelta(days=1)
    
    print(f"\n{'='*80}")
    print(f"📅 {day_str}")
    print(f"{'='*80}")
    
    day_trades = []
    
    # Process 1H data for Winner Hunter
    if wh_model:
        day_1h = df_1h[(df_1h['timestamp'] >= day_start) & (df_1h['timestamp'] < day_end)]
        
        for idx, row in day_1h.iterrows():
            timestamp = row['timestamp']
            
            # Get historical data up to this point
            hist_1h = df_1h[df_1h['timestamp'] <= timestamp].tail(500)
            
            if len(hist_1h) < 200:
                continue
            
            # Add indicators
            try:
                hist_1h_feat = add_all_indicators(hist_1h.copy())
                hist_1h_feat.set_index('timestamp', inplace=True)
                
                # Get latest features
                latest = hist_1h_feat.iloc[-1:]
                
                # Get feature columns (exclude OHLCV)
                feature_cols = [c for c in latest.columns if c not in ['open', 'high', 'low', 'close', 'volume']]
                X = latest[feature_cols]
                
                # Predict
                prob = wh_model.predict_proba(X)[0][1]
                
                # Check threshold
                direction = None
                if prob >= NEW_THRESHOLDS['Winner Hunter (1H)']['SHORT']:
                    direction = "SHORT"
                elif prob >= NEW_THRESHOLDS['Winner Hunter (1H)']['LONG']:
                    direction = "LONG"
                
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
                            'model': 'Winner Hunter (1H)',
                            'direction': direction,
                            'confidence': prob,
                            'entry_price': row['close'],
                            'tp_price': row['close'] * (1 + TP_PCT) if direction == "LONG" else row['close'] * (1 - TP_PCT),
                            'sl_price': row['close'] * (1 - SL_PCT) if direction == "LONG" else row['close'] * (1 + SL_PCT),
                            'regime': regime,
                            'outcome': outcome,
                            'pnl': pnl,
                            'exit_time': exit_time.isoformat() if exit_time else None
                        }
                        day_trades.append(trade)
                        all_trades.append(trade)
                        
            except Exception as e:
                continue
    
    # Process 5M data for MTF Scalper
    if mtf_model:
        day_5m = df_5m[(df_5m['timestamp'] >= day_start) & (df_5m['timestamp'] < day_end)]
        
        for idx, row in day_5m.iterrows():
            timestamp = row['timestamp']
            
            # Get historical data
            hist_5m = df_5m[df_5m['timestamp'] <= timestamp].tail(500)
            hist_15m = df_15m[df_15m['timestamp'] <= timestamp].tail(500)
            hist_1h = df_1h[df_1h['timestamp'] <= timestamp].tail(500)
            
            if len(hist_5m) < 200 or len(hist_15m) < 50 or len(hist_1h) < 50:
                continue
            
            try:
                # Add indicators to all timeframes
                hist_5m_feat = add_all_indicators(hist_5m.copy())
                hist_15m_feat = add_all_indicators(hist_15m.copy())
                hist_1h_feat = add_all_indicators(hist_1h.copy())
                
                hist_5m_feat.set_index('timestamp', inplace=True)
                hist_15m_feat.set_index('timestamp', inplace=True)
                hist_1h_feat.set_index('timestamp', inplace=True)
                
                # Merge 15m context
                exclude = ['open', 'high', 'low', 'close', 'volume']
                ctx_15m = [c for c in hist_15m_feat.columns if c not in exclude]
                df_15m_renamed = hist_15m_feat[ctx_15m].copy()
                df_15m_renamed.columns = [f"{c}_15m" for c in ctx_15m]
                df_15m_resampled = df_15m_renamed.reindex(hist_5m_feat.index, method='ffill')
                hist_5m_feat = pd.concat([hist_5m_feat, df_15m_resampled], axis=1)
                
                # Merge 1h context
                ctx_1h = [c for c in hist_1h_feat.columns if c not in exclude]
                df_1h_renamed = hist_1h_feat[ctx_1h].copy()
                df_1h_renamed.columns = [f"{c}_1h" for c in ctx_1h]
                df_1h_resampled = df_1h_renamed.reindex(hist_5m_feat.index, method='ffill')
                hist_5m_feat = pd.concat([hist_5m_feat, df_1h_resampled], axis=1)
                
                # Get latest features
                latest = hist_5m_feat.iloc[-1:]
                
                # Get feature columns
                feature_cols = [c for c in latest.columns if c not in exclude]
                X = latest[feature_cols]
                
                # Predict
                prob = mtf_model.predict_proba(X)[0][1]
                
                # Check threshold
                direction = None
                if prob >= NEW_THRESHOLDS['MTF Scalper (5M)']['SHORT']:
                    direction = "SHORT"
                elif prob >= NEW_THRESHOLDS['MTF Scalper (5M)']['LONG']:
                    direction = "LONG"
                
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
                            'confidence': prob,
                            'entry_price': row['close'],
                            'tp_price': row['close'] * (1 + TP_PCT) if direction == "LONG" else row['close'] * (1 - TP_PCT),
                            'sl_price': row['close'] * (1 - SL_PCT) if direction == "LONG" else row['close'] * (1 + SL_PCT),
                            'regime': regime,
                            'outcome': outcome,
                            'pnl': pnl,
                            'exit_time': exit_time.isoformat() if exit_time else None
                        }
                        day_trades.append(trade)
                        all_trades.append(trade)
                        
            except Exception as e:
                continue
    
    # Print day summary
    if day_trades:
        print(f"\n  📊 {len(day_trades)} trades generated:")
        for i, trade in enumerate(day_trades[:5], 1):
            emoji = "✅" if trade['outcome'] == 'WIN' else "❌" if trade['outcome'] == 'LOSS' else "🟡"
            print(f"  {i}. {emoji} {trade['model']} {trade['direction']} @ ${trade['entry_price']:,.2f}")
            print(f"     Conf: {trade['confidence']:.2%} | {trade['outcome']} ({trade['pnl']:+.2f}%)")
        if len(day_trades) > 5:
            print(f"  ... and {len(day_trades) - 5} more")
    else:
        print(f"  No trades on {day_str}")

# Final summary
print(f"\n{'='*80}")
print("📈 REAL MODEL RECONSTRUCTION SUMMARY")
print(f"{'='*80}")

if all_trades:
    wins = [t for t in all_trades if t['outcome'] == 'WIN']
    losses = [t for t in all_trades if t['outcome'] == 'LOSS']
    opens = [t for t in all_trades if t['outcome'] == 'OPEN']
    
    print(f"\nTotal Trades: {len(all_trades)}")
    print(f"  Wins: {len(wins)} ✅")
    print(f"  Losses: {len(losses)} ❌")
    print(f"  Open: {len(opens)} 🟡")
    if len(wins) + len(losses) > 0:
        print(f"  Win Rate: {len(wins)/(len(wins)+len(losses))*100:.1f}%")
    print(f"  Total P&L: {sum(t['pnl'] for t in all_trades):+.2f}%")
    
    # Save
    with open('REAL_MODEL_TRADES.json', 'w') as f:
        json.dump(all_trades, f, indent=2, default=str)
    
    print(f"\n✅ Saved {len(all_trades)} trades to REAL_MODEL_TRADES.json")
else:
    print("\n❌ No trades generated")

print(f"\n{'='*80}")
print("✅ Real model reconstruction complete!")
print(f"{'='*80}")
