#!/usr/bin/env python3
"""
Liquidation Proxy Generator
Since direct liquidation APIs are deprecated, we'll create a proxy using:
1. Volume spikes + CVD divergence
2. Large price wicks (liquidation cascades)
3. Funding rate extremes
"""

import pandas as pd
import numpy as np

def create_liquidation_proxy(df):
    """
    Create liquidation proxy features from OHLCV data
    
    Theory:
    - Liquidations cause volume spikes
    - Liquidations create long wicks (stop hunts)
    - Liquidations align with CVD spikes
    """
    
    df = df.copy()
    
    # 1. Volume Surge (potential liquidation event)
    df['vol_ma_20'] = df['volume'].rolling(20).mean()
    df['vol_surge'] = df['volume'] / df['vol_ma_20']
    df['is_vol_spike'] = (df['vol_surge'] > 3.0).astype(int)  # 3x average volume
    
    # 2. Wick Analysis (liquidation cascades create long wicks)
    df['body'] = abs(df['close'] - df['open'])
    df['upper_wick'] = df['high'] - df[['open', 'close']].max(axis=1)
    df['lower_wick'] = df[['open', 'close']].min(axis=1) - df['low']
    df['total_wick'] = df['upper_wick'] + df['lower_wick']
    
    # Wick ratio (wick vs body)
    df['wick_ratio'] = df['total_wick'] / (df['body'] + 0.0001)
    df['is_long_wick'] = (df['wick_ratio'] > 2.0).astype(int)  # Wick 2x body
    
    # 3. Price Reversal (liquidation causes sharp reversal)
    df['price_change'] = df['close'].pct_change()
    df['is_sharp_move'] = (abs(df['price_change']) > 0.02).astype(int)  # 2% move
    
    # 4. Liquidation Proxy Score
    # Combine: volume spike + long wick + sharp move = likely liquidation
    df['liq_proxy_score'] = (
        df['is_vol_spike'] * 3 +  # Volume is strongest signal
        df['is_long_wick'] * 2 +   # Wicks indicate stop hunts
        df['is_sharp_move'] * 1    # Sharp moves confirm
    )
    
    # 5. Liquidation Direction (which side got liquidated?)
    # If price moves up sharply with volume = shorts liquidated
    # If price moves down sharply with volume = longs liquidated
    df['liq_direction'] = 0
    df.loc[(df['price_change'] > 0.01) & (df['is_vol_spike'] == 1), 'liq_direction'] = 1  # Shorts liquidated
    df.loc[(df['price_change'] < -0.01) & (df['is_vol_spike'] == 1), 'liq_direction'] = -1  # Longs liquidated
    
    # 6. Liquidation Clusters (multiple liquidations in short time)
    df['liq_cluster'] = (df['liq_proxy_score'] > 3).astype(int)
    df['liq_cluster_count'] = df['liq_cluster'].rolling(12).sum()  # Count in 1 hour (12x5min)
    
    return df

def analyze_liquidation_correlation(price_df, liq_proxy_df):
    """
    Analyze correlation between liquidation proxy and future price movement
    """
    
    print("📊 Liquidation Proxy Correlation Analysis")
    print("="*70)
    
    # Merge data
    df = liq_proxy_df.copy()
    
    # Future returns (what happens after liquidation?)
    for periods in [1, 3, 6, 12]:  # 5min, 15min, 30min, 1hour
        df[f'future_return_{periods}'] = df['close'].pct_change(periods).shift(-periods)
    
    # Analyze: When liquidation proxy is high, what happens next?
    high_liq = df[df['liq_proxy_score'] >= 4]
    
    if len(high_liq) > 0:
        print(f"\n🔥 High Liquidation Events: {len(high_liq)}")
        print(f"\n   Average Future Returns:")
        for periods in [1, 3, 6, 12]:
            avg_return = high_liq[f'future_return_{periods}'].mean() * 100
            print(f"      {periods*5}min: {avg_return:+.3f}%")
        
        # Direction analysis
        shorts_liq = high_liq[high_liq['liq_direction'] == 1]
        longs_liq = high_liq[high_liq['liq_direction'] == -1]
        
        print(f"\n   Shorts Liquidated ({len(shorts_liq)} events):")
        if len(shorts_liq) > 0:
            for periods in [1, 3, 6, 12]:
                avg_return = shorts_liq[f'future_return_{periods}'].mean() * 100
                print(f"      {periods*5}min: {avg_return:+.3f}%")
        
        print(f"\n   Longs Liquidated ({len(longs_liq)} events):")
        if len(longs_liq) > 0:
            for periods in [1, 3, 6, 12]:
                avg_return = longs_liq[f'future_return_{periods}'].mean() * 100
                print(f"      {periods*5}min: {avg_return:+.3f}%")
    
    return df

if __name__ == "__main__":
    print("🚀 Creating Liquidation Proxy from Price Data")
    print("="*70)
    
    # Load Jan 2026 data
    df = pd.read_csv('training/data/BTC_5m_jan2_14_2026_mtf_full.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    print(f"✅ Loaded {len(df)} candles from 2025")
    
    # Create liquidation proxy
    df_with_liq = create_liquidation_proxy(df)
    
    # Analyze correlation
    df_analyzed = analyze_liquidation_correlation(df, df_with_liq)
    
    # Save
    df_analyzed.to_csv('BTC_5m_2025_with_liquidation_proxy.csv', index=False)
    print(f"\n💾 Saved to BTC_5m_2025_with_liquidation_proxy.csv")
    
    # Show sample high liquidation events
    high_liq_events = df_analyzed[df_analyzed['liq_proxy_score'] >= 4].head(20)
    print(f"\n📋 Sample High Liquidation Events:")
    print(high_liq_events[['timestamp', 'close', 'volume', 'liq_proxy_score', 'liq_direction', 'price_change']].to_string(index=False))
