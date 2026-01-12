#!/usr/bin/env python3
"""
Calculate average hold time from trade log
"""
import pandas as pd
from datetime import datetime

# Read the markdown file
with open('LAST_WEEK_TRADES.md', 'r') as f:
    lines = f.readlines()

# Find the table
trades = []
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
                exit_time = pd.to_datetime(parts[11])
                hold_time = exit_time - entry_time
                trades.append({
                    'entry': entry_time,
                    'exit': exit_time,
                    'hold_hours': hold_time.total_seconds() / 3600,
                    'exit_reason': parts[12]
                })
            except:
                continue

df = pd.DataFrame(trades)

print("📊 TRADE HOLD TIME ANALYSIS")
print("=" * 60)
print(f"Total Trades: {len(df)}")
print(f"\nAverage Hold Time: {df['hold_hours'].mean():.2f} hours")
print(f"Median Hold Time: {df['hold_hours'].median():.2f} hours")
print(f"Min Hold Time: {df['hold_hours'].min():.2f} hours")
print(f"Max Hold Time: {df['hold_hours'].max():.2f} hours")

print(f"\n📈 By Exit Reason:")
print(df.groupby('exit_reason')['hold_hours'].agg(['mean', 'median', 'count']))

print(f"\n📊 Distribution:")
bins = [0, 1, 3, 6, 12, 24, 100]
labels = ['<1h', '1-3h', '3-6h', '6-12h', '12-24h', '>24h']
df['bucket'] = pd.cut(df['hold_hours'], bins=bins, labels=labels)
print(df['bucket'].value_counts().sort_index())
