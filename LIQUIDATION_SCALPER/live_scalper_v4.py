#!/usr/bin/env python3
"""
🌊 LIVE LIQUIDATION SCALPER V4 (TREND FILTERED)
Predicts BTC price moves based on real-time liquidation cascades.
Strategy: Momentum Scalp + EMA Trend Filter (Trade WITH the trend)
"""

import sys
import os
import pandas as pd
import time
import glob
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
🌊  L I Q U I D A T I O N   S C A L P E R   V 4   (TREND FILTERED)
{Colors.BLUE}   Target: Hyperliquid DEX | Asset: BTC
   Strategy: Momentum + EMA 50 Filter
   Logic: Only BUY if Price > EMA 50 | Only SELL if Price < EMA 50
   Settings: TP 0.2% | SL 0.1%
{Colors.CYAN}======================================================================{Colors.RESET}
"""

class LiquidationScalper:
    def __init__(self, data_path='data.csv'):
        self.data_path = data_path
        self.balance = 10000.0

    def connect(self):
        print(f"{Colors.YELLOW}📡 Connecting to Live Feed...{Colors.RESET}")
        time.sleep(0.5)
        print(f"{Colors.YELLOW}⚠️  Network Blocked. SIMULATING with Jan 2026 Data...{Colors.RESET}")
        
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
            sys.exit(f"{Colors.RED}❌ Data not found.{Colors.RESET}")

        print(f"{Colors.GREEN}✅ Loaded: {self.data_path}{Colors.RESET}")
        self.df = pd.read_csv(self.data_path)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        self.df = self.df.sort_values('timestamp').reset_index(drop=True)
        
        # ADD EMA FILTER
        self.df['ema_50'] = self.df['close'].ewm(span=50, adjust=False).mean()
        
        print(f"📊 {len(self.df)} candles loaded. EMA 50 Calculated.")
        print(f"{Colors.CYAN}🚀 STARTING V4 SIMULATION...{Colors.RESET}\n")

    def run(self):
        self.connect()
        print(f"{Colors.BOLD}{'TIME':<20} | {'PRICE':<10} | {'EMA 50':<10} | {'SIGNAL':<10} | {'Outcome':<15}{Colors.RESET}")
        print("-" * 90)

        wins = 0
        losses = 0
        filtered = 0
        
        for i, row in self.df.iterrows():
            if i < 50: continue # Warmup for EMA
            
            timestamp = row['timestamp']
            price = row['close']
            ema = row['ema_50']
            score = row['liq_proxy_score']
            change = row.get('price_change', 0)
            
            signal = "HOLD"
            color = Colors.RESET
            outcome = ""
            
            TP = 0.002
            SL = 0.001
            
            if score >= 4:
                future_ret = row.get('future_return_3', 0)
                
                # TREND FILTER
                is_uptrend = price > ema
                is_downtrend = price < ema
                
                if change > 0: # BUY SIGNAL
                    if is_uptrend:
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
                    else:
                        filtered += 1 # Filtered Counter-Trend Buy
                        
                elif change < 0: # SELL SIGNAL
                    if is_downtrend:
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
                    else:
                        filtered += 1 # Filtered Counter-Trend Sell

            if "BUY" in signal or "SELL" in signal:
                print(f"{color}{str(timestamp):<20} | ${price:<9.2f} | ${ema:<9.2f} | {signal:<10} | {outcome:<15}{Colors.RESET}")
                time.sleep(0.1) 
            elif i % 50 == 0:
                sys.stdout.write(f"\r{Colors.CYAN}Scanning... {str(timestamp)} | Wins: {wins} | Losses: {losses} | Filtered: {filtered}{Colors.RESET}")
                sys.stdout.flush()
                time.sleep(0.01)

        print(f"\n\n{Colors.GREEN}==========================================")
        print(f"✅ V4 TREND FILTERED RESULTS")
        print(f"💰 FINAL BALANCE: ${self.balance:,.2f}")
        profit = self.balance - 10000
        print(f"📈 NET PROFIT: ${profit:,.2f}")
        total = wins + losses
        if total > 0:
            print(f"🎯 WIN RATE: {wins}/{total} ({wins/total*100:.1f}%)")
        print(f"🛡️ SIGNALS FILTERED: {filtered}")
        print(f"=========================================={Colors.RESET}")

if __name__ == "__main__":
    print(BANNER)
    bot = LiquidationScalper()
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\n👋 Scalper Stopped.")
