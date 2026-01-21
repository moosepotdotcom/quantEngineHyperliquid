#!/usr/bin/env python3
"""
PHASE 2: SCALPING LABEL GENERATOR
Generates training labels optimized for 0.5% TP / 0.3% SL targets
"""

import pandas as pd
import numpy as np
from datetime import datetime
import requests
import time

def fetch_training_data(days=90):
    """Fetch 3 months of 5m data for training"""
    print(f"\n📡 Fetching {days} days of training data...")
    
    url = 'https://api.hyperliquid.xyz/info'
    
    # Calculate time range
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now().timestamp() - (days * 24 * 3600)) * 1000)
    
    payload = {
        'type': 'candleSnapshot',
        'req': {
            'coin': 'BTC',
            'interval': '5m',
            'startTime': start_time,
            'endTime': end_time
        }
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=30)
        data = resp.json()
        
        df_data = []
        for candle in data:
            df_data.append([
                candle['t'],
                float(candle['o']),
                float(candle['h']),
                float(candle['l']),
                float(candle['c']),
                float(candle['v'])
            ])
        
        df = pd.DataFrame(df_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        print(f"✅ Fetched {len(df)} candles")
        print(f"   Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
        
        return df
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def generate_scalping_labels(df, tp_pct=0.005, sl_pct=0.003, lookahead=100):
    """
    Generate labels for scalping strategy
    
    Args:
        df: DataFrame with OHLCV data
        tp_pct: Take profit percentage (0.005 = 0.5%)
        sl_pct: Stop loss percentage (0.003 = 0.3%)
        lookahead: Number of candles to look ahead (100 = ~8 hours on 5m)
    
    Returns:
        DataFrame with labels column (0=Neutral, 1=Long, 2=Short)
    """
    print(f"\n🏷️  Generating scalping labels...")
    print(f"   TP: {tp_pct*100:.1f}% | SL: {sl_pct*100:.1f}%")
    print(f"   Lookahead: {lookahead} candles (~{lookahead*5/60:.1f} hours)")
    
    labels = []
    long_wins = 0
    long_losses = 0
    short_wins = 0
    short_losses = 0
    neutrals = 0
    
    total = len(df)
    
    for i in range(total):
        if i % 1000 == 0:
            print(f"   Processing: {i}/{total} ({i/total*100:.1f}%)", end='\r')
        
        # Need lookahead window
        if i >= total - lookahead:
            labels.append(0)  # Neutral (insufficient data)
            neutrals += 1
            continue
        
        current_price = df.iloc[i]['close']
        future = df.iloc[i+1:i+lookahead+1]
        
        # Calculate TP/SL levels
        long_tp = current_price * (1 + tp_pct)
        long_sl = current_price * (1 - sl_pct)
        short_tp = current_price * (1 - tp_pct)
        short_sl = current_price * (1 + sl_pct)
        
        # Check LONG outcome
        long_outcome = None
        for _, row in future.iterrows():
            if row['high'] >= long_tp:
                long_outcome = 'WIN'
                break
            if row['low'] <= long_sl:
                long_outcome = 'LOSS'
                break
        
        # Check SHORT outcome
        short_outcome = None
        for _, row in future.iterrows():
            if row['low'] <= short_tp:
                short_outcome = 'WIN'
                break
            if row['high'] >= short_sl:
                short_outcome = 'LOSS'
                break
        
        # Assign label based on best outcome
        if long_outcome == 'WIN' and short_outcome != 'WIN':
            labels.append(1)  # LONG
            long_wins += 1
        elif short_outcome == 'WIN' and long_outcome != 'WIN':
            labels.append(2)  # SHORT
            short_wins += 1
        elif long_outcome == 'LOSS':
            long_losses += 1
            if short_outcome == 'WIN':
                labels.append(2)  # SHORT is better
                short_wins += 1
            else:
                labels.append(0)  # NEUTRAL
                neutrals += 1
        elif short_outcome == 'LOSS':
            short_losses += 1
            if long_outcome == 'WIN':
                labels.append(1)  # LONG is better
                long_wins += 1
            else:
                labels.append(0)  # NEUTRAL
                neutrals += 1
        else:
            labels.append(0)  # NEUTRAL (both expired or both win)
            neutrals += 1
    
    print(f"\n\n✅ Labels generated!")
    print(f"\n📊 Label Distribution:")
    print(f"   LONG signals: {long_wins:,} ({long_wins/total*100:.1f}%)")
    print(f"   SHORT signals: {short_wins:,} ({short_wins/total*100:.1f}%)")
    print(f"   NEUTRAL: {neutrals:,} ({neutrals/total*100:.1f}%)")
    print(f"\n   Total tradeable: {long_wins + short_wins:,} ({(long_wins + short_wins)/total*100:.1f}%)")
    print(f"   Long win rate: {long_wins/(long_wins + long_losses)*100:.1f}%")
    print(f"   Short win rate: {short_wins/(short_wins + short_losses)*100:.1f}%")
    
    df['label'] = labels
    return df

def main():
    print("\n" + "🚀"*35)
    print("PHASE 2: SCALPING MODEL RETRAINING")
    print("Generating labels for 0.5% TP / 0.3% SL")
    print("🚀"*35)
    
    # Step 1: Fetch training data
    df = fetch_training_data(days=90)
    
    if df is None:
        print("\n❌ Failed to fetch data. Using cached data...")
        # Try to load cached data
        try:
            df = pd.read_csv('/Users/alifiyaa/Downloads/quantEngineHyperliquid/EXPORT/btc_5m_history_final.csv')
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            print(f"✅ Loaded {len(df)} cached candles")
        except:
            print("❌ No cached data available. Exiting...")
            return
    
    # Step 2: Generate scalping labels
    df_labeled = generate_scalping_labels(df, tp_pct=0.005, sl_pct=0.003, lookahead=100)
    
    # Step 3: Save labeled data
    output_file = '/Users/alifiyaa/Downloads/quantEngineHyperliquid/training/data/scalping_labels_0.5pct.csv'
    df_labeled.to_csv(output_file, index=False)
    print(f"\n💾 Saved labeled data to: {output_file}")
    
    # Step 4: Statistics
    print(f"\n📊 Training Data Statistics:")
    print(f"   Total samples: {len(df_labeled):,}")
    print(f"   Date range: {df_labeled['timestamp'].min()} to {df_labeled['timestamp'].max()}")
    print(f"   Tradeable signals: {len(df_labeled[df_labeled['label'] != 0]):,}")
    print(f"   Signal frequency: {len(df_labeled[df_labeled['label'] != 0])/len(df_labeled)*100:.1f}%")
    
    # Estimate trades per day
    days = (df_labeled['timestamp'].max() - df_labeled['timestamp'].min()).days
    signals_per_day = len(df_labeled[df_labeled['label'] != 0]) / days
    print(f"\n   Estimated signals per day: {signals_per_day:.1f}")
    print(f"   With 45% threshold: ~{signals_per_day * 0.45:.1f} trades/day")
    
    print("\n✅ PHASE 2 STEP 1 COMPLETE!")
    print("\n📝 Next steps:")
    print("   1. Add technical indicators to labeled data")
    print("   2. Train XGBoost, LightGBM, CatBoost models")
    print("   3. Optimize thresholds for 80%+ win rate")
    print("   4. Backtest new models")
    print("   5. Deploy!")
    
    print(f"\n🎯 Ready to train models? Run:")
    print(f"   python train_scalping_models.py")

if __name__ == "__main__":
    main()
