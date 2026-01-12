import re
import requests
import json
import time
from datetime import datetime

LOG_FILE = "/tmp/reconstructed_logs.txt"
POSITION_SIZE_BTC = 1.27

SETTINGS = {
    'Winner Hunter (1H)': {'tp': 0.015, 'sl': 0.008, 'thresh': 27.52},
    'MTF Scalper (5M)': {'tp': 0.008, 'sl': 0.005, 'thresh': 20.13}
}

def parse_full_history():
    print("🛠️ PARSING FULL LOG HISTORY...")
    with open(LOG_FILE, 'r') as f:
        lines = f.readlines()

    signals = []
    # Identify signal blocks by searching for 'SIGNAL DETECTED'
    for i, line in enumerate(lines):
        if 'SIGNAL DETECTED' in line.upper():
            # Extract a context block (25 lines before)
            start_idx = max(0, i - 25)
            block = "".join(lines[start_idx:i+1])
            
            conf_match = re.search(r'Confidence:\s*([\d.]+)%', block)
            price_match = re.search(r'Price:\s*\$?([\d,.]+)', block)
            time_match = re.search(r'Time:\s*([\d\-:\s]+)', block)
            if not time_match:
                # Try to find a timestamp in nearby lines if not in TRADE PLAN
                time_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', block)
            
            model_match = re.search(r'Model:\s*([\w\s()\-0-9]+)', block)
            
            if conf_match and price_match:
                price = float(price_match.group(1).replace(',', ''))
                conf = float(conf_match.group(1))
                model = "MTF Scalper (5M)"
                if model_match and "Winner" in model_match.group(1):
                    model = "Winner Hunter (1H)"
                
                timestamp = time_match.group(1).strip() if time_match else "Unknown"
                
                if price > 0:
                    signals.append({
                        'conf': conf,
                        'price': price,
                        'time': timestamp,
                        'model': model
                    })

    # Deduplicate based on model, approximate time, and entry price
    unique = {}
    for s in signals:
        # Round time to minutes for dedup
        time_key = s['time'][:16] if len(s['time']) >= 16 else s['time']
        key = f"{s['model']}_{time_key}_{int(s['price'])}"
        if key not in unique:
            unique[key] = s
            
    return sorted(unique.values(), key=lambda x: x['time'])

def check_trade_result(signal):
    if signal['time'] == "Unknown" or not signal['time']:
        return "ERROR", 0
        
    try:
        # Normalize time format for strptime
        time_str = signal['time'].split('.')[0]
        dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
        start_ms = int(dt.timestamp() * 1000)
    except Exception as e:
        print(f"   ⚠️ Could not parse time: {signal['time']} -> {e}")
        return "BAD_TIME", 0

    url = "https://api.hyperliquid.xyz/info"
    # Check 18 hours per trade
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": "BTC",
            "interval": "5m", 
            "startTime": start_ms,
            "endTime": start_ms + (18 * 3600 * 1000)
        }
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=15).json()
        if not resp:
            return "PENDING/MISSING_DATA", 0
            
        rules = SETTINGS[signal['model']]
        tp_target = signal['price'] * (1 + rules['tp'])
        sl_target = signal['price'] * (1 - rules['sl'])
        
        for c in resp:
            h, l = float(c['h']), float(c['l'])
            # Check for Stop Loss first (conservative)
            if l <= sl_target:
                return "LOSS", sl_target
            if h >= tp_target:
                return "WIN", tp_target
        
        return "EXPIRED", float(resp[-1]['c'])
    except Exception as e:
        print(f"   ⚠️ API Error for {signal['time']}: {e}")
        return "API_ERROR", 0

def main():
    signals = parse_full_history()
    print(f"✅ Extracted {len(signals)} unique trade attempts from logs.")
    
    audit_results = []
    print("\n🔍 EVALUATING OUTCOMES AGAINST HYPERLIQUID DATA...")
    for s in signals:
        # Apply the thresholds requested by user
        thresh = SETTINGS[s['model']]['thresh']
        if s['conf'] < thresh:
            print(f"   ⏩ Skipping {s['time']} ({s['model']}): Confidence {s['conf']}% < {thresh}%")
            continue
            
        res, exit_px = check_trade_result(s)
        
        # Calculate P&L for 1.27 BTC
        pnl_usd = 0
        if exit_px > 0:
            # Simple P&L: size * (exit - entry)
            pnl_usd = POSITION_SIZE_BTC * (exit_px - s['price'])
            
        audit_results.append({**s, 'result': res, 'exit': exit_px, 'pnl': pnl_usd})
        emoji = "✅" if res == "WIN" else "❌" if res == "LOSS" else "🕒"
        print(f"   [{s['time']}] {s['model']} ({s['conf']}%): {emoji} {res} (${pnl_usd:+.2f})")
        time.sleep(0.1)

    # FINAL REPORT GENERATION
    report_path = "/Users/alifiyaa/Downloads/quantEngineHyperliquid/DEFINITIVE_JAN_AUDIT.md"
    wins = len([r for r in audit_results if r['result'] == 'WIN'])
    losses = len([r for r in audit_results if r['result'] == 'LOSS'])
    total = wins + losses
    win_rate = (wins / total * 100) if total > 0 else 0
    total_pnl = sum(r['pnl'] for r in audit_results)

    with open(report_path, 'w') as f:
        f.write(f"# 📊 Definitive Bot Performance Audit (Jan 1st - Jan 6th)\n\n")
        f.write(f"**Period:** 2026-01-01 to 2026-01-06\n")
        f.write(f"**Position Size:** 1.27 BTC\n")
        f.write(f"**Win Rate (Completed):** {win_rate:.1f}% ({wins} Wins / {losses} Losses)\n")
        f.write(f"**Total USD Profit/Loss:** **${total_pnl:,.2f}**\n\n")
        
        f.write("## 📜 Full Trade Log (High Confidence Signals Only)\n")
        f.write("| Time | Model | Conf | Entry | Exit | Result | P&L (USD) |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for r in audit_results:
            status_ico = "✅ WIN" if r['result'] == "WIN" else "❌ LOSS" if r['result'] == "LOSS" else f"🕒 {r['result']}"
            f.write(f"| {r['time']} | {r['model']} | {r['conf']}% | ${r['price']:,.2f} | ${r['exit']:,.2f} | {status_ico} | **{r['pnl']:+,.2f}** |\n")

    print(f"\n✨ DEFINITIVE AUDIT COMPLETE: {report_path}")

if __name__ == "__main__":
    main()
