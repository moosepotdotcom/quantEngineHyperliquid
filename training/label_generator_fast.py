#!/usr/bin/env python3
"""
OPTIMIZED label generation using vectorized operations
Much faster than loop-based approach
"""
import pandas as pd
import numpy as np

def generate_labels_vectorized(df, tp_pct=0.015, sl_pct=0.008, lookahead_bars=24, name=''):
    """
    Generate trading labels using vectorized operations (FAST!)
    
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
    print(f"   Using VECTORIZED approach for speed...")
    
    # Convert to numpy arrays for speed
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values
    
    # Calculate TP and SL prices
    tp_prices = close * (1 + tp_pct)
    sl_prices = close * (1 - sl_pct)
    
    # Initialize labels
    labels = np.zeros(len(df), dtype=int)
    
    # Process in chunks for memory efficiency
    chunk_size = 10000
    total_chunks = (len(df) + chunk_size - 1) // chunk_size
    
    print(f"   Processing {len(df):,} rows in {total_chunks} chunks...")
    
    for chunk_idx in range(total_chunks):
        start_idx = chunk_idx * chunk_size
        end_idx = min(start_idx + chunk_size, len(df))
        
        for i in range(start_idx, end_idx):
            if i >= len(df) - lookahead_bars:
                # Not enough future data
                continue
            
            # Get future bars
            future_high = high[i+1:min(i+lookahead_bars+1, len(df))]
            future_low = low[i+1:min(i+lookahead_bars+1, len(df))]
            
            # Check if TP hit
            tp_hit = np.any(future_high >= tp_prices[i])
            
            if tp_hit:
                # Find first bar where TP hit
                tp_bar = np.argmax(future_high >= tp_prices[i])
                
                # Check if SL hit before TP
                sl_hit_before = np.any(future_low[:tp_bar+1] <= sl_prices[i])
                
                if not sl_hit_before:
                    labels[i] = 1
        
        # Progress
        progress = ((chunk_idx + 1) / total_chunks) * 100
        print(f"   Progress: {progress:.1f}%", end='\r')
    
    print(f"\n   ✅ Completed!")
    
    df['label'] = labels
    
    # Statistics
    wins = np.sum(labels == 1)
    losses = np.sum(labels == 0)
    total = len(labels)
    win_rate = (wins / total) * 100 if total > 0 else 0
    
    print(f"\n   📊 Label Statistics:")
    print(f"      Total:      {total:,}")
    print(f"      Wins (1):   {wins:,} ({wins/total*100:.2f}%)")
    print(f"      Losses (0): {losses:,} ({losses/total*100:.2f}%)")
    print(f"      Win Rate:   {win_rate:.2f}%")
    
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
    
    df_1h = pd.read_csv('training/data/BTC_1h_features.csv')
    df_1h['timestamp'] = pd.to_datetime(df_1h['timestamp'])
    print(f"\n📊 Loaded {len(df_1h):,} rows")
    
    # Generate labels (lookahead 24 bars = 24 hours for 1H)
    df_1h = generate_labels_vectorized(df_1h, tp_pct=0.015, sl_pct=0.008, lookahead_bars=24, name='1H')
    
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
    df_mtf = generate_labels_vectorized(df_mtf, tp_pct=0.015, sl_pct=0.008, lookahead_bars=288, name='5M MTF')
    
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
