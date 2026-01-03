#!/usr/bin/env python3
"""
Recover lost MTF Scalper trade prices from historical data
"""
import requests
from datetime import datetime
import json

# MTF Scalper trade timestamps (UTC)
trades = [
    {"id": 2, "time": "2025-12-30 07:02:50", "confidence": 22.83},
    {"id": 4, "time": "2026-01-01 06:56:58", "confidence": 22.68},
    {"id": 6, "time": "2026-01-01 09:40:48", "confidence": 28.71},
    {"id": 8, "time": "2026-01-01 10:35:09", "confidence": 24.76},
]

def get_price_at_timestamp(timestamp_str):
    """Get BTC price at specific timestamp from Hyperliquid"""
    # Convert to milliseconds
    dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
    ts_ms = int(dt.timestamp() * 1000)
    
    # Query 5-minute candles around this time
    url = "https://api.hyperliquid.xyz/info"
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": "BTC",
            "interval": "5m",
            "startTime": ts_ms - 300000,  # 5 min before
            "endTime": ts_ms + 300000      # 5 min after
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            candles = response.json()
            if candles and len(candles) > 0:
                # Find closest candle
                closest = min(candles, key=lambda c: abs(int(c['t']) - ts_ms))
                price = float(closest['c'])
                candle_time = datetime.fromtimestamp(int(closest['t']) / 1000)
                return price, candle_time
    except Exception as e:
        print(f"Error: {e}")
    
    return None, None

print("="*70)
print("🔍 RECOVERING LOST MTF SCALPER PRICES")
print("="*70)

recovered = []

for trade in trades:
    print(f"\n📊 Trade #{trade['id']} - {trade['time']}")
    print(f"   Confidence: {trade['confidence']:.2%}")
    
    price, candle_time = get_price_at_timestamp(trade['time'])
    
    if price:
        # Calculate TP/SL
        tp_pct = 0.015  # 1.5%
        sl_pct = 0.008  # 0.8%
        tp_price = price * (1 + tp_pct)
        sl_price = price * (1 - sl_pct)
        pnl_tp = (tp_price - price) / price * 1000  # $1000 position
        pnl_sl = (sl_price - price) / price * 1000
        
        print(f"   ✅ RECOVERED!")
        print(f"   Entry Price: ${price:,.2f}")
        print(f"   Candle Time: {candle_time}")
        print(f"   TP: ${tp_price:,.2f} (+{tp_pct*100:.1f}% / +${pnl_tp:.2f})")
        print(f"   SL: ${sl_price:,.2f} (-{sl_pct*100:.1f}% / ${pnl_sl:.2f})")
        
        recovered.append({
            "id": trade['id'],
            "time": trade['time'],
            "confidence": trade['confidence'],
            "price": price,
            "tp": tp_price,
            "sl": sl_price,
            "pnl_tp": pnl_tp,
            "pnl_sl": pnl_sl
        })
    else:
        print(f"   ❌ Could not recover price")

print("\n" + "="*70)
print("📊 RECOVERY SUMMARY")
print("="*70)
print(f"Total Trades: {len(trades)}")
print(f"Recovered: {len(recovered)}")
print(f"Failed: {len(trades) - len(recovered)}")

if recovered:
    print("\n✅ RECOVERED TRADES:")
    for t in recovered:
        print(f"\n   Trade #{t['id']}:")
        print(f"   Entry: ${t['price']:,.2f}")
        print(f"   TP: ${t['tp']:,.2f} (+${t['pnl_tp']:.2f})")
        print(f"   SL: ${t['sl']:,.2f} (${t['pnl_sl']:.2f})")

# Save to JSON
with open('recovered_mtf_trades.json', 'w') as f:
    json.dump(recovered, f, indent=2, default=str)
    print(f"\n💾 Saved to recovered_mtf_trades.json")

print("\n" + "="*70)
