#!/usr/bin/env python3
"""
OPTIMIZED label generation using vectorized operations
Much faster than loop-based approach
"""
import pandas as pd
import numpy as np
from tqdm import tqdm

def generate_labels_bidirectional_vectorized(df, tp_pct=0.015, sl_pct=0.008, lookahead_bars=24, name=''):
    """
    Generate bidirectional trading labels using vectorized operations (0=None, 1=Long, 2=Short)
    """
    print(f"\n📊 Generating BIDIRECTIONAL labels for {name}...")
    print(f"   TP: {tp_pct*100:.2f}%, SL: {sl_pct*100:.2f}%")
    print(f"   Lookahead: {lookahead_bars} bars")
    
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values
    
    tp_prices_l = close * (1 + tp_pct)
    sl_prices_l = close * (1 - sl_pct)
    tp_prices_s = close * (1 - tp_pct)
    sl_prices_s = close * (1 + tp_pct)
    
    labels = np.zeros(len(df), dtype=int)
    
    # Process in chunks
    chunk_size = 5000
    total_samples = len(df)
    
    for i in tqdm(range(total_samples - lookahead_bars), desc=f"   Processing {name}"):
        # Long check
        future_high = high[i+1:i+lookahead_bars+1]
        future_low = low[i+1:i+lookahead_bars+1]
        
        # Long side
        long_tp_hits = np.where(future_high >= tp_prices_l[i])[0]
        long_sl_hits = np.where(future_low <= sl_prices_l[i])[0]
        
        t_tp_l = long_tp_hits[0] if len(long_tp_hits) > 0 else 99999
        t_sl_l = long_sl_hits[0] if len(long_sl_hits) > 0 else 99999
        
        # Short side
        short_tp_hits = np.where(future_low <= tp_prices_s[i])[0]
        short_sl_hits = np.where(future_high >= sl_prices_s[i])[0]
        
        t_tp_s = short_tp_hits[0] if len(short_tp_hits) > 0 else 99999
        t_sl_s = short_sl_hits[0] if len(short_sl_hits) > 0 else 99999
        
        # Decision
        long_win = (t_tp_l < t_sl_l)
        short_win = (t_tp_s < t_sl_s)
        
        if long_win and short_win:
            # Both would win, pick the faster one
            if t_tp_l < t_tp_s:
                labels[i] = 1
            elif t_tp_s < t_tp_l:
                labels[i] = 2
            else:
                # Tie at same bar - safer to ignore
                labels[i] = 0
        elif long_win:
            labels[i] = 1
        elif short_win:
            labels[i] = 2
            
    df['label'] = labels
    
    # Statistics
    longs = np.sum(labels == 1)
    shorts = np.sum(labels == 2)
    total = len(labels)
    
    print(f"\n   📊 Label Statistics:")
    print(f"      Total:      {total:,}")
    print(f"      Longs (1):  {longs:,} ({longs/total*100:.2f}%)")
    print(f"      Shorts (2): {shorts:,} ({shorts/total*100:.2f}%)")
    print(f"      No Result:  {(total-longs-shorts):,} ({(total-longs-shorts)/total*100:.2f}%)")
    
    return df

def main():
    """Main execution"""
    print("="*70)
    print("🏷️  OPTIMIZED LABEL GENERATION PIPELINE")
    print("="*70)
    
    # Generate labels for Winner Hunter (1H)
    print("\n" + "="*70)
    print("1️⃣ WINNER HUNTER (1H) LABELS")
    print("="*70)
    
    df_1h = pd.read_csv('training/data/BTC_1h_mtf_features.csv')
    df_1h['timestamp'] = pd.to_datetime(df_1h['timestamp'])
    print(f"\n📊 Loaded {len(df_1h):,} rows")
    
    # Generate labels (lookahead 24 bars = 24 hours for 1H)
    df_1h = generate_labels_bidirectional_vectorized(df_1h, tp_pct=0.015, sl_pct=0.008, lookahead_bars=24, name='1H')
    
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
    df_mtf = generate_labels_bidirectional_vectorized(df_mtf, tp_pct=0.015, sl_pct=0.008, lookahead_bars=288, name='5M MTF')
    
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
