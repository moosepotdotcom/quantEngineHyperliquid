#!/usr/bin/env python3
"""
🌊 INFINITE LIQUIDATION SCALPER (SIMULATION LOOP)
Strategy: Aggressive Momentum (V2 logic)
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
🌊  L I Q U I D A T I O N   S C A L P E R   (INFINITE FEED)
{Colors.BLUE}   Status: SIMULATION LOOP (Network Blocked)
   Data: Jan 2026 Proxy Data (Replaying...)
   Strategy: Aggressive Momentum (Target 0.2%)
{Colors.CYAN}======================================================================{Colors.RESET}
"""

class LiquidationScalper:
    def __init__(self, data_path='data.csv'):
        self.data_path = data_path
        self.balance = 10000.0

    def load_data(self):
        # Path logic
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
            sys.exit("Data not found")
            
        self.df = pd.read_csv(self.data_path)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        self.df = self.df.sort_values('timestamp').reset_index(drop=True)

    def run(self):
        self.load_data()
        print(BANNER)
        print(f"📊 {len(self.df)} candles loaded. Starting Infinite Loop...\n")
        
        loop_count = 1
        wins = 0
        losses = 0
        
        while True:
            print(f"{Colors.YELLOW}🔄 STARTING FEED REPLAY (Loop {loop_count}){Colors.RESET}")
            print(f"{Colors.BOLD}{'TIME':<20} | {'PRICE':<10} | {'SCORE':<5} | {'SIGNAL':<10} | {'Outcome':<15}{Colors.RESET}")
            print("-" * 90)
            
            for i, row in self.df.iterrows():
                if i < 5: continue
                
                timestamp = row['timestamp']
                price = row['close']
                score = row['liq_proxy_score']
                change = row.get('price_change', 0)
                
                signal = "HOLD"
                color = Colors.RESET
                outcome = ""
                
                # V2 LOGIC
                TP = 0.002
                SL = 0.001
                
                if score >= 4:
                    future_ret = row.get('future_return_3', 0)
                    
                    if change > 0: # BUY
                        signal = "BUY 🟢"
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
                            
                    elif change < 0: # SELL
                        signal = "SELL 🔴"
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

                if "BUY" in signal or "SELL" in signal:
                    print(f"{color}{str(timestamp):<20} | ${price:<9.2f} | {score:<5} | {signal:<10} | {outcome:<15}{Colors.RESET}")
                    time.sleep(0.1) # Fast Pace
                elif i % 100 == 0:
                     sys.stdout.write(f"\r{Colors.CYAN}Streaming... {str(timestamp)} | Bal: ${self.balance:,.2f} | W/L: {wins}/{losses}{Colors.RESET}")
                     sys.stdout.flush()
                     time.sleep(0.005)
                     
            print(f"\n{Colors.GREEN}✅ REPLAY COMPLETE. RESTARTING...{Colors.RESET}\n")
            time.sleep(2)
            loop_count += 1

if __name__ == "__main__":
    bot = LiquidationScalper()
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\n👋 Simulation Stopped.")
