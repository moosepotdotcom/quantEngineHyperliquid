#!/usr/bin/env python3
import re
import requests
import json
import time
from datetime import datetime, timedelta

LOG_FILE = "/tmp/signals_history.txt"
POSITION_SIZE_BTC = 1.27
TP_PCT = 0.015
SL_PCT = 0.008

def parse_logs():
    print("📖 Reading logs...")
    with open(LOG_FILE, 'r') as f:
        content = f.read()

    # Split by blocks that look like signals
    # Blocks start with Confidence
    blocks = re.split(r'   Confidence:', content)
    
    signals = []
    for block in blocks[1:]:  # Skip first empty split
        try:
            # Extract data using regex
            confidence_match = re.search(r'([\d.]+)%', block)
            price_match = re.search(r'Price: \$([\d,.]+)', block)
            model_match = re.search(r'Model: ([\w\s()\-0-9]+)', block)
            timestamp_match = re.search(r'📊 Last row timestamp: ([\d\-:\s]+)', block)
            
            if not (confidence_match and price_match and model_match and timestamp_match):
                continue
                
            confidence = float(confidence_match.group(1))
            price = float(price_match.group(1).replace(',', ''))
            model = model_match.group(1).strip()
            timestamp_str = timestamp_match.group(1).strip()
            
            # Simple deduplication based on Model and Bar Timestamp
            # Since the bot checks every minute, a 1H bar will generate many identical signals
            signal_key = f"{model}_{timestamp_str}"
            
            signals.append({
                'key': signal_key,
                'model': model,
                'price': price,
                'confidence': confidence,
                'time': timestamp_str
            })
        except Exception as e:
            print(f"   ⚠️ Failed to parse block: {e}")
            
    # Deduplicate
    unique_signals = {}
    for s in signals:
        if s['key'] not in unique_signals:
            unique_signals[s['key']] = s
            
    sorted_signals = sorted(unique_signals.values(), key=lambda x: x['time'])
    print(f"✅ Found {len(sorted_signals)} unique signals since Jan 1st.")
    return sorted_signals

def get_historical_data(coin, interval, start_time_str):
    """Fetch candles from Hyperliquid starting from the signal time"""
    url = "https://api.hyperliquid.xyz/info"
    
    dt = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
    start_ms = int(dt.timestamp() * 1000)
    # Fetch 24 hours of data after the signal
    end_ms = start_ms + (24 * 60 * 60 * 1000)
    
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": coin,
            "interval": interval,
            "startTime": start_ms,
            "endTime": end_ms
        }
    }
    
    try:
        resp = requests.post(url, json=payload)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"   ❌ Error fetching candles: {e}")
    return []

def simulate_outcome(signal):
    print(f"🔎 Simulating signal: {signal['model']} at {signal['time']} (${signal['price']})")
    
    # Thresholds
    thresholds = {
        'Winner Hunter (1H)': 27.52,
        'MTF Scalper (5M)': 20.13
    }
    
    if signal['confidence'] < thresholds.get(signal['model'], 0):
        print(f"   ⏩ Skipping: Confidence {signal['confidence']}% < threshold")
        return None

    entry_price = signal['price']
    tp_price = entry_price * (1 + TP_PCT)
    sl_price = entry_price * (1 - SL_PCT)
    
    # Use 1m candles for high resolution if possible, otherwise interval
    interval = '1m' if '5M' in signal['model'] else '5m'
    candles = get_historical_data('BTC', interval, signal['time'])
    
    if not candles:
        # Fallback to broader interval
        candles = get_historical_data('BTC', '1h', signal['time'])

    status = "PENDING"
    exit_time = None
    exit_price = None
    
    for c in candles:
        high = float(c['h'])
        low = float(c['l'])
        
        # Check if SL hit first (conservatism)
        if low <= sl_price:
            status = "HIT SL"
            exit_price = sl_price
            exit_time = datetime.fromtimestamp(c['t']/1000).strftime("%Y-%m-%d %H:%M")
            break
        # Check if TP hit
        if high >= tp_price:
            status = "HIT TP"
            exit_price = tp_price
            exit_time = datetime.fromtimestamp(c['t']/1000).strftime("%Y-%m-%d %H:%M")
            break
            
    if status == "PENDING":
        # If still pending after 24h, use current price (or last seen)
        if candles:
            exit_price = float(candles[-1]['c'])
            exit_time = "24h Expiry"
            status = "EXPIRED"
        else:
            return None

    # Financials
    pnl_pct = (exit_price - entry_price) / entry_price
    pnl_usd = POSITION_SIZE_BTC * (exit_price - entry_price)
    
    print(f"   🏁 Result: {status} at {exit_price} ({pnl_pct*100:+.2f}%) -> ${pnl_usd:+.2f}")
    
    return {
        **signal,
        'status': status,
        'exit_price': exit_price,
        'exit_time': exit_time,
        'pnl_pct': pnl_pct,
        'pnl_usd': pnl_usd
    }

def main():
    signals = parse_logs()
    results = []
    
    for s in signals:
        res = simulate_outcome(s)
        if res:
            results.append(res)
            time.sleep(0.5) # Rate limit protection

    if not results:
        print("❌ No valid completed trades found for simulation.")
        return

    # Generate Report
    report_file = "/Users/alifiyaa/Downloads/quantEngineHyperliquid/BACKTEST_SIMULATION_REPORT.md"
    
    total_pnl = sum([r['pnl_usd'] for r in results])
    wins = len([r for r in results if r['status'] == 'HIT TP'])
    losses = len([r for r in results if r['status'] == 'HIT SL'])
    win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0
    
    with open(report_file, 'w') as f:
        f.write(f"# 📊 Backtrack Analysis: 1.27 BTC Simulation\n\n")
        f.write(f"**Period:** Jan 1, 2026 - Jan 6, 2026\n")
        f.write(f"**Position Size:** {POSITION_SIZE_BTC} BTC\n")
        f.write(f"**Risk/Reward:** +{TP_PCT*100:.1f}% TP / -{SL_PCT*100:.1f}% SL\n\n")
        
        f.write(f"## 📈 Performance Summary\n")
        f.write(f"| Metric | Value |\n")
        f.write(f"| :--- | :--- |\n")
        f.write(f"| **Total Profit/Loss** | **${total_pnl:,.2f} USD** |\n")
        f.write(f"| **Win Rate** | {win_rate:.1f}% |\n")
        f.write(f"| **Total Trades** | {len(results)} |\n")
        f.write(f"| **Wins/Losses** | {wins}W - {losses}L |\n\n")
        
        f.write(f"## 📝 Trade Logs\n")
        f.write(f"| Time | Model | Confidence | Entry | Exit | Status | P&L (USD) |\n")
        f.write(f"| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for r in results:
            emoji = "✅" if "TP" in r['status'] else "❌" if "SL" in r['status'] else "🕒"
            f.write(f"| {r['time']} | {r['model']} | {r['confidence']:.2f}% | ${r['price']:,.2f} | ${r['exit_price']:,.2f} | {emoji} {r['status']} | **{r['pnl_usd']:+,.2f}** |\n")

    print(f"\n✨ Report generated: {report_file}")

if __name__ == "__main__":
    main()
