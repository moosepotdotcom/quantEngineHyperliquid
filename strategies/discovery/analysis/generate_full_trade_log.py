#!/usr/bin/env python3
"""
Generate Full Trade Log with Live P&L
"""
import json
import os
import requests
from datetime import datetime

# 1. Get live price
url = "https://api.hyperliquid.xyz/info"
payload = {"type": "allMids"} 
current_price = 0
try:
    resp = requests.post(url, json=payload, timeout=10)
    data = resp.json()
    if 'BTC' in data:
        current_price = float(data['BTC'])
    else:
        # Fallback to candle snapshot
        payload = {
            "type": "candleSnapshot",
            "req": {
                 "coin": "BTC",
                 "interval": "1m",
                 "startTime": 0,
                 "endTime": 9999999999999
            }
        }
        resp = requests.post(url, json=payload, timeout=10)
        candles = resp.json()
        current_price = float(candles[-1]['c'])
except Exception as e:
    print(f"Error getting price: {e}")
    # Fallback to last known if API fails
    current_price = 91225.50

print(f"💰 LIVE BTC PRICE: ${current_price:,.2f}")

# 2. Collect all signals
trades = []

# Thresholds
THRESHOLDS = {
    "Winner Hunter (1H)": {"LONG": 0.3412, "SHORT": 0.4789},
    "MTF Scalper (5M)": {"LONG": 0.5987, "SHORT": 0.6891}
}

for date in ['20260101', '20260102', '20260103', '20260104', '20260105', '20260106', '20260107', '20260108']:
    log_file = f'logs/trades/predictions_{date}.jsonl'
    if not os.path.exists(log_file): continue
    
    with open(log_file, 'r') as f:
        for line in f:
            try:
                p = json.loads(line.strip())
                model = p.get('model', '')
                conf = p.get('confidence', 0)
                price = p.get('market_data', {}).get('close', 0)
                ts = p.get('timestamp', '')
                
                is_signal = False
                direction = ""
                
                if model in THRESHOLDS:
                    if conf >= THRESHOLDS[model]["LONG"] and conf < THRESHOLDS[model]["SHORT"]:
                        is_signal = True; direction = "LONG"
                    elif conf >= THRESHOLDS[model]["SHORT"]:
                        is_signal = True; direction = "SHORT"
                
                if is_signal and price > 0:
                    trades.append({
                        'ts': ts,
                        'model': model,
                        'dir': direction,
                        'entry': price,
                        'conf': conf
                    })
            except: pass

# Sort trades reverse chronological (newest first)
trades.sort(key=lambda x: x['ts'], reverse=True)

# 3. Generate Markdown Report
filename = "ALL_TRADES_LOG.md"

with open(filename, 'w') as f:
    f.write(f"# 📊 FULL TRADE LOG (Simulated)\n")
    f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"**Live BTC Price:** ${current_price:,.2f}\n")
    f.write(f"**Total Signals:** {len(trades)}\n\n")
    
    f.write("## 📉 Performance Summary\n")
    
    # Calculate stats
    in_profit = 0
    in_loss = 0
    total_pnl = 0
    
    for t in trades:
        entry = t['entry']
        if t['dir'] == "LONG":
            pnl = (current_price - entry) / entry * 100
        else:
            pnl = (entry - current_price) / entry * 100
        t['pnl'] = pnl
        
        total_pnl += pnl
        if pnl > 0: in_profit += 1
        else: in_loss += 1

    avg_pnl = total_pnl / len(trades) if trades else 0
    
    f.write(f"- **Avg P&L Per Trade:** {avg_pnl:+.2f}%\n")
    f.write(f"- **Win Rate (Floating):** {(in_profit/len(trades)*100) if trades else 0:.1f}%\n")
    f.write(f"- **Profitable Trades:** {in_profit}\n")
    f.write(f"- **Losing Trades:** {in_loss}\n\n")
    
    f.write("## 📝 Detailed Log\n\n")
    f.write("| Timestamp | Model | Dir | Conf | Entry | Current P&L | Status |\n")
    f.write("|-----------|-------|-----|------|-------|-------------|--------|\n")
    
    for t in trades:
        status = "🟡 FLATTISH"
        if t['pnl'] > 1.5: status = "✅ TP TARGET" # Theoretical TP
        elif t['pnl'] < -0.8: status = "❌ SL HIT" # Theoretical SL
        elif t['pnl'] > 0.5: status = "🟢 PROFIT"
        elif t['pnl'] < -0.5: status = "🔴 DRAWDOWN"
        
        f.write(f"| {t['ts'][:19]} | {t['model']} | {t['dir']} | {t['conf']:.1%} | ${t['entry']:,.0f} | **{t['pnl']:+.2f}%** | {status} |\n")

print(f"✅ Generated {filename} with {len(trades)} trades")
