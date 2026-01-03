#!/usr/bin/env python3
"""
Generate trading labels for both Winner Hunter and MTF Scalper
Labels: 1 if TP hit before SL, 0 otherwise
"""
import pandas as pd
import numpy as np
from tqdm import tqdm

def generate_labels(df, tp_pct=0.015, sl_pct=0.008, lookahead_bars=24, name=''):
    """
    Generate trading labels
    
    Args:
        df: DataFrame with OHLC data
        tp_pct: Take profit percentage (1.5% = 0.015)
        sl_pct: Stop loss percentage (0.8% = 0.008)
        lookahead_bars: Maximum bars to look ahead
        name: Dataset name for logging
    
    Returns:
        DataFrame with 'label' column added
    """
    print(f"\n📊 Generating labels for {name}...")
    print(f"   TP: {tp_pct*100:.1f}%, SL: {sl_pct*100:.1f}%")
    print(f"   Lookahead: {lookahead_bars} bars")
    
    labels = []
    wins = 0
    losses = 0
    no_result = 0
    
    for i in tqdm(range(len(df)), desc=f"   Processing {name}"):
        if i >= len(df) - lookahead_bars:
            # Not enough future data
            labels.append(0)
            no_result += 1
            continue
        
        entry_price = df.iloc[i]['close']
        tp_price = entry_price * (1 + tp_pct)
        sl_price = entry_price * (1 - sl_pct)
        
        # Look ahead to see if TP or SL is hit
        hit_tp = False
        hit_sl = False
        
        for j in range(i + 1, min(i + lookahead_bars + 1, len(df))):
            high = df.iloc[j]['high']
            low = df.iloc[j]['low']
            
            # Check if TP hit
            if high >= tp_price:
                hit_tp = True
                break
            
            # Check if SL hit
            if low <= sl_price:
                hit_sl = True
                break
        
        # Label: 1 if TP hit before SL, 0 otherwise
        if hit_tp:
            labels.append(1)
            wins += 1
        else:
            labels.append(0)
            if hit_sl:
                losses += 1
            else:
                no_result += 1
    
    df['label'] = labels
    
    # Statistics
    total = len(labels)
    win_rate = (wins / total) * 100 if total > 0 else 0
    
    print(f"\n   📊 Label Statistics:")
    print(f"      Total:      {total:,}")
    print(f"      Wins (1):   {wins:,} ({wins/total*100:.2f}%)")
    print(f"      Losses (0): {losses:,} ({losses/total*100:.2f}%)")
    print(f"      No Result:  {no_result:,} ({no_result/total*100:.2f}%)")
    print(f"      Win Rate:   {win_rate:.2f}%")
    
    return df

def main():
    """Main execution"""
    print("="*70)
    print("🏷️  LABEL GENERATION PIPELINE")
    print("="*70)
    
    # Generate labels for Winner Hunter (1H)
    print("\n" + "="*70)
    print("1️⃣ WINNER HUNTER (1H) LABELS")
    print("="*70)
    
    df_1h = pd.read_csv('training/data/BTC_1h_features.csv')
    df_1h['timestamp'] = pd.to_datetime(df_1h['timestamp'])
    print(f"\n📊 Loaded {len(df_1h):,} rows")
    
    # Generate labels (lookahead 24 bars = 24 hours for 1H)
    df_1h = generate_labels(df_1h, tp_pct=0.015, sl_pct=0.008, lookahead_bars=24, name='1H')
    
    # Save
    output_file = 'training/data/BTC_1h_labeled.csv'
    df_1h.to_csv(output_file, index=False)
    print(f"\n✅ Saved to {output_file}")
    
    # Generate labels for MTF Scalper (5M)
    print("\n" + "="*70)
    print("2️⃣ MTF SCALPER (5M) LABELS")
    print("="*70)
    
    df_mtf = pd.read_csv('training/data/BTC_5m_mtf_features.csv')
    df_mtf['timestamp'] = pd.to_datetime(df_mtf['timestamp'])
    print(f"\n📊 Loaded {len(df_mtf):,} rows")
    
    # Generate labels (lookahead 288 bars = 24 hours for 5M)
    df_mtf = generate_labels(df_mtf, tp_pct=0.015, sl_pct=0.008, lookahead_bars=288, name='5M MTF')
    
    # Save
    output_file = 'training/data/BTC_5m_mtf_labeled.csv'
    df_mtf.to_csv(output_file, index=False)
    print(f"\n✅ Saved to {output_file}")
    
    # Summary
    print("\n" + "="*70)
    print("📊 LABEL GENERATION SUMMARY")
    print("="*70)
    print(f"1H labeled:  {len(df_1h):,} rows")
    print(f"5M labeled:  {len(df_mtf):,} rows")
    print("\n✅ All labels generated successfully!")
    print("="*70)

if __name__ == '__main__':
    main()
