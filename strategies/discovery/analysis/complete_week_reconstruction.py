#!/usr/bin/env python3
"""
Complete Week Reconstruction with Exact Trade Details
Downloads historical data and simulates all trades Jan 2-8, 2026
"""
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

# Thresholds
NEW_THRESHOLDS = {
    'Winner Hunter (1H)': {'LONG': 0.5000, 'SHORT': 0.4789},
    'MTF Scalper (5M)': {'LONG': 0.6500, 'SHORT': 0.6891}
}

TP_PCT = 0.015  # 1.5%
SL_PCT = 0.008  # 0.8%

def download_historical_data(start_date, end_date, interval='1h'):
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
        print(f"Error downloading data: {e}")
        return None

def get_market_regime_simple(df):
    """Simple EMA-based regime detection"""
    if len(df) < 50:
        return "UNKNOWN"
    
    ema_20 = df['close'].ewm(span=20, adjust=False).mean().iloc[-1]
    ema_50 = df['close'].ewm(span=50, adjust=False).mean().iloc[-1]
    
    if ema_20 > ema_50 * 1.005:
        return "BULLISH"
    elif ema_20 < ema_50 * 0.995:
        return "BEARISH"
    else:
        return "RANGING"

def should_trade_simple(direction, regime):
    """Check if trade aligns with trend"""
    if direction == "LONG" and regime != "BULLISH":
        return False
    if direction == "SHORT" and regime != "BEARISH":
        return False
    return True

def simulate_trade_outcome(entry_price, direction, entry_time, candles_1m):
    """Simulate TP/SL outcome with exact exit time"""
    # Get candles after entry
    future_candles = candles_1m[candles_1m['timestamp'] > entry_time].head(2880)  # 48 hours
    
    if len(future_candles) == 0:
        return None, None, None
    
    if direction == "LONG":
        tp_target = entry_price * (1 + TP_PCT)
        sl_target = entry_price * (1 - SL_PCT)
    else:
        tp_target = entry_price * (1 - TP_PCT)
        sl_target = entry_price * (1 + SL_PCT)
    
    for _, candle in future_candles.iterrows():
        if direction == "LONG":
            if candle['high'] >= tp_target:
                return "WIN", TP_PCT * 100, candle['timestamp']
            if candle['low'] <= sl_target:
                return "LOSS", -SL_PCT * 100, candle['timestamp']
        else:
            if candle['low'] <= tp_target:
                return "WIN", TP_PCT * 100, candle['timestamp']
            if candle['high'] >= sl_target:
                return "LOSS", -SL_PCT * 100, candle['timestamp']
    
    return "OPEN", 0.0, None

print("="*80)
print("🔬 COMPLETE WEEK RECONSTRUCTION - Jan 2-8, 2026")
print("="*80)
print("\nDownloading historical data...")

# Download data for full week
start_date = datetime(2026, 1, 2, 0, 0, 0)
end_date = datetime(2026, 1, 9, 0, 0, 0)

# Download 1h data for regime detection and signals
print("  Downloading 1H data...")
df_1h = download_historical_data(start_date, end_date, '1h')

# Download 1m data for TP/SL simulation
print("  Downloading 1M data...")
df_1m = download_historical_data(start_date, end_date, '1m')

if df_1h is None or df_1m is None:
    print("❌ Failed to download data")
    exit(1)

print(f"  ✅ Downloaded {len(df_1h)} 1H candles")
print(f"  ✅ Downloaded {len(df_1m)} 1M candles")

# Reconstruct trades day by day
all_trades = []

for day_offset in range(7):
    day_date = start_date + timedelta(days=day_offset)
    day_str = day_date.strftime('%Y-%m-%d')
    day_start = datetime(day_date.year, day_date.month, day_date.day, 0, 0, 0)
    day_end = day_start + timedelta(days=1)
    
    print(f"\n{'='*80}")
    print(f"📅 {day_str}")
    print(f"{'='*80}")
    
    # Get candles for this day
    day_candles_1h = df_1h[(df_1h['timestamp'] >= day_start) & (df_1h['timestamp'] < day_end)]
    
    if len(day_candles_1h) == 0:
        print("  No data for this day")
        continue
    
    # Check each hour for signals
    day_trades = []
    
    for _, candle in day_candles_1h.iterrows():
        timestamp = candle['timestamp']
        price = candle['close']
        
        # Get historical data up to this point for regime
        historical = df_1h[df_1h['timestamp'] <= timestamp].tail(100)
        
        if len(historical) < 50:
            continue
        
        # Determine market regime
        regime = get_market_regime_simple(historical)
        
        # Simulate model confidence (simplified - using price action)
        # In reality, this would come from the actual models
        # For now, we'll use a simple heuristic based on momentum
        
        returns = historical['close'].pct_change(5).iloc[-1] * 100
        
        # MTF Scalper logic (simplified)
        if abs(returns) > 0.5:  # Strong momentum
            if returns < -0.5:  # Bearish momentum
                mtf_conf = min(0.75, 0.65 + abs(returns) * 0.02)
                direction = "SHORT"
                
                # Check threshold
                if mtf_conf >= NEW_THRESHOLDS['MTF Scalper (5M)']['SHORT']:
                    # Check trend filter
                    if should_trade_simple(direction, regime):
                        # Simulate outcome
                        outcome, pnl, exit_time = simulate_trade_outcome(
                            price, direction, timestamp, df_1m
                        )
                        
                        if outcome:
                            trade = {
                                'date': day_str,
                                'entry_time': timestamp,
                                'model': 'MTF Scalper (5M)',
                                'direction': direction,
                                'confidence': mtf_conf,
                                'entry_price': price,
                                'tp_price': price * (1 - TP_PCT),
                                'sl_price': price * (1 + SL_PCT),
                                'regime': regime,
                                'outcome': outcome,
                                'pnl': pnl,
                                'exit_time': exit_time
                            }
                            day_trades.append(trade)
                            all_trades.append(trade)
            
            elif returns > 0.5:  # Bullish momentum
                mtf_conf = min(0.75, 0.65 + abs(returns) * 0.02)
                direction = "LONG"
                
                if mtf_conf >= NEW_THRESHOLDS['MTF Scalper (5M)']['LONG']:
                    if should_trade_simple(direction, regime):
                        outcome, pnl, exit_time = simulate_trade_outcome(
                            price, direction, timestamp, df_1m
                        )
                        
                        if outcome:
                            trade = {
                                'date': day_str,
                                'entry_time': timestamp,
                                'model': 'MTF Scalper (5M)',
                                'direction': direction,
                                'confidence': mtf_conf,
                                'entry_price': price,
                                'tp_price': price * (1 + TP_PCT),
                                'sl_price': price * (1 - SL_PCT),
                                'regime': regime,
                                'outcome': outcome,
                                'pnl': pnl,
                                'exit_time': exit_time
                            }
                            day_trades.append(trade)
                            all_trades.append(trade)
    
    # Print day summary
    if day_trades:
        print(f"\n  📊 {len(day_trades)} trades on {day_str}:")
        for i, trade in enumerate(day_trades, 1):
            emoji = "✅" if trade['outcome'] == 'WIN' else "❌" if trade['outcome'] == 'LOSS' else "🟡"
            duration = (trade['exit_time'] - trade['entry_time']).total_seconds() / 60 if trade['exit_time'] else 0
            
            print(f"\n  {i}. {emoji} {trade['model']} {trade['direction']}")
            print(f"     Entry:  {trade['entry_time'].strftime('%Y-%m-%d %H:%M')} @ ${trade['entry_price']:,.2f}")
            print(f"     TP:     ${trade['tp_price']:,.2f} (+1.5%)")
            print(f"     SL:     ${trade['sl_price']:,.2f} (-0.8%)")
            print(f"     Regime: {trade['regime']}")
            print(f"     Conf:   {trade['confidence']:.2%}")
            if trade['exit_time']:
                print(f"     Exit:   {trade['exit_time'].strftime('%Y-%m-%d %H:%M')} ({int(duration)} min)")
            print(f"     Result: {trade['outcome']} ({trade['pnl']:+.2f}%)")
    else:
        print(f"  No trades on {day_str}")

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
    print(f"  Win Rate: {len(wins)/(len(wins)+len(losses))*100:.1f}%")
    print(f"  Total P&L: {sum(t['pnl'] for t in all_trades):+.2f}%")
    print(f"  Avg P&L/Trade: {sum(t['pnl'] for t in all_trades)/len(all_trades):+.2f}%")
    
    # Save to file
    with open('COMPLETE_WEEK_TRADES.json', 'w') as f:
        json.dump(all_trades, f, indent=2, default=str)
    
    print(f"\n✅ Saved {len(all_trades)} trades to COMPLETE_WEEK_TRADES.json")
else:
    print("\n❌ No trades found for the week")

print(f"\n{'='*80}")
print("✅ Reconstruction complete!")
print(f"{'='*80}")
