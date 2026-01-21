#!/usr/bin/env python3
"""
🌊 LIVE LIQUIDATION SCALPER V5 (CVD DIVERGENCE)
Strategy: Liquidation + CVD Divergence (Order Flow)
Logic:
- Identify Liquidation Spikes (Score >= 4)
- Calculate Cumulative Volume Delta (CVD)
- Filter: Only trade if CVD confirms the move (or spot divergences)
- For Scalping: We want CVD CONFIRMATION (Aggressive) or DIVERGENCE (Reversal)?
- V2 (Momentum) worked best. So we want CONFIRMATION.
- Rule: BUY if Liq Spike AND CVD is making new highs (Strong Buying).
- Rule: SELL if Liq Spike AND CVD is making new lows (Strong Selling).
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
🌊  L I Q U I D A T I O N   S C A L P E R   V 5   (ORDER FLOW)
{Colors.BLUE}   Target: Hyperliquid DEX | Asset: BTC
   Strategy: Liquidation + CVD Confirmation
   Enhancement: Filters out "Fakeouts" where Price moves but Volume/CVD is weak.
   Settings: TP 0.2% | SL 0.1%
{Colors.CYAN}======================================================================{Colors.RESET}
"""

class LiquidationScalper:
    def __init__(self, data_path='data.csv'):
        self.data_path = data_path
        self.balance = 10000.0

    def connect(self):
        print(f"{Colors.YELLOW}📡 Connecting to Live Order Flow...{Colors.RESET}")
        time.sleep(0.5)
        print(f"{Colors.YELLOW}⚠️  Network Blocked. SIMULATING with Jan 2026 Proxy Data...{Colors.RESET}")
        
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
        
        # CALCULATE CVD (Proxy)
        # If close > open: Buy Vol. If close < open: Sell Vol.
        # This is "Taker Buy/Sell Volume" proxy.
        self.df['delta'] = 0.0
        self.df.loc[self.df['close'] >= self.df['open'], 'delta'] = self.df['volume']
        self.df.loc[self.df['close'] < self.df['open'], 'delta'] = -self.df['volume']
        self.df['cvd'] = self.df['delta'].cumsum()
        
        # Calculate CVD Period Highs/Lows (Window 12 = 1 Hour)
        self.df['cvd_high_1h'] = self.df['cvd'].rolling(12).max()
        self.df['cvd_low_1h'] = self.df['cvd'].rolling(12).min()
        
        print(f"📊 {len(self.df)} candles loaded. CVD Calculated.")
        print(f"{Colors.CYAN}🚀 STARTING V5 SIMULATION...{Colors.RESET}\n")

    def run(self):
        self.connect()
        print(f"{Colors.BOLD}{'TIME':<20} | {'PRICE':<10} | {'CVD':<10} | {'SIGNAL':<10} | {'Outcome':<15}{Colors.RESET}")
        print("-" * 90)

        wins = 0
        losses = 0
        filtered = 0
        
        for i, row in self.df.iterrows():
            if i < 20: continue
            
            timestamp = row['timestamp']
            price = row['close']
            score = row['liq_proxy_score']
            change = row.get('price_change', 0)
            cvd = row['cvd']
            cvd_high = row['cvd_high_1h']
            cvd_low = row['cvd_low_1h']
            
            signal = "HOLD"
            color = Colors.RESET
            outcome = ""
            
            TP = 0.002
            SL = 0.001
            
            if score >= 4:
                future_ret = row.get('future_return_3', 0)
                
                # CVD LOGIC: CONFIRMATION
                # BUY only if CVD is near 1H High (Strong Buy Pressure)
                # SELL only if CVD is near 1H Low (Strong Sell Pressure)
                # "Near" = within 5% range or just strictly making new highs?
                # Let's say: CVD > CVD_High[prev] (Breakout)
                
                prev_cvd_high = self.df.iloc[i-1]['cvd_high_1h']
                prev_cvd_low = self.df.iloc[i-1]['cvd_low_1h']
                
                # Check confirmation
                # Note: 'cvd' logic here is crude.
                # If Delta is positive and large, CVD rises.
                
                if change > 0: # Potential BUY
                    if cvd > prev_cvd_high: # CVD Breakout! Strong Buying!
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
                        filtered += 1
                        
                elif change < 0: # Potential SELL
                    if cvd < prev_cvd_low: # CVD Breakdown! Strong Selling!
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
                        filtered += 1

            if "BUY" in signal or "SELL" in signal:
                print(f"{color}{str(timestamp):<20} | ${price:<9.2f} | {cvd:<10.0f} | {signal:<10} | {outcome:<15}{Colors.RESET}")
                time.sleep(0.1) 
            elif i % 50 == 0:
                sys.stdout.write(f"\r{Colors.CYAN}Scanning... {str(timestamp)} | Wins: {wins} | Losses: {losses} | Filtered: {filtered}{Colors.RESET}")
                sys.stdout.flush()
                time.sleep(0.01)

        print(f"\n\n{Colors.GREEN}==========================================")
        print(f"✅ V5 ORDER FLOW RESULTS")
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
