"""
PHASE 1 SCALPING TEST - Using Cached Data
Tests different TP/SL combinations to find optimal scalping targets
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Load cached data
print("\n🚀 PHASE 1: SCALPING TARGET OPTIMIZATION")
print("="*70)
print("Loading cached data...")

df_5m = pd.read_csv('/Users/alifiyaa/Downloads/quantEngineHyperliquid/EXPORT/btc_5m_history_final.csv')
df_5m['timestamp'] = pd.to_datetime(df_5m['timestamp'])
df_5m.set_index('timestamp', inplace=True)

print(f"✅ Loaded {len(df_5m)} candles")
print(f"   Period: {df_5m.index.min()} to {df_5m.index.max()}")

# Filter to Jan 2-11
start_date = "2026-01-02"
end_date = "2026-01-11 23:59:59"
mask = (df_5m.index >= start_date) & (df_5m.index <= end_date)
df_test = df_5m[mask].copy()

print(f"   Test period: {len(df_test)} candles (Jan 2-11)")

def simulate_trades(df, tp_pct, sl_pct, signal_times):
    """Simulate trades with specific TP/SL"""
    trades = []
    
    for signal_time in signal_times:
        # Find entry candle
        entry_idx = df.index.get_indexer([signal_time], method='nearest')[0]
        entry_price = df.iloc[entry_idx]['close']
        
        # Calculate TP/SL
        tp_price = entry_price * (1 + tp_pct)
        sl_price = entry_price * (1 - sl_pct)
        
        # Look ahead for TP/SL
        future = df.iloc[entry_idx+1:]
        
        outcome = None
        exit_time = None
        exit_price = None
        
        for i, (ts, row) in enumerate(future.iterrows()):
            # Check TP
            if row['high'] >= tp_price:
                outcome = 'WIN'
                exit_time = ts
                exit_price = tp_price
                break
            
            # Check SL
            if row['low'] <= sl_price:
                outcome = 'LOSS'
                exit_time = ts
                exit_price = sl_price
                break
            
            # Max 24 hours
            if i >= 288:  # 24h on 5m candles
                outcome = 'EXPIRED'
                exit_time = ts
                exit_price = row['close']
                break
        
        if outcome:
            hold_hours = (exit_time - signal_time).total_seconds() / 3600
            trades.append({
                'entry_time': signal_time,
                'exit_time': exit_time,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'outcome': outcome,
                'hold_hours': hold_hours
            })
    
    return trades

# Known signal times from previous backtests (with NO ATR penalty)
signal_times = [
    pd.Timestamp('2026-01-02 01:20:00'),
    pd.Timestamp('2026-01-02 06:05:00'),
    pd.Timestamp('2026-01-03 01:25:00'),
    pd.Timestamp('2026-01-03 07:10:00'),
    pd.Timestamp('2026-01-05 07:50:00'),
    pd.Timestamp('2026-01-07 16:00:00'),
    pd.Timestamp('2026-01-08 05:00:00'),
]

print(f"\n📊 Testing {len(signal_times)} known signals with different TP/SL targets...")
print("="*70)

# Test configurations
configs = [
    (0.015, 0.008, "Current (Swing)"),
    (0.010, 0.005, "Medium"),
    (0.008, 0.004, "Balanced"),
    (0.005, 0.003, "Scalping"),
    (0.003, 0.002, "Ultra Scalp"),
]

results = []

for tp_pct, sl_pct, name in configs:
    print(f"\n🧪 Testing: {name} (TP: {tp_pct*100:.1f}% | SL: {sl_pct*100:.1f}%)")
    
    trades = simulate_trades(df_test, tp_pct, sl_pct, signal_times)
    
    wins = len([t for t in trades if t['outcome'] == 'WIN'])
    losses = len([t for t in trades if t['outcome'] == 'LOSS'])
    expired = len([t for t in trades if t['outcome'] == 'EXPIRED'])
    total = len(trades)
    
    if total > 0:
        win_rate = (wins / total) * 100
        avg_hold = sum([t['hold_hours'] for t in trades]) / total
        
        # Calculate P&L
        capital = 53
        leverage = 27
        buying_power = capital * leverage
        
        pnl_per_win = buying_power * tp_pct
        pnl_per_loss = buying_power * sl_pct
        total_pnl = (wins * pnl_per_win) - (losses * pnl_per_loss)
        final_balance = capital + total_pnl
        roi = (total_pnl / capital) * 100
        
        print(f"   Trades: {total} | Wins: {wins} | Losses: {losses} | Expired: {expired}")
        print(f"   Win Rate: {win_rate:.1f}%")
        print(f"   Avg Hold: {avg_hold:.1f} hours")
        print(f"   P&L: ${total_pnl:+.2f} | ROI: {roi:+.1f}%")
        
        results.append({
            'name': name,
            'tp': tp_pct,
            'sl': sl_pct,
            'total': total,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'avg_hold': avg_hold,
            'pnl': total_pnl,
            'roi': roi
        })

# Print comparison
print("\n" + "="*70)
print("📊 COMPARISON TABLE")
print("="*70)
print(f"{'Config':<15} {'Trades':<8} {'WR%':<8} {'Hold(h)':<10} {'P&L':<12} {'ROI%':<10}")
print("-"*70)

for r in results:
    print(f"{r['name']:<15} {r['total']:<8} {r['win_rate']:<8.1f} {r['avg_hold']:<10.1f} ${r['pnl']:<11.2f} {r['roi']:<10.1f}")

print("="*70)

# Find best
best_roi = max(results, key=lambda x: x['roi'])
fastest = min(results, key=lambda x: x['avg_hold'])

print(f"\n🏆 BEST ROI: {best_roi['name']} ({best_roi['roi']:+.1f}%)")
print(f"⚡ FASTEST: {fastest['name']} ({fastest['avg_hold']:.1f}h avg hold)")

print("\n💡 RECOMMENDATION:")
if best_roi['name'] == fastest['name']:
    print(f"   Use {best_roi['name']} - Best ROI AND fastest exits!")
else:
    print(f"   {best_roi['name']} for max profit ({best_roi['roi']:+.1f}%)")
    print(f"   {fastest['name']} for max speed ({fastest['avg_hold']:.1f}h holds)")

print("\n✅ Phase 1 Complete!")
print("   Next: Phase 2 - Retrain model with optimal targets")
