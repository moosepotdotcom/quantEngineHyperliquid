#!/usr/bin/env python3
"""
Simulate trading with $53 starting capital, 50x leverage, 0.02 BTC lot size
"""
import pandas as pd
from datetime import datetime

print("=" * 70)
print("💰 TRADING SIMULATION: $53 Starting Capital")
print("=" * 70)
print()

# Parse trade log
trades = []
with open('LAST_WEEK_TRADES.md', 'r') as f:
    lines = f.readlines()

in_table = False
for line in lines:
    if '| Entry Time' in line:
        in_table = True
        continue
    if in_table and '|---' in line:
        continue
    if in_table and '|' in line and 'Total PnL' not in line:
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 13:
            try:
                entry_time = pd.to_datetime(parts[1])
                trade_type = parts[2]
                entry_price = float(parts[8])  # Entry Price column
                exit_price = float(parts[12])  # Exit Price column
                exit_reason = parts[13]  # Exit Reason
                pnl_pct = float(parts[14].replace('%', '').replace('+', ''))  # PnL%
                
                trades.append({
                    'time': entry_time,
                    'type': trade_type,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'exit_reason': exit_reason,
                    'pnl_pct': pnl_pct / 100  # Convert to decimal
                })
            except Exception as e:
                continue

df = pd.DataFrame(trades)

# Trading parameters
STARTING_CAPITAL = 53.0
LEVERAGE = 50
LOT_SIZE_BTC = 0.02

# Calculate effective position value (per trade)
# Using average BTC price from trades
avg_btc_price = df['entry_price'].mean()
POSITION_VALUE_USD = LOT_SIZE_BTC * avg_btc_price

print(f"📊 Trading Parameters:")
print(f"   Starting Capital: ${STARTING_CAPITAL:.2f}")
print(f"   Leverage: {LEVERAGE}x")
print(f"   Lot Size: {LOT_SIZE_BTC} BTC per trade")
print(f"   Avg BTC Price: ${avg_btc_price:,.2f}")
print(f"   Position Value: ${POSITION_VALUE_USD:,.2f} per trade")
print(f"   Margin Used: ${POSITION_VALUE_USD / LEVERAGE:,.2f} per trade")
print()

# Simulate trading
balance = STARTING_CAPITAL
equity_history = [STARTING_CAPITAL]
trade_history = []

liquidation_price = None
max_balance = STARTING_CAPITAL
max_drawdown = 0
win_count = 0
loss_count = 0

print("🔄 Simulating 182 Trades...")
print("-" * 70)

for idx, row in df.iterrows():
    entry_price = row['entry_price']
    pnl_pct = row['pnl_pct']
    
    # Calculate P&L in USD
    # P&L = Position Value × P&L%
    pnl_usd = POSITION_VALUE_USD * pnl_pct
    
    # Update balance
    new_balance = balance + pnl_usd
    
    # Track history
    trade_history.append({
        'trade_num': idx + 1,
        'time': row['time'],
        'entry_price': entry_price,
        'pnl_pct': pnl_pct * 100,
        'pnl_usd': pnl_usd,
        'balance_before': balance,
        'balance_after': new_balance
    })
    
    # Update stats
    if pnl_usd > 0:
        win_count += 1
    else:
        loss_count += 1
    
    balance = new_balance
    equity_history.append(balance)
    
    # Check for liquidation (balance falls below margin requirement)
    margin_requirement = POSITION_VALUE_USD / LEVERAGE
    if balance < margin_requirement:
        print(f"\n⚠️  LIQUIDATION at Trade #{idx + 1}")
        print(f"   Balance: ${balance:.2f}")
        print(f"   Margin Required: ${margin_requirement:.2f}")
        liquidation_price = idx + 1
        break
    
    # Track max balance and drawdown
    if balance > max_balance:
        max_balance = balance
    
    current_drawdown = ((max_balance - balance) / max_balance) * 100
    if current_drawdown > max_drawdown:
        max_drawdown = current_drawdown

# Results
print()
print("=" * 70)
print("📊 SIMULATION RESULTS")
print("=" * 70)

if liquidation_price:
    print(f"\n❌ ACCOUNT LIQUIDATED at Trade #{liquidation_price}")
    print(f"   Final Balance: ${balance:.2f}")
    print(f"   Trades Completed: {liquidation_price}/{len(df)}")
else:
    print(f"\n✅ SIMULATION COMPLETED")
    print(f"   Total Trades: {len(df)}")
    print(f"   Wins: {win_count} ({win_count/len(df)*100:.1f}%)")
    print(f"   Losses: {loss_count} ({loss_count/len(df)*100:.1f}%)")

print(f"\n💰 Capital Growth:")
print(f"   Starting: ${STARTING_CAPITAL:.2f}")
print(f"   Ending: ${balance:.2f}")
print(f"   Profit: ${balance - STARTING_CAPITAL:+.2f}")
print(f"   ROI: {((balance / STARTING_CAPITAL) - 1) * 100:+.1f}%")

print(f"\n📈 Risk Metrics:")
print(f"   Max Balance: ${max_balance:.2f}")
print(f"   Max Drawdown: {max_drawdown:.2f}%")

# Show first 10 and last 10 trades
print(f"\n📋 Trade Sample (First 10):")
df_history = pd.DataFrame(trade_history)
print(df_history[['trade_num', 'pnl_usd', 'balance_after']].head(10).to_string(index=False))

if not liquidation_price and len(df_history) > 10:
    print(f"\n📋 Trade Sample (Last 10):")
    print(df_history[['trade_num', 'pnl_usd', 'balance_after']].tail(10).to_string(index=False))

# Calculate what happens if we compounded (variable position sizing)
print(f"\n" + "=" * 70)
print("🔄 COMPOUND MODE (Variable Position Size)")
print("=" * 70)

balance_compound = STARTING_CAPITAL
max_balance_compound = STARTING_CAPITAL

for idx, row in df.iterrows():
    pnl_pct = row['pnl_pct']
    
    # Recalculate position size based on current balance
    current_position_value = (balance_compound * LEVERAGE) * (LOT_SIZE_BTC * avg_btc_price / POSITION_VALUE_USD)
    
    # P&L
    pnl_usd = current_position_value * pnl_pct
    
    balance_compound += pnl_usd
    
    if balance_compound > max_balance_compound:
        max_balance_compound = balance_compound
    
    # Check liquidation
    margin_req = current_position_value / LEVERAGE
    if balance_compound < margin_req:
        print(f"⚠️  Would liquidate at Trade #{idx + 1}")
        print(f"   Balance: ${balance_compound:.2f}")
        break

if balance_compound > 0:
    print(f"\n💰 Compound Results:")
    print(f"   Starting: ${STARTING_CAPITAL:.2f}")
    print(f"   Ending: ${balance_compound:.2f}")
    print(f"   Profit: ${balance_compound - STARTING_CAPITAL:+.2f}")
    print(f"   ROI: {((balance_compound / STARTING_CAPITAL) - 1) * 100:+.1f}%")

print()
