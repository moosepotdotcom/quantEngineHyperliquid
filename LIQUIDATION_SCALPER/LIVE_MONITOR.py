#!/usr/bin/env python3
"""
🌊 LOG STREAM SCALPER (LIVE RAW FEED)
Reads `logs/collector_debug.log` in real-time.
Parses raw "trades" channel.
Generates Signals on Heavy Hitting Trades (Whale Watching).
"""

import time
import os
import json
import re
import sys

# CONFIG
LOG_FILE = "logs/collector_debug.log"
WHALE_THRESHOLD_USD = 1000.0  # $1k Trade = Signal (Lowered for visibility)

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    YELLOW = '\033[93m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

BANNER = f"""
{Colors.CYAN}======================================================================
🌊  L I Q U I D A T I O N   S C A L P E R   (LOG STREAM)
{Colors.BLUE}   Source: {LOG_FILE}
   Mode: Live Trade Parsing (Whale Detector)
   Threshold: ${WHALE_THRESHOLD_USD:,.0f}
{Colors.CYAN}======================================================================{Colors.RESET}
"""

def parse_line(line):
    # Regex to extract JSON from: ++Rcv decoded: ... data=b'{JSON}'
    match = re.search(r"data=b'({.*})'", line)
    if match:
        try:
            json_str = match.group(1)
            # Fix single quotes if any (though logs usually valid JSON)
            return json.loads(json_str)
        except:
            return None
    return None

def main():
    print(BANNER)
    
    if not os.path.exists(LOG_FILE):
        print(f"{Colors.RED}❌ Log file not found: {LOG_FILE}{Colors.RESET}")
        return

    print(f"{Colors.GREEN}✅ Connected to Log Stream... Waiting for Whales...{Colors.RESET}")
    print(f"{Colors.BOLD}{'TIME':<15} | {'PRICE':<10} | {'SIZE (USD)':<12} | {'SIDE':<5} | {'SIGNAL':<10}{Colors.RESET}")
    print("-" * 70)
    
    # Seek to end
    with open(LOG_FILE, 'r') as f:
        f.seek(0, 2)
        
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.01)
                continue
                
            line = line.strip()
            if "trades" in line and "data=b" in line:
                data = parse_line(line)
                if data and data.get('channel') == 'trades':
                    trades = data.get('data', [])
                    for t in trades:
                        try:
                            price = float(t['px'])
                            size = float(t['sz'])
                            side = t['side'] 
                            value_usd = price * size
                            
                            if value_usd >= WHALE_THRESHOLD_USD:
                                timestamp = time.strftime('%H:%M:%S')
                                signal = "HOLD"
                                color = Colors.RESET
                                
                                if side == 'B':
                                    signal = "BUY 🟢"
                                    color = Colors.GREEN
                                else:
                                    signal = "SELL 🔴"
                                    color = Colors.RED
                                    
                                print(f"{color}{timestamp:<15} | ${price:<10.2f} | ${value_usd:<12,.0f} | {side:<5} | {signal:<10}{Colors.RESET}")
                        except:
                            continue

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Scalper Stopped.")
