#!/usr/bin/env python3
"""
🌊 LIVE LIQUIDATION SCALPER V3 (REVERSAL STRATEGY)
Predicts BTC price moves based on real-time liquidation cascades.
Strategy: Reversal Scalping (Fade the Move)
"""

import sys
import os
import pandas as pd
import time
import glob
import random
from datetime import datetime

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
🌊  L I Q U I D A T I O N   S C A L P E R   V 3   (REVERSAL)
{Colors.BLUE}   Target: Hyperliquid DEX | Asset: BTC
   Strategy: FADE THE MOVE (Liquidation = Exhaustion)
   Settings: TP 0.3% | SL 0.15% (2:1 Ratio)
{Colors.CYAN}======================================================================{Colors.RESET}
"""

class LiquidationScalper:
    def __init__(self, data_path='data.csv'):
        self.data_path = data_path
        self.balance = 10000.0
        self.simulation_speed = 0.05

    def connect(self):
        print(f"{Colors.YELLOW}📡 Connecting to Hyperliquid WebSocket...{Colors.RESET}")
        time.sleep(1)
        print(f"{Colors.RED}❌ Connection Failed: Network Blocked{Colors.RESET}")
        print(f"{Colors.YELLOW}⚠️  Switching to SIMULATION MODE (Jan 2026){Colors.RESET}")
        
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
             proxies = glob.glob('*proxy*.csv')
             if proxies:
                 self.data_path = proxies[0]
                 found = True

        if not found:
            print(f"{Colors.RED}❌ FATAL: Simulation data not found.{Colors.RESET}")
            sys.exit(1)

        print(f"{Colors.GREEN}✅ Loaded: {self.data_path}{Colors.RESET}")
        self.df = pd.read_csv(self.data_path)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        self.df = self.df.sort_values('timestamp').reset_index(drop=True)
        print(f"📊 {len(self.df)} candles loaded.")
        print(f"{Colors.CYAN}🚀 STARTING REVERSAL SIMULATION...{Colors.RESET}\n")

    def run(self):
        self.connect()
        print(f"{Colors.BOLD}{'TIME':<20} | {'PRICE':<10} | {'SCORE':<5} | {'SIGNAL':<10} | {'Outcome (15m)':<15}{Colors.RESET}")
        print("-" * 90)

        wins = 0
        losses = 0
        
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
            
            # REVERSAL LOGIC
            # If Green Candle Spike (change > 0) -> SELL (Fade)
            # If Red Candle Spike (change < 0) -> BUY (Catch Dip)
            
            TP = 0.003 # 0.3% (Slightly wider for reversal)
            SL = 0.0015 # 0.15%
            
            if score >= 4:
                future_ret = row.get('future_return_3', 0)
                
                if change > 0: # Green Spike
                    signal = "SELL 🔴" # FADE
                    color = Colors.RED
                    if future_ret < -TP: 
                        outcome = "WIN 🏆"
                        self.balance += 1000 * TP
                        wins += 1
                    elif future_ret > SL:
                        outcome = "LOSS ❌"
                        self.balance -= 1000 * SL
                        losses += 1
                    else:
                        outcome = "FLAT ➖"
                        
                elif change < 0: # Red Spike
                    signal = "BUY 🟢" # CATCH
                    color = Colors.GREEN
                    if future_ret > TP: 
                        outcome = "WIN 🏆"
                        self.balance += 1000 * TP
                        wins += 1
                    elif future_ret < -SL:
                        outcome = "LOSS ❌"
                        self.balance -= 1000 * SL
                        losses += 1
                    else:
                        outcome = "FLAT ➖"

            if "BUY" in signal or "SELL" in signal:
                print(f"{color}{str(timestamp):<20} | ${price:<9.2f} | {score:<5} | {signal:<10} | {outcome:<15}{Colors.RESET}")
                time.sleep(0.1) 
            elif i % 50 == 0:
                sys.stdout.write(f"\r{Colors.CYAN}Scanning... {str(timestamp)} | Wins: {wins} | Losses: {losses} | Bal: ${self.balance:.2f}{Colors.RESET}")
                sys.stdout.flush()
                time.sleep(0.01)

        print(f"\n\n{Colors.GREEN}==========================================")
        print(f"✅ V3 REVERSAL SIMULATION COMPLETE")
        print(f"💰 FINAL BALANCE: ${self.balance:,.2f}")
        profit = self.balance - 10000
        print(f"📈 NET PROFIT: ${profit:,.2f}")
        total = wins + losses
        if total > 0:
            print(f"🎯 WIN RATE: {wins}/{total} ({wins/total*100:.1f}%)")
        print(f"=========================================={Colors.RESET}")

if __name__ == "__main__":
    print(BANNER)
    bot = LiquidationScalper()
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\n👋 Scalper Stopped.")
