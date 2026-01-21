#!/usr/bin/env python3
"""
V9 Label Generator - Liquidation-Enhanced Strategy
Combines V8 logic with liquidation proxy signals
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def generate_v9_labels_with_liquidations(df, tp=0.015, sl=0.008):
    """
    Generate labels using liquidation signals
    
    Strategy:
    - Enter when liquidation event occurs in our direction
    - Ride the momentum from forced liquidations
    - Exit at TP/SL
    """
    
    print(f"🎯 Generating V9 Labels with Liquidation Signals")
    print(f"   TP: {tp*100}%, SL: {sl*100}%")
    print("="*70)
    
    labels = []
    
    for i in range(100, len(df) - 200):
        if i % 10000 == 0:
            print(f"   Processing {i}/{len(df)}...")
        
        row = df.iloc[i]
        future = df.iloc[i+1:i+201]
        
        if len(future) < 20:
            labels.append(3)  # Neutral
            continue
        
        entry_price = row['close']
        
        # Check for liquidation signals
        liq_score = row.get('liq_proxy_score', 0)
        liq_direction = row.get('liq_direction', 0)
        liq_cluster = row.get('liq_cluster_count', 0)
        
        # V9 ENHANCED LOGIC:
        # Use liquidation signals as BOOST, not requirement
        # This way we get more trades but prioritize liquidation setups
        
        is_bullish_setup = False
        is_bearish_setup = False
        
        cvd_1h = row.get('cvd_1h', 0)
        rsi_15m = row.get('rsi_15m', 50)
        ema_50 = row.get('ema_50_15m', entry_price)
        vol_surge = row.get('vol_surge', 1)
        
        # LONG Setup: Standard + liquidation boost
        if entry_price < ema_50 and cvd_1h > 0 and rsi_15m < 65:
            # Boost if liquidation detected
            if liq_score >= 3 or liq_direction == 1 or vol_surge > 2:
                is_bullish_setup = True
        
        # SHORT Setup: Standard + liquidation boost  
        elif entry_price > ema_50 and cvd_1h < 0 and rsi_15m > 35:
            # Boost if liquidation detected
            if liq_score >= 3 or liq_direction == -1 or vol_surge > 2:
                is_bearish_setup = True
        
        # Check outcome
        if is_bullish_setup:
            outcome = 'TIMEOUT'
            for _, candle in future.iterrows():
                if candle['high'] >= entry_price * (1 + tp):
                    outcome = 'WIN'
                    break
                if candle['low'] <= entry_price * (1 - sl):
                    outcome = 'LOSS'
                    break
            
            if outcome == 'WIN':
                labels.append(1)  # LONG
            else:
                labels.append(3)  # Neutral (bad setup)
        
        elif is_bearish_setup:
            outcome = 'TIMEOUT'
            for _, candle in future.iterrows():
                if candle['low'] <= entry_price * (1 - tp):
                    outcome = 'WIN'
                    break
                if candle['high'] >= entry_price * (1 + sl):
                    outcome = 'LOSS'
                    break
            
            if outcome == 'WIN':
                labels.append(2)  # SHORT
            else:
                labels.append(3)  # Neutral (bad setup)
        
        else:
            labels.append(3)  # Neutral (no setup)
    
    # Pad beginning
    labels = [3] * 100 + labels
    
    # Pad end
    while len(labels) < len(df):
        labels.append(3)
    
    return labels

def main():
    print("🚀 V9 Label Generation - Liquidation-Enhanced")
    print("="*70)
    
    # Load data with liquidation proxy AND enriched features
    df = pd.read_csv('../training/data/BTC_5m_2025_enriched_with_liquidations.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    print(f"✅ Loaded {len(df)} candles with liquidation features")
    
    # Generate labels
    labels = generate_v9_labels_with_liquidations(df, tp=0.015, sl=0.008)
    
    df['v9_label'] = labels
    
    # Statistics
    label_counts = pd.Series(labels).value_counts()
    total = len(labels)
    
    print(f"\n📊 Label Distribution:")
    print(f"   Neutral (3): {label_counts.get(3, 0):,} ({label_counts.get(3, 0)/total*100:.1f}%)")
    print(f"   Long (1):    {label_counts.get(1, 0):,} ({label_counts.get(1, 0)/total*100:.1f}%)")
    print(f"   Short (2):   {label_counts.get(2, 0):,} ({label_counts.get(2, 0)/total*100:.1f}%)")
    
    # Save
    output_file = '../training/data/BTC_5m_2025_v9_labeled.csv'
    df.to_csv(output_file, index=False)
    print(f"\n💾 Saved to {output_file}")
    
    # Show sample liquidation-based trades
    liq_trades = df[(df['v9_label'].isin([1, 2])) & (df['liq_proxy_score'] >= 4)]
    print(f"\n📋 Sample Liquidation-Based Trades ({len(liq_trades)} total):")
    print(liq_trades[['timestamp', 'close', 'v9_label', 'liq_proxy_score', 'liq_direction', 'liq_cluster_count']].head(20).to_string(index=False))

if __name__ == "__main__":
    main()
