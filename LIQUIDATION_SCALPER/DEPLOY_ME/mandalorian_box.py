#!/usr/bin/env python3
"""
🛡️ MANDALORIAN BOX - TERMINAL COMMAND CENTER
Visualize the Hyperliquid Data Stream in a TUI.
"""

import curses
import time
import threading
import collections
import json
import re
import os
from datetime import datetime

# CONFIG
LOG_FILE = "logs/collector_debug.log"
MAX_TAPE_LEN = 20
MAX_WHALE_LEN = 10
WHALE_THRESH = 50000.0

# Data Stores
tape = collections.deque(maxlen=MAX_TAPE_LEN)
whales = collections.deque(maxlen=MAX_WHALE_LEN)
market_stats = {
    "price": 0.0,
    "vol_1m": 0.0,
    "trend": "NEUTRAL",
    "last_update": time.time()
}
running = True

# --- LOG READER THREAD ---
def log_reader():
    global market_stats
    if not os.path.exists(LOG_FILE):
        return

    curr_vol = 0
    last_min = datetime.now().minute

    with open(LOG_FILE, 'r') as f:
        f.seek(0, 2)
        while running:
            line = f.readline()
            if not line:
                time.sleep(0.05)
                continue
            
            match = re.search(r"data=b'({.*})'", line)
            if match:
                try:
                    data = json.loads(match.group(1))
                    if data.get('channel') == 'trades':
                        for t in data.get('data', []):
                            px = float(t['px'])
                            sz = float(t['sz'])
                            side = t['side'] # B/A
                            val = px * sz
                            users = t.get('users', ['???', '???'])
                            
                            # Update Global State
                            market_stats['price'] = px
                            market_stats['last_update'] = time.time()
                            
                            # 1m Volume
                            now_min = datetime.now().minute
                            if now_min != last_min:
                                curr_vol = 0
                                last_min = now_min
                            curr_vol += val
                            market_stats['vol_1m'] = curr_vol
                            
                            # Add to Tape
                            tape.appendleft({
                                'time': datetime.now().strftime('%H:%M:%S'),
                                'price': px,
                                'size': sz,
                                'side': side,
                                'val': val,
                                'user': users[0][:6] # Short address
                            })
                            
                            # Add to Whales
                            if val >= WHALE_THRESH:
                                whales.appendleft({
                                    'time': datetime.now().strftime('%H:%M:%S'),
                                    'price': px,
                                    'val': val,
                                    'side': side
                                })
                                
                except:
                    continue

# --- TUI ENGINE ---
def draw_dashboard(stdscr):
    # Setup Colors
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)   # Buy
    curses.init_pair(2, curses.COLOR_RED, -1)     # Sell
    curses.init_pair(3, curses.COLOR_CYAN, -1)    # UI
    curses.init_pair(4, curses.COLOR_WHITE, -1)   # Text
    curses.init_pair(5, curses.COLOR_YELLOW, -1)  # Warning
    
    stdscr.nodelay(True)
    stdscr.timeout(100) # Refresh every 100ms
    
    while running:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        
        # 1. HEADER
        title = " 🛡️  MANDALORIAN BOX "
        price_str = f" BTC: ${market_stats['price']:,.2f} "
        status_str = " STATUS: HUNTING "
        
        stdscr.attron(curses.color_pair(3) | curses.A_REVERSE)
        stdscr.addstr(0, 0, " " * w)
        stdscr.addstr(0, 2, title)
        stdscr.addstr(0, w//2 - len(price_str)//2, price_str)
        stdscr.addstr(0, w - len(status_str) - 2, status_str)
        stdscr.attroff(curses.color_pair(3) | curses.A_REVERSE)
        
        # 2. MARKET STATS (Top Left)
        stdscr.addstr(2, 2, "📊 MARKET INTEL", curses.color_pair(3) | curses.A_BOLD)
        stdscr.addstr(3, 2, "-"*20, curses.color_pair(3))
        stdscr.addstr(4, 2, f"Vol (1m): ${market_stats['vol_1m']:,.0f}")
        
        # Trend Logic
        trend = "NEUTRAL"
        if len(tape) > 5:
            last_5 = list(tape)[:5]
            buys = sum(1 for t in last_5 if t['side'] == 'B')
            if buys >= 4: trend = "BULLISH 🟢"
            elif buys <= 1: trend = "BEARISH 🔴"
        
        stdscr.addstr(5, 2, f"Trend:    {trend}")
        
        # 3. WHALE RADAR (Top Right)
        col_right = w // 2
        stdscr.addstr(2, col_right, "🐋 WHALE RADAR (> $50k)", curses.color_pair(5) | curses.A_BOLD)
        stdscr.addstr(3, col_right, "-"*30, curses.color_pair(5))
        
        for i, whale in enumerate(whales):
            if 4 + i >= h // 2: break
            color = curses.color_pair(1) if whale['side'] == 'B' else curses.color_pair(2)
            side_str = "BUY " if whale['side'] == 'B' else "SELL"
            row_str = f"{whale['time']} {side_str} ${whale['val']/1000:.1f}k @ {whale['price']:.0f}"
            stdscr.addstr(4 + i, col_right, row_str, color)

        # 4. THE TAPE (Bottom)
        mid_y = h // 2
        stdscr.addstr(mid_y, 2, "📜 THE TAPE (Live Stream)", curses.color_pair(3) | curses.A_BOLD)
        stdscr.addstr(mid_y + 1, 2, "-" * (w - 4), curses.color_pair(3))
        
        # Header
        stdscr.addstr(mid_y + 2, 2, f"{'PRICE':<10} {'SIZE':<10} {'SIDE':<6} {'VAL(USD)':<12} {'USER':<10}", curses.color_pair(4))
        
        for i, t in enumerate(tape):
            y = mid_y + 3 + i
            if y >= h - 2: break
            
            color = curses.color_pair(1) if t['side'] == 'B' else curses.color_pair(2)
            side_icon = "🟢" if t['side'] == 'B' else "🔴"
            
            row_str = f"{t['price']:<10.1f} {t['size']:<10.4f} {side_icon:<6} ${t['val']:<11,.0f} {t['user']:<10}"
            stdscr.addstr(y, 2, row_str, color)
            
        # Draw Border
        stdscr.border()
        
        # Refresh
        stdscr.refresh()
        
        # Input (Exit)
        ch = stdscr.getch()
        if ch == ord('q'):
            break

def main():
    # Start Reader
    t = threading.Thread(target=log_reader)
    t.daemon = True
    t.start()
    
    # Start UI
    try:
        curses.wrapper(draw_dashboard)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
    finally:
        global running
        running = False
        print("MandalorianBox Shutdown.")

if __name__ == "__main__":
    main()
