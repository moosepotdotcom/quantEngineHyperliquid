#!/usr/bin/env python3
"""
Financial Simulation: The "Money Squeeze"
-----------------------------------------
Starting Balance: $53
Leverage: 27x
Start Date: Jan 2, 2026

Strategy:
- Full Compounding: Allocate 95% of Balance * Leverage per trade.
- 0.02 Lots? User said "0.02 lots" which might mean fixed size. 
- Scenario A: Fixed $2000 Position (approx 0.02 BTC)
- Scenario B: Full Compounding (Aggressive)

We will simulate both.
"""

import pandas as pd
import numpy as np

CSV_FILE = 'portfolio_trades.csv'
START_CAPITAL = 53.0
LEVERAGE = 27.0
FEE_PCT = 0.00035

def run_simulation():
    try:
        df = pd.read_csv(CSV_FILE)
    except:
        print("❌ CSV not found.")
        return

    print(f"💰 Starting Simulation | Capital: ${START_CAPITAL} | Lev: {LEVERAGE}x")
    print("-" * 60)

    # --- Scenario A: Compounding (Max Growth) ---
    balance = START_CAPITAL
    equity_curve = [balance]
    points_captured = 0
    
    print("\n🚀 SCENARIO A: Full Compounding (95% Margin Usage)")
    
    for i, row in df.iterrows():
        # Raw PnL (Price movement %)
        # We need to reconstruct raw price move because 'pnl' in CSV includes fees and is unleashing?
        # Use simple approach: PnL % in CSV is unleveraged * 1? 
        # Wait, backtest_portfolio_universal.py calculates:
        # pnl = (exit - entry) / entry
        # pnl -= fees
        # So 'pnl' in CSV is UNLEVERAGED NET PnL.
        
        raw_pnl = row['pnl']
        
        # Position Size = Balance * Leverage * 0.95
        position_size = balance * LEVERAGE * 0.95
        
        # Profit = Position Size * Raw PnL
        profit = position_size * raw_pnl
        
        balance += profit
        equity_curve.append(balance)
        
        # Stop if blown
        if balance <= 5:
            print(f"   💀 Account Blown at trade {i}")
            break
            
    roi = (balance - START_CAPITAL) / START_CAPITAL * 100
    print(f"   Final Balance: ${balance:.2f}")
    print(f"   Total ROI:     {roi:.2f}%")
    print(f"   Multiplier:    {balance/START_CAPITAL:.1f}x")

    # --- Scenario B: "0.02 Lots" (Fixed ~$1900 Position) ---
    balance_b = START_CAPITAL
    print("\n🛡️ SCENARIO B: Fixed Size ($1900 / ~0.02 BTC equivalent)")
    
    fixed_size = 1900.0 # Approx 0.02 BTC at $95k
    # Check if we can afford it? $53 * 27 = $1431.
    # We can't afford $1900 initially.
    # Let's use Max Size ($1400)
    fixed_size = 1400.0
    
    for i, row in df.iterrows():
        raw_pnl = row['pnl']
        profit = fixed_size * raw_pnl
        balance_b += profit
        
    roi_b = (balance_b - START_CAPITAL) / START_CAPITAL * 100
    print(f"   Final Balance: ${balance_b:.2f}")
    print(f"   Total ROI:     {roi_b:.2f}%")

if __name__ == "__main__":
    run_simulation()
