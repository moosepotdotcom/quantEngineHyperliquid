#!/usr/bin/env python3
"""
CORRECTED Week Reconstruction - Uses actual prediction logs + simulation
"""
import json
import requests
import pandas as pd
from datetime import datetime, timedelta

# Thresholds
NEW_THRESHOLDS = {
    'Winner Hunter (1H)': {'LONG': 0.5000, 'SHORT': 0.4789},
    'MTF Scalper (5M)': {'LONG': 0.6500, 'SHORT': 0.6891}
}

TP_PCT = 0.015
SL_PCT = 0.008

def get_historical_candles(start_time, end_time):
    """Get 1-minute BTC candles"""
    url = "https://api.hyperliquid.xyz/info"
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": "BTC",
            "interval": "1m",
            "startTime": int(start_time.timestamp() * 1000),
            "endTime": int(end_time.timestamp() * 1000)
        }
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        if data:
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
            df['close'] = df['c'].astype(float)
            df['high'] = df['h'].astype(float)
            df['low'] = df['l'].astype(float)
            return df
        return None
    except:
        return None

def simulate_outcome(entry_price, direction, entry_time):
    """Simulate TP/SL outcome"""
    end_time = entry_time + timedelta(hours=48)
    candles = get_historical_candles(entry_time, end_time)
    
    if candles is None or len(candles) == 0:
        return "UNCONFIRMED", 0.0, None
    
    if direction == "LONG":
        tp_target = entry_price * (1 + TP_PCT)
        sl_target = entry_price * (1 - SL_PCT)
    else:
        tp_target = entry_price * (1 - TP_PCT)
        sl_target = entry_price * (1 + SL_PCT)
    
    for _, candle in candles.iterrows():
        high = candle['high']
        low = candle['low']
        
        if direction == "LONG":
            if high >= tp_target:
                return "WIN", TP_PCT * 100, candle['timestamp']
            if low <= sl_target:
                return "LOSS", -SL_PCT * 100, candle['timestamp']
        else:
            if low <= tp_target:
                return "WIN", TP_PCT * 100, candle['timestamp']
            if high >= sl_target:
                return "LOSS", -SL_PCT * 100, candle['timestamp']
    
    return "OPEN", 0.0, None

print("="*80)
print("🔧 CORRECTED WEEK RECONSTRUCTION - Using Actual Prediction Logs")
print("="*80)

all_trades = []

# Process each day
for day_offset in range(7):
    day_date = datetime(2026, 1, 2) + timedelta(days=day_offset)
    day_str = day_date.strftime('%Y-%m-%d')
    date_file = day_date.strftime('%Y%m%d')
    
    print(f"\n{'='*80}")
    print(f"📅 {day_str}")
    print(f"{'='*80}")
    
    # Try to load actual prediction logs
    try:
        with open(f'logs/trades/predictions_{date_file}.jsonl', 'r') as f:
            predictions = [json.loads(line) for line in f]
        
        print(f"  ✅ Loaded {len(predictions)} actual predictions")
        
        # Process predictions with new thresholds
        day_trades = []
        for pred in predictions:
            model = pred.get('model', '')
            conf = pred.get('confidence', 0)
            price = pred.get('market_data', {}).get('close', 0)
            timestamp = pred.get('timestamp', '')
            
            if not price or price == 0 or model not in NEW_THRESHOLDS:
                continue
            
            # Determine direction
            if conf >= NEW_THRESHOLDS[model]['SHORT']:
                direction = 'SHORT'
            elif conf >= NEW_THRESHOLDS[model]['LONG']:
                direction = 'LONG'
            else:
                continue
            
            # Simulate outcome
            entry_time = datetime.fromisoformat(timestamp)
            outcome, pnl, exit_time = simulate_outcome(price, direction, entry_time)
            
            if outcome != "UNCONFIRMED":
                trade = {
                    'date': day_str,
                    'entry_time': timestamp,
                    'model': model,
                    'direction': direction,
                    'confidence': conf,
                    'entry_price': price,
                    'tp_price': price * (1 + TP_PCT) if direction == "LONG" else price * (1 - TP_PCT),
                    'sl_price': price * (1 - SL_PCT) if direction == "LONG" else price * (1 + SL_PCT),
                    'outcome': outcome,
                    'pnl': pnl,
                    'exit_time': exit_time.isoformat() if exit_time else None
                }
                day_trades.append(trade)
                all_trades.append(trade)
        
        if day_trades:
            print(f"\n  📊 {len(day_trades)} trades from actual predictions:")
            for i, trade in enumerate(day_trades, 1):
                emoji = "✅" if trade['outcome'] == 'WIN' else "❌" if trade['outcome'] == 'LOSS' else "🟡"
                print(f"  {i}. {emoji} {trade['model']} {trade['direction']} @ ${trade['entry_price']:,.2f}")
                print(f"     {trade['outcome']} ({trade['pnl']:+.2f}%)")
        else:
            print(f"  No trades passed thresholds on {day_str}")
            
    except FileNotFoundError:
        print(f"  No prediction log for {day_str}")

# Summary
print(f"\n{'='*80}")
print("📈 CORRECTED WEEK SUMMARY")
print(f"{'='*80}")

if all_trades:
    wins = [t for t in all_trades if t['outcome'] == 'WIN']
    losses = [t for t in all_trades if t['outcome'] == 'LOSS']
    
    print(f"\nTotal Trades: {len(all_trades)}")
    print(f"  Wins: {len(wins)} ✅")
    print(f"  Losses: {len(losses)} ❌")
    print(f"  Win Rate: {len(wins)/(len(wins)+len(losses))*100:.1f}%")
    print(f"  Total P&L: {sum(t['pnl'] for t in all_trades):+.2f}%")
    
    # Save
    with open('CORRECTED_WEEK_TRADES.json', 'w') as f:
        json.dump(all_trades, f, indent=2, default=str)
    
    print(f"\n✅ Saved to CORRECTED_WEEK_TRADES.json")
else:
    print("\n❌ No trades found")

print(f"\n{'='*80}")
