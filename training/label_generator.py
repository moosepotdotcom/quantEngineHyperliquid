#!/usr/bin/env python3
"""
Generate trading labels for both Winner Hunter and MTF Scalper
Labels: 1 if TP hit before SL, 0 otherwise
"""
import pandas as pd
import numpy as np
from tqdm import tqdm

def generate_labels_bidirectional(df, tp_pct=0.015, sl_pct=0.008, lookahead_bars=24, name=''):
    """
    Generate bidirectional trading labels (0=None, 1=Long, 2=Short)
    
    Args:
        df: DataFrame with OHLC data
        tp_pct: Take profit percentage (1.5% = 0.015)
        sl_pct: Stop loss percentage (0.8% = 0.008)
        lookahead_bars: Maximum bars to look ahead
        name: Dataset name for logging
    
    Returns:
        DataFrame with 'label' column added
    """
    print(f"\n📊 Generating BIDIRECTIONAL labels for {name}...")
    print(f"   TP: {tp_pct*100:.2f}%, SL: {sl_pct*100:.2f}%")
    print(f"   Lookahead: {lookahead_bars} bars")
    
    labels = []
    longs = 0
    shorts = 0
    no_result = 0
    
    for i in tqdm(range(len(df)), desc=f"   Processing {name}"):
        if i >= len(df) - lookahead_bars:
            labels.append(0)
            no_result += 1
            continue
        
        entry_price = df.iloc[i]['close']
        
        # Targets
        tp_long = entry_price * (1 + tp_pct)
        sl_long = entry_price * (1 - sl_pct)
        
        tp_short = entry_price * (1 - tp_pct)
        sl_short = entry_price * (1 + sl_pct)
        
        found_label = 0
        
        # Look ahead
        for j in range(i + 1, min(i + lookahead_bars + 1, len(df))):
            high = df.iloc[j]['high']
            low = df.iloc[j]['low']
            
            # Check Long TP/SL
            long_tp_hit = (high >= tp_long)
            long_sl_hit = (low <= sl_long)
            
            # Check Short TP/SL
            short_tp_hit = (low <= tp_short)
            short_sl_hit = (high >= sl_short)
            
            # Note: We prioritize the first target hit in the timeframe.
            # If multiple targets hit in the same bar, it's safer to discard (label 0).
            
            # Priority logic:
            if long_tp_hit and not long_sl_hit:
                found_label = 1
                longs += 1
                break
            elif short_tp_hit and not short_sl_hit:
                found_label = 2
                shorts += 1
                break
            elif long_sl_hit or short_sl_hit:
                # One of the SLs hit first (or both TP/SL hit same bar)
                found_label = 0
                break
        
        labels.append(found_label)
        if found_label == 0:
            no_result += 1
            
    df['label'] = labels
    
    # Statistics
    total = len(labels)
    print(f"\n   📊 Label Statistics:")
    print(f"      Total:      {total:,}")
    print(f"      Longs (1):  {longs:,} ({longs/total*100:.2f}%)")
    print(f"      Shorts (2): {shorts:,} ({shorts/total*100:.2f}%)")
    print(f"      No Result:  {no_result:,} ({no_result/total*100:.2f}%)")
    
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
    
    df_1h = pd.read_csv('training/data/BTC_1h_mtf_features.csv')
    df_1h['timestamp'] = pd.to_datetime(df_1h['timestamp'])
    print(f"\n📊 Loaded {len(df_1h):,} rows")
    
    # Generate labels (lookahead 24 bars = 24 hours for 1H)
    df_1h = generate_labels_bidirectional(df_1h, tp_pct=0.015, sl_pct=0.008, lookahead_bars=24, name='1H')
    
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
    df_mtf = generate_labels_bidirectional(df_mtf, tp_pct=0.015, sl_pct=0.008, lookahead_bars=288, name='5M MTF')
    
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
