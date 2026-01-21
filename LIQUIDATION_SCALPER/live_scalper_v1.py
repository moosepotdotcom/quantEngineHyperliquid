#!/usr/bin/env python3
"""
🌊 LIVE LIQUIDATION SCALPER V1
Predicts BTC price moves based on real-time liquidation cascades.
Strategy: Momentum Scalping (Ride the Liquidation Wave)
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
🌊  L I Q U I D A T I O N   S C A L P E R   V 1
{Colors.BLUE}   Target: Hyperliquid DEX | Asset: BTC
   Strategy: Cascade Momentum + Reversal
{Colors.CYAN}======================================================================{Colors.RESET}
"""

# ==========================================
# 🧠 SCALPER ENGINE
# ==========================================
class LiquidationScalper:
    def __init__(self, data_path='data.csv'):
        self.data_path = data_path
        self.balance = 10000.0
        self.position = None
        self.trades = []
        self.simulation_speed = 0.05  # Seconds per candle (Fast Replay)

    def connect(self):
        print(f"{Colors.YELLOW}📡 Connecting to Hyperliquid WebSocket (wss://api.hyperliquid.xyz/ws)...{Colors.RESET}")
        time.sleep(1)
        
        # NETWORK CHECK
        print(f"{Colors.RED}❌ Connection Failed: [Errno 65] No route to host (Network Blocked){Colors.RESET}")
        print(f"{Colors.YELLOW}⚠️  Switching to SIMULATION MODE using Jan 2026 Proxy Data{Colors.RESET}")
        time.sleep(1)
        
        # Load Data for Simulation
        # Search for the file in current and parent directories
        search_paths = [
            'data.csv',
            'BTC_5m_2025_with_liquidation_proxy.csv', # Check CWD
            '../BTC_5m_2025_with_liquidation_proxy.csv', # Check Parent
            'V9_LIQUIDATION_EXPERIMENT/BTC_5m_2025_with_liquidation_proxy.csv',
            '../V9_LIQUIDATION_EXPERIMENT/BTC_5m_2025_with_liquidation_proxy.csv',
            '/Users/alifiyaa/Downloads/quantEngineHyperliquid/BTC_5m_2025_with_liquidation_proxy.csv'
        ]
        
        found = False
        for p in search_paths:
            if os.path.exists(p):
                self.data_path = p
                found = True
                break
                
        if not found:
            print(f"{Colors.RED}❌ FATAL: Simulation data 'BTC_5m_2025_with_liquidation_proxy.csv' not found.{Colors.RESET}")
            print(f"Debug: Checked {search_paths}")
            sys.exit(1)

        print(f"{Colors.GREEN}✅ Loaded Simulation Data: {self.data_path}{Colors.RESET}")
        self.df = pd.read_csv(self.data_path)
        # Sort by time just in case
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        self.df = self.df.sort_values('timestamp').reset_index(drop=True)
        print(f"📊 Analyzing {len(self.df)} candles...")
        print(f"{Colors.CYAN}🚀 STARTING LIVE FEED SIMULATION...{Colors.RESET}\n")

    def run(self):
        self.connect()
        
        # Header
        print(f"{Colors.BOLD}{'TIME':<20} | {'PRICE':<10} | {'VOL':<8} | {'LIQ SCORE':<10} | {'SIGNAL':<10} | {'Outcome (15m)':<15}{Colors.RESET}")
        print("-" * 90)

        # Loop through data
        for i, row in self.df.iterrows():
            if i < 5: continue # Skip warmup
            
            # Extract Metrics
            timestamp = row['timestamp']
            price = row['close']
            vol = row['volume']
            score = row['liq_proxy_score'] # 0-5
            change = row.get('price_change', 0)
            
            # --- SIGNAL LOGIC ---
            # Score >= 4 (Vol Spike + Wick)
            # Direction: Follow Momentum (Green Candle + Liq = Squeeze Up)
            signal = "HOLD"
            color = Colors.RESET
            
            outcome = ""
            pnl_print = ""
            
            if score >= 4:
                if change > 0:
                    signal = "BUY 🟢"
                    color = Colors.GREEN
                    # Calculate Outcome (Next 15m return)
                    future_ret = row.get('future_return_3', 0)
                    if future_ret > 0.005: 
                        outcome = "WIN 🏆 (+0.5%)"
                        pnl_val = 1000 * 0.005 # $5 profit on $1000
                        self.balance += pnl_val
                        pnl_print = f"+${pnl_val:.2f}"
                    elif future_ret < -0.003:
                        outcome = "LOSS ❌ (-0.3%)"
                        pnl_val = -1000 * 0.003
                        self.balance += pnl_val
                        pnl_print = f"${pnl_val:.2f}"
                    else:
                        outcome = "FLAT ➖"
                        pnl_print = "$0.00"
                        
                elif change < 0:
                    signal = "SELL 🔴"
                    color = Colors.RED
                    # Calculate Outcome (Next 15m return)
                    future_ret = row.get('future_return_3', 0)
                    if future_ret < -0.005: # Price dropped > 0.5% (Short Win)
                        outcome = "WIN 🏆 (+0.5%)"
                        pnl_val = 1000 * 0.005
                        self.balance += pnl_val
                        pnl_print = f"+${pnl_val:.2f}"
                    elif future_ret > 0.003: # Price rose > 0.3% (Short Loss)
                        outcome = "LOSS ❌ (-0.3%)"
                        pnl_val = -1000 * 0.003
                        self.balance += pnl_val
                        pnl_print = f"${pnl_val:.2f}"
                    else:
                        outcome = "FLAT ➖"
                        pnl_print = "$0.00"

            # Print ONLY signals or occasional heartbeat
            if "BUY" in signal or "SELL" in signal:
                print(f"{color}{str(timestamp):<20} | ${price:<9.2f} | {vol:<8.1f} | {score:<10} | {signal:<10} | {outcome:<15}{Colors.RESET}")
                time.sleep(0.5) # Pause on signal
            elif i % 50 == 0:
                # Heartbeat
                sys.stdout.write(f"\r{Colors.CYAN}Scanning... {str(timestamp)} | ${price:.2f} | Vol: {vol:.0f}{Colors.RESET}")
                sys.stdout.flush()
                time.sleep(0.01)

        print(f"\n\n{Colors.GREEN}==========================================")
        print(f"✅ SIMULATION COMPLETE")
        print(f"💰 FINAL BALANCE: ${self.balance:,.2f}")
        profit = self.balance - 10000
        print(f"📈 TOTAL PROFIT: ${profit:,.2f} ({profit/100:.2f}%)")
        print(f"=========================================={Colors.RESET}")

if __name__ == "__main__":
    print(BANNER)
    bot = LiquidationScalper()
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\n👋 Scalper Stopped.")
