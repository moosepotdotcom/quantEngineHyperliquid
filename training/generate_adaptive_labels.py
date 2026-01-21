#!/usr/bin/env python3
"""
ADAPTIVE LABEL GENERATOR
Generates optimal TP/SL labels for each candle based on forward simulation
Optimized for ONE position at a time (capital efficiency)
"""

import sys
sys.path.insert(0, '/Users/alifiyaa/Downloads/quantEngineHyperliquid/EXPORT')

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("\n" + "="*70)
print("🚀 ADAPTIVE LABEL GENERATOR")
print("Optimizing for: ONE position at a time")
print("="*70)

# Load data
print("\n📥 Loading historical data...")
df = pd.read_csv('/Users/alifiyaa/Downloads/quantEngineHyperliquid/EXPORT/btc_5m_history_final.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"✅ Loaded {len(df):,} candles")
print(f"   Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"   Days: {(df['timestamp'].max() - df['timestamp'].min()).days}")

# Test different TP/SL combinations
tp_options = [0.003, 0.005, 0.008, 0.010, 0.015, 0.020]  # 0.3% to 2.0%
sl_options = [0.002, 0.003, 0.005, 0.008]  # 0.2% to 0.8%

print(f"\n🔬 Testing {len(tp_options)} TP × {len(sl_options)} SL = {len(tp_options)*len(sl_options)} combinations")

# Generate labels
print("\n🏷️  Generating adaptive labels...")

labels = []
optimal_tps = []
optimal_sls = []
hold_times = []
win_probs = []

lookahead = 288  # 24 hours on 5m candles

for i in range(len(df)):
    if i % 500 == 0:
        print(f"   Progress: {i}/{len(df)} ({i/len(df)*100:.1f}%)", end='\r')
    
    # Need lookahead
    if i >= len(df) - lookahead:
        labels.append(0)
        optimal_tps.append(0.01)
        optimal_sls.append(0.005)
        hold_times.append(0)
        win_probs.append(0)
        continue
    
    current_price = df.iloc[i]['close']
    future = df.iloc[i+1:i+lookahead+1]
    
    best_score = -999
    best_tp = 0.01
    best_sl = 0.005
    best_label = 0
    best_hold = 0
    best_win_prob = 0
    
    # Test LONG
    for tp_pct in tp_options:
        for sl_pct in sl_options:
            tp_price = current_price * (1 + tp_pct)
            sl_price = current_price * (1 - sl_pct)
            
            outcome = None
            hold_candles = 0
            
            for j, (_, row) in enumerate(future.iterrows()):
                if row['high'] >= tp_price:
                    outcome = 'WIN'
                    hold_candles = j + 1
                    break
                elif row['low'] <= sl_price:
                    outcome = 'LOSS'
                    hold_candles = j + 1
                    break
            
            if outcome == 'WIN':
                # Score = Profit / Time (capital efficiency!)
                profit = tp_pct
                time_hours = hold_candles * 5 / 60
                if time_hours == 0: time_hours = 0.1
                
                score = profit / time_hours  # Profit per hour
                
                if score > best_score:
                    best_score = score
                    best_tp = tp_pct
                    best_sl = sl_pct
                    best_label = 1  # LONG
                    best_hold = time_hours
                    best_win_prob = 1.0
    
    # Test SHORT
    for tp_pct in tp_options:
        for sl_pct in sl_options:
            tp_price = current_price * (1 - tp_pct)
            sl_price = current_price * (1 + sl_pct)
            
            outcome = None
            hold_candles = 0
            
            for j, (_, row) in enumerate(future.iterrows()):
                if row['low'] <= tp_price:
                    outcome = 'WIN'
                    hold_candles = j + 1
                    break
                elif row['high'] >= sl_price:
                    outcome = 'LOSS'
                    hold_candles = j + 1
                    break
            
            if outcome == 'WIN':
                profit = tp_pct
                time_hours = hold_candles * 5 / 60
                if time_hours == 0: time_hours = 0.1
                
                score = profit / time_hours
                
                if score > best_score:
                    best_score = score
                    best_tp = tp_pct
                    best_sl = sl_pct
                    best_label = 2  # SHORT
                    best_hold = time_hours
                    best_win_prob = 1.0
    
    labels.append(best_label)
    optimal_tps.append(best_tp)
    optimal_sls.append(best_sl)
    hold_times.append(best_hold)
    win_probs.append(best_win_prob)

# Add to dataframe
df['label'] = labels
df['optimal_tp'] = optimal_tps
df['optimal_sl'] = optimal_sls
df['expected_hold_hours'] = hold_times
df['win_probability'] = win_probs

# Statistics
print(f"\n\n✅ Labels generated!")
print(f"\n📊 Label Distribution:")
longs = len(df[df['label'] == 1])
shorts = len(df[df['label'] == 2])
neutrals = len(df[df['label'] == 0])
total = len(df)

print(f"   LONG: {longs:,} ({longs/total*100:.1f}%)")
print(f"   SHORT: {shorts:,} ({shorts/total*100:.1f}%)")
print(f"   NEUTRAL: {neutrals:,} ({neutrals/total*100:.1f}%)")
print(f"   Tradeable: {longs+shorts:,} ({(longs+shorts)/total*100:.1f}%)")

# Optimal target statistics
tradeable = df[df['label'] != 0]
if len(tradeable) > 0:
    print(f"\n📈 Optimal Targets (for tradeable signals):")
    print(f"   Avg TP: {tradeable['optimal_tp'].mean()*100:.2f}%")
    print(f"   Avg SL: {tradeable['optimal_sl'].mean()*100:.2f}%")
    print(f"   Avg Hold: {tradeable['expected_hold_hours'].mean():.1f} hours")
    print(f"   Avg Win Prob: {tradeable['win_probability'].mean()*100:.1f}%")

# Save
output_file = '/Users/alifiyaa/Downloads/quantEngineHyperliquid/training/data/adaptive_labels.csv'
df.to_csv(output_file, index=False)
print(f"\n💾 Saved to: {output_file}")
print(f"   Size: {len(df):,} samples")

print("\n✅ PHASE 1 COMPLETE!")
print("   Next: Add indicators and train models")
