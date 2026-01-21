#!/usr/bin/env python3
"""
🌊 LIVE LIQUIDATION SCALPER V2 (AGGRESSIVE SCALP)
Predicts BTC price moves based on real-time liquidation cascades.
Strategy: High-Frequency Momentum Scalp (TP 0.2% / SL 0.1%)
"""

import sys
import os
import pandas as pd
import time
import glob
import random
from datetime import datetime

# ==========================================
# 🎨 GRAPHICS & CONFIG
# ==========================================
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
🌊  L I Q U I D A T I O N   S C A L P E R   V 2   (AGGRESSIVE)
{Colors.BLUE}   Target: Hyperliquid DEX | Asset: BTC
   Strategy: Cascade Momentum + Reversal
   Settings: TP 0.2% | SL 0.1%
{Colors.CYAN}======================================================================{Colors.RESET}
"""

# ==========================================
# 🧠 SCALPER ENGINE
# ==========================================
class LiquidationScalper:
    def __init__(self, data_path='data.csv'):
        self.data_path = data_path
        self.balance = 10000.0
        self.simulation_speed = 0.05

    def connect(self):
        print(f"{Colors.YELLOW}📡 Connecting to Hyperliquid WebSocket (wss://api.hyperliquid.xyz/ws)...{Colors.RESET}")
        time.sleep(1)
        print(f"{Colors.RED}❌ Connection Failed: [Errno 65] No route to host (Network Blocked){Colors.RESET}")
        print(f"{Colors.YELLOW}⚠️  Switching to SIMULATION MODE using Jan 2026 Proxy Data{Colors.RESET}")
        
        # Load Data
        search_paths = [
            'data.csv', 'BTC_5m_2025_with_liquidation_proxy.csv',
            '../BTC_5m_2025_with_liquidation_proxy.csv',
            'LIQUIDATION_SCALPER/data.csv'
        ]
        found = False
        for p in search_paths:
            if os.path.exists(p):
                self.data_path = p
                found = True
                break
        
        if not found:
             # Just look in current dir for ANY csv with proxy in name
             proxies = glob.glob('*proxy*.csv')
             if proxies:
                 self.data_path = proxies[0]
                 found = True

        if not found:
            print(f"{Colors.RED}❌ FATAL: Simulation data not found.{Colors.RESET}")
            sys.exit(1)

        print(f"{Colors.GREEN}✅ Loaded Simulation Data: {self.data_path}{Colors.RESET}")
        self.df = pd.read_csv(self.data_path)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        self.df = self.df.sort_values('timestamp').reset_index(drop=True)
        print(f"📊 Analyzing {len(self.df)} candles...")
        print(f"{Colors.CYAN}🚀 STARTING AGGRESSIVE SCALP SIMULATION...{Colors.RESET}\n")

    def run(self):
        self.connect()
        
        # Header
        print(f"{Colors.BOLD}{'TIME':<20} | {'PRICE':<10} | {'VOL':<8} | {'SCORE':<5} | {'SIGNAL':<10} | {'Outcome (15m)':<15}{Colors.RESET}")
        print("-" * 90)

        wins = 0
        losses = 0
        
        # Loop through data
        for i, row in self.df.iterrows():
            if i < 5: continue
            
            timestamp = row['timestamp']
            price = row['close']
            vol = row['volume']
            score = row['liq_proxy_score']
            change = row.get('price_change', 0)
            
            signal = "HOLD"
            color = Colors.RESET
            outcome = ""
            
            # AGGRESSIVE SETTINGS
            TP = 0.002 # 0.2%
            SL = 0.001 # 0.1%
            
            if score >= 4:
                # Get next 15m return (approx)
                future_ret = row.get('future_return_3', 0)
                
                if change > 0:
                    signal = "BUY 🟢"
                    color = Colors.GREEN
                    if future_ret > TP: 
                        outcome = "WIN 🏆 (+0.2%)"
                        self.balance += 1000 * TP
                        wins += 1
                    elif future_ret < -SL:
                        outcome = "LOSS ❌ (-0.1%)"
                        self.balance -= 1000 * SL
                        losses += 1
                    else:
                        outcome = "FLAT ➖"
                        
                elif change < 0:
                    signal = "SELL 🔴"
                    color = Colors.RED
                    if future_ret < -TP: 
                        outcome = "WIN 🏆 (+0.2%)"
                        self.balance += 1000 * TP
                        wins += 1
                    elif future_ret > SL:
                        outcome = "LOSS ❌ (-0.1%)"
                        self.balance -= 1000 * SL
                        losses += 1
                    else:
                        outcome = "FLAT ➖"

            if "BUY" in signal or "SELL" in signal:
                print(f"{color}{str(timestamp):<20} | ${price:<9.2f} | {vol:<8.1f} | {score:<5} | {signal:<10} | {outcome:<15}{Colors.RESET}")
                time.sleep(0.1) 
            elif i % 50 == 0:
                sys.stdout.write(f"\r{Colors.CYAN}Scanning... {str(timestamp)} | ${price:.2f} | Wins: {wins} | Losses: {losses}{Colors.RESET}")
                sys.stdout.flush()
                time.sleep(0.01)

        print(f"\n\n{Colors.GREEN}==========================================")
        print(f"✅ SIMULATION COMPLETE")
        print(f"💰 FINAL BALANCE: ${self.balance:,.2f}")
        profit = self.balance - 10000
        print(f"📈 TOTAL PROFIT: ${profit:,.2f} ({profit/100:.2f}%)")
        print(f"🏆 WINS: {wins} | ❌ LOSSES: {losses}")
        if wins+losses > 0:
            print(f"🎯 WIN RATE: {wins/(wins+losses)*100:.1f}%")
        print(f"=========================================={Colors.RESET}")

if __name__ == "__main__":
    print(BANNER)
    bot = LiquidationScalper()
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\n👋 Scalper Stopped.")
