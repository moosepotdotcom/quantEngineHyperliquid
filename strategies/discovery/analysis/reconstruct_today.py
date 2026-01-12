#!/usr/bin/env python3
"""
Reconstruct Today's Trade Opportunities
Analyzes prediction logs to see if any signals crossed thresholds
"""
import json
import requests
from datetime import datetime, timedelta

# Thresholds
ELASTIC_THRESHOLDS = {
    'Winner Hunter (1H)': {'LONG': 0.3412, 'SHORT': 0.4500},
    'MTF Scalper (5M)': {'LONG': 0.4500, 'SHORT': 0.6017}
}

SURGICAL_THRESHOLDS = {
    'Winner Hunter (1H)': {'LONG': 0.3412, 'SHORT': 0.4789},
    'MTF Scalper (5M)': {'LONG': 0.5987, 'SHORT': 0.6891}
}

# TP/SL parameters
TP_PCT = 0.015  # 1.5%
SL_PCT = 0.008  # 0.8%

def get_historical_candles(start_time, end_time):
    """Get 1-minute BTC candles for outcome simulation"""
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
        return resp.json()
    except:
        return []

def simulate_outcome(entry_price, direction, entry_time):
    """Simulate if TP or SL would have been hit"""
    # Get candles for next 48 hours
    end_time = entry_time + timedelta(hours=48)
    candles = get_historical_candles(entry_time, end_time)
    
    if not candles:
        return "UNCONFIRMED", 0.0, None
    
    if direction == "LONG":
        tp_target = entry_price * (1 + TP_PCT)
        sl_target = entry_price * (1 - SL_PCT)
    else:
        tp_target = entry_price * (1 - TP_PCT)
        sl_target = entry_price * (1 + SL_PCT)
    
    for candle in candles:
        high = float(candle['h'])
        low = float(candle['l'])
        
        if direction == "LONG":
            if high >= tp_target:
                return "WIN", TP_PCT * 100, candle['t']
            if low <= sl_target:
                return "LOSS", -SL_PCT * 100, candle['t']
        else:
            if low <= tp_target:
                return "WIN", TP_PCT * 100, candle['t']
            if high >= sl_target:
                return "LOSS", -SL_PCT * 100, candle['t']
    
    # Calculate current P&L if still open
    current_price = float(candles[-1]['c'])
    if direction == "LONG":
        pnl = (current_price - entry_price) / entry_price * 100
    else:
        pnl = (entry_price - current_price) / entry_price * 100
    
    return "OPEN", pnl, None

# Load today's predictions
print("="*70)
print("📊 TODAY'S TRADE RECONSTRUCTION - January 8, 2026")
print("="*70)

try:
    with open('logs/trades/predictions_20260108.jsonl', 'r') as f:
        predictions = [json.loads(line) for line in f]
except:
    print("❌ No prediction log found for today")
    exit(1)

print(f"\nTotal predictions analyzed: {len(predictions)}")

# Find signals that crossed thresholds
elastic_signals = []
surgical_signals = []

for pred in predictions:
    model = pred.get('model', '')
    conf = pred.get('confidence', 0)
    price = pred.get('market_data', {}).get('close', 0)
    timestamp = pred.get('timestamp', '')
    
    if not price or price == 0:
        continue
    
    # Check ELASTIC thresholds
    if model in ELASTIC_THRESHOLDS:
        if conf >= ELASTIC_THRESHOLDS[model]['SHORT']:
            elastic_signals.append({
                'model': model,
                'direction': 'SHORT',
                'confidence': conf,
                'entry_price': price,
                'timestamp': timestamp
            })
        elif conf >= ELASTIC_THRESHOLDS[model]['LONG'] and conf < ELASTIC_THRESHOLDS[model]['SHORT']:
            elastic_signals.append({
                'model': model,
                'direction': 'LONG',
                'confidence': conf,
                'entry_price': price,
                'timestamp': timestamp
            })
    
    # Check SURGICAL thresholds
    if model in SURGICAL_THRESHOLDS:
        if conf >= SURGICAL_THRESHOLDS[model]['SHORT']:
            surgical_signals.append({
                'model': model,
                'direction': 'SHORT',
                'confidence': conf,
                'entry_price': price,
                'timestamp': timestamp
            })
        elif conf >= SURGICAL_THRESHOLDS[model]['LONG'] and conf < SURGICAL_THRESHOLDS[model]['SHORT']:
            surgical_signals.append({
                'model': model,
                'direction': 'LONG',
                'confidence': conf,
                'entry_price': price,
                'timestamp': timestamp
            })

print(f"\n🧠 ELASTIC Mode Signals: {len(elastic_signals)}")
print(f"🎯 SURGICAL Mode Signals: {len(surgical_signals)}")

# Simulate ELASTIC signals
if elastic_signals:
    print(f"\n{'='*70}")
    print("🧠 ELASTIC MODE TRADES (Current Bot Mode)")
    print(f"{'='*70}")
    
    wins = 0
    losses = 0
    opens = 0
    total_pnl = 0
    
    for i, sig in enumerate(elastic_signals[:10], 1):  # Show first 10
        entry_time = datetime.fromisoformat(sig['timestamp'])
        outcome, pnl, exit_time = simulate_outcome(sig['entry_price'], sig['direction'], entry_time)
        
        if outcome == "WIN":
            wins += 1
            emoji = "✅"
        elif outcome == "LOSS":
            losses += 1
            emoji = "❌"
        else:
            opens += 1
            emoji = "🟡"
        
        total_pnl += pnl
        
        print(f"\n{i}. {emoji} {sig['model']} {sig['direction']}")
        print(f"   Time: {sig['timestamp'][:19]}")
        print(f"   Confidence: {sig['confidence']:.2%}")
        print(f"   Entry: ${sig['entry_price']:,.2f}")
        print(f"   Outcome: {outcome} ({pnl:+.2f}%)")
    
    if len(elastic_signals) > 10:
        print(f"\n... and {len(elastic_signals) - 10} more signals")
    
    print(f"\n{'='*70}")
    print(f"ELASTIC SUMMARY:")
    print(f"  Wins: {wins} | Losses: {losses} | Open: {opens}")
    print(f"  Total P&L: {total_pnl:+.2f}%")
    if wins + losses > 0:
        print(f"  Win Rate: {wins/(wins+losses)*100:.1f}%")
    print(f"{'='*70}")
else:
    print("\n❌ No ELASTIC signals crossed thresholds today")

# Simulate SURGICAL signals
if surgical_signals:
    print(f"\n{'='*70}")
    print("🎯 SURGICAL MODE TRADES (Conservative Thresholds)")
    print(f"{'='*70}")
    
    wins = 0
    losses = 0
    opens = 0
    total_pnl = 0
    
    for i, sig in enumerate(surgical_signals[:10], 1):
        entry_time = datetime.fromisoformat(sig['timestamp'])
        outcome, pnl, exit_time = simulate_outcome(sig['entry_price'], sig['direction'], entry_time)
        
        if outcome == "WIN":
            wins += 1
            emoji = "✅"
        elif outcome == "LOSS":
            losses += 1
            emoji = "❌"
        else:
            opens += 1
            emoji = "🟡"
        
        total_pnl += pnl
        
        print(f"\n{i}. {emoji} {sig['model']} {sig['direction']}")
        print(f"   Time: {sig['timestamp'][:19]}")
        print(f"   Confidence: {sig['confidence']:.2%}")
        print(f"   Entry: ${sig['entry_price']:,.2f}")
        print(f"   Outcome: {outcome} ({pnl:+.2f}%)")
    
    if len(surgical_signals) > 10:
        print(f"\n... and {len(surgical_signals) - 10} more signals")
    
    print(f"\n{'='*70}")
    print(f"SURGICAL SUMMARY:")
    print(f"  Wins: {wins} | Losses: {losses} | Open: {opens}")
    print(f"  Total P&L: {total_pnl:+.2f}%")
    if wins + losses > 0:
        print(f"  Win Rate: {wins/(wins+losses)*100:.1f}%")
    print(f"{'='*70}")
else:
    print("\n❌ No SURGICAL signals crossed thresholds today")

print(f"\n✅ Reconstruction complete")
