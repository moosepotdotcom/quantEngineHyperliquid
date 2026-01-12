#!/usr/bin/env python3
"""
Simulate outcomes for the missed signals during network outage
"""
import json
import requests
from datetime import datetime, timedelta

def fetch_price_data(start_time, end_time):
    """Fetch 5m candles from Hyperliquid"""
    url = "https://api.hyperliquid.xyz/info"
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": "BTC",
            "interval": "5m",
            "startTime": int(start_time.timestamp() * 1000),
            "endTime": int(end_time.timestamp() * 1000)
        }
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"Error: {e}")
    return []

def simulate_trade(entry_price, entry_time, direction='LONG', tp_pct=0.015, sl_pct=0.008):
    """Simulate TP/SL outcome"""
    # Calculate targets
    if direction == 'LONG':
        tp_price = entry_price * (1 + tp_pct)
        sl_price = entry_price * (1 - sl_pct)
    else:
        tp_price = entry_price * (1 - tp_pct)
        sl_price = entry_price * (1 + sl_pct)
    
    # Fetch price data
    candles = fetch_price_data(entry_time, entry_time + timedelta(hours=2))
    
    if not candles:
        return {'outcome': 'UNKNOWN', 'reason': 'No price data'}
    
    # Check each candle
    for candle in candles:
        candle_time = datetime.fromtimestamp(candle['t'] / 1000)
        
        if candle_time <= entry_time:
            continue
        
        high = float(candle['h'])
        low = float(candle['l'])
        
        # Check TP/SL
        if direction == 'LONG':
            if high >= tp_price:
                duration = (candle_time - entry_time).total_seconds() / 60
                return {
                    'outcome': 'WIN',
                    'exit_price': tp_price,
                    'duration_mins': int(duration),
                    'pnl_pct': tp_pct
                }
            elif low <= sl_price:
                duration = (candle_time - entry_time).total_seconds() / 60
                return {
                    'outcome': 'LOSS',
                    'exit_price': sl_price,
                    'duration_mins': int(duration),
                    'pnl_pct': -sl_pct
                }
        else:  # SHORT
            if low <= tp_price:
                duration = (candle_time - entry_time).total_seconds() / 60
                return {
                    'outcome': 'WIN',
                    'exit_price': tp_price,
                    'duration_mins': int(duration),
                    'pnl_pct': tp_pct
                }
            elif high >= sl_price:
                duration = (candle_time - entry_time).total_seconds() / 60
                return {
                    'outcome': 'LOSS',
                    'exit_price': sl_price,
                    'duration_mins': int(duration),
                    'pnl_pct': -sl_pct
                }
    
    return {'outcome': 'OPEN', 'reason': 'Still in trade or TP not hit yet'}

# Load the high-confidence signals
signals = []
with open('logs/trades/predictions_20260108.jsonl', 'r') as f:
    for line in f:
        try:
            pred = json.loads(line.strip())
            if pred.get('model') == 'MTF Scalper (5M)' and pred.get('confidence', 0) >= 0.5987:
                signals.append(pred)
        except: pass

# Sort by confidence
signals.sort(key=lambda x: x.get('confidence', 0), reverse=True)

print("="*70)
print("🔍 SIMULATING MISSED TRADES (Network Outage Period)")
print("="*70)
print(f"\nFound {len(signals)} MTF Scalper signals that exceeded 59.87% threshold\n")

# Simulate top 5
results = []
for i, signal in enumerate(signals[:5], 1):
    ts_str = signal.get('timestamp', '')
    entry_time = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
    entry_price = signal.get('market_data', {}).get('close', 0)
    confidence = signal.get('confidence', 0)
    
    print(f"\n[{i}] {ts_str[:19]} | Confidence: {confidence:.2%} | Entry: ${entry_price:,.0f}")
    
    # Simulate
    result = simulate_trade(entry_price, entry_time, direction='LONG')
    results.append(result)
    
    if result['outcome'] == 'WIN':
        print(f"    ✅ WIN - TP hit @ ${result['exit_price']:,.0f} in {result['duration_mins']}m")
    elif result['outcome'] == 'LOSS':
        print(f"    ❌ LOSS - SL hit @ ${result['exit_price']:,.0f} in {result['duration_mins']}m")
    else:
        print(f"    ⚪ {result['outcome']} - {result.get('reason', 'Unknown')}")

# Summary
wins = len([r for r in results if r['outcome'] == 'WIN'])
losses = len([r for r in results if r['outcome'] == 'LOSS'])
total_pnl = sum(r.get('pnl_pct', 0) for r in results)

print("\n" + "="*70)
print("📊 SIMULATION SUMMARY")
print("="*70)
print(f"Total Simulated: {len(results)}")
print(f"Wins: {wins}")
print(f"Losses: {losses}")
print(f"Win Rate: {(wins/len(results)*100) if results else 0:.1f}%")
print(f"Total P&L: {total_pnl:.2%}")
print("="*70)
