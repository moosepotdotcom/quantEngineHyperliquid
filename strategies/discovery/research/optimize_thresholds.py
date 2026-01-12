import pandas as pd
import re
import numpy as np

def parse_trade_log(filepath):
    trades = []
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    # Regex to parse the markdown table
    # | 2026-01-02 00:00 | LONG | 0.47 | 88698 | ... | +1.5% |
    pattern = re.compile(r"\|\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s+\|\s+(\w+)\s+\|\s+([\d\.]+)\s+\|\s+([\d\.]+)\s+\|\s+([\d\.]+)\s+\|\s+([\d\.]+)\s+\|\s+([\d\.]+)\s+\|\s+([\d\.]+)\s+\|\s+(\w+)\s+\|\s+([+\-\d\.]+)%")
    
    # Headers usually: Entry Time, Type, Conf, Entry, TP, SL, Exit Time, Exit Price, Reason, PnL
    # But checking the file format from previous turns:
    # | Entry Time | Type | Conf | Price | TP | SL | Exit Time | Exit Price | Reason | PnL |
    
    for line in lines:
        # Simple split by | might be easier/robuster than regex if format varies slightly
        if "|" not in line or "---" in line or "Entry Time" in line:
            continue
            
        parts = [p.strip() for p in line.split('|')]
        if len(parts) < 10:
            continue
            
        try:
            # parts[0] is empty string (before first |)
            entry_time = parts[1]
            trade_type = parts[2]
            conf = float(parts[3].replace('%', ''))
            # If conf is like "0.47", it might be 0.47. If "47.1%", parse accordingly.
            # In previous turn it was "0.47". Let's assume raw float.
            if conf > 1.0: conf /= 100.0
            
            entry_price = float(parts[4])
            exit_price = float(parts[7])
            pnl_pct = float(parts[9].replace('%', '').replace('+', ''))
            
            trades.append({
                'time': entry_time,
                'type': trade_type,
                'conf': conf,
                'entry': entry_price,
                'exit': exit_price,
                'pnl_pct': pnl_pct,
                'points': (exit_price - entry_price) if trade_type == 'LONG' else (entry_price - exit_price)
            })
        except ValueError:
            continue
            
    return pd.DataFrame(trades)

def optimize(df):
    print("📊 OPTIMIZATION REPORT")
    print("=" * 60)
    print(f"{'Threshold':<10} {'Trades/Day':<12} {'Win Rate':<10} {'Total Pts':<12} {'Avg Pts/Day':<12} {'Accuracy'}")
    print("-" * 60)
    
    # Calculate days covered
    df['dt'] = pd.to_datetime(df['time'])
    days = (df['dt'].max() - df['dt'].min()).total_seconds() / 86400
    if days < 1: days = 1
    
    # Iterate thresholds
    best_thresh = 0.45
    target_found = False
    
    for thresh in np.arange(0.45, 0.85, 0.01):
        subset = df[df['conf'] >= thresh]
        if len(subset) == 0:
            break
            
        wins = len(subset[subset['pnl_pct'] > 0])
        total = len(subset)
        wr = (wins / total) * 100
        
        trades_per_day = total / days
        total_points = subset['points'].sum()
        daily_points = total_points / days
        
        print(f"{thresh:.2f}{' ':<6} {trades_per_day:<12.1f} {wr:<10.1f}% {total_points:<12.0f} {daily_points:<12.0f} {wins}/{total}")
        
        # Check targets (99% WR, 10-15 trades/day)
        if wr >= 98.5 and 8 <= trades_per_day <= 20:
             print(f"   🎯 MATCH FOUND! Threshold {thresh:.2f}")
             
    print("-" * 60)
    
    # Current stats (0.45)
    total_pts_now = df['points'].sum()
    avg_pts_now = total_pts_now / days
    print(f"\n📈 CURRENT STATS (0.45 Threshold):")
    print(f"   Avg Points Per Day: {avg_pts_now:,.0f} points")
    print(f"   Avg Points Per Trade: {df['points'].mean():.0f} points")
    print(f"   Total Trades: {len(df)}")

if __name__ == "__main__":
    df = parse_trade_log('ULTIMATE_TRADES.md')
    if len(df) > 0:
        optimize(df)
    else:
        print("❌ No trades found in log file.")
