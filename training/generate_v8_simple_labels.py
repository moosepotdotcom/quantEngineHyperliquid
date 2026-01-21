
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.v5_feature_engineer import generate_v5_features

def generate_v8_simple_labels():
    """
    Generate 3-class labels for V8 simple strategy (NO GRID):
    - Class 0: Long (0.5% target, 0.15% stop)
    - Class 1: Short (0.5% target, 0.15% stop)
    - Class 2: Neutral (sit out)
    
    Only label as Long/Short if:
    1. Setup is valid (EMA, RSI, CVD alignment)
    2. Trade would WIN with our parameters
    """
    print("🏷️  Generating V8 Simple Labels (No Grid)...")
    
    # Load data
    data_path = 'training/data/BTC_5m_2025_enriched.csv'
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    print(f"   📊 Loaded {len(df)} candles")
    
    # Generate features
    print("   🧠 Generating Features...")
    df_enriched = generate_v5_features(df)
    
    # Calculate outcomes
    print("   🔮 Calculating Trade Outcomes...")
    
    labels = []
    
    tp = 0.005  # 0.5%
    sl = 0.0015  # 0.15%
    
    for i in range(len(df_enriched) - 48):
        row = df_enriched.iloc[i]
        future = df_enriched.iloc[i+1:i+49]
        
        entry_price = row['close']
        
        # Check setup indicators
        ema_50 = row.get('ema_50_15m', 0)
        rsi_15m = row.get('rsi_15m', 50)
        rsi_1h = row.get('rsi_1h', 50)
        cvd_1h = row.get('cvd_1h', 0)
        imbalance = row.get('flow_imbalance_15m', 0)
        if pd.isna(imbalance): imbalance = row.get('flow_imbalance', 0)
        
        # Check if bullish setup
        is_bullish_setup = (
            entry_price < ema_50 and
            rsi_15m <= 63 and
            rsi_1h < 60 and
            cvd_1h > 0
        )
        
        # Check if bearish setup
        is_bearish_setup = (
            entry_price > ema_50 and
            imbalance < 0.10 and
            rsi_1h > 40 and
            cvd_1h < 0
        )
        
        if is_bullish_setup:
            # Check if long would win
            outcome = 'TIMEOUT'
            for _, candle in future.iterrows():
                if candle['high'] >= entry_price * (1 + tp):
                    outcome = 'WIN'
                    break
                if candle['low'] <= entry_price * (1 - sl):
                    outcome = 'LOSS'
                    break
            
            if outcome == 'WIN':
                labels.append(0)  # LONG
            else:
                labels.append(2)  # NEUTRAL
                
        elif is_bearish_setup:
            # Check if short would win
            outcome = 'TIMEOUT'
            for _, candle in future.iterrows():
                if candle['low'] <= entry_price * (1 - tp):
                    outcome = 'WIN'
                    break
                if candle['high'] >= entry_price * (1 + sl):
                    outcome = 'LOSS'
                    break
            
            if outcome == 'WIN':
                labels.append(1)  # SHORT
            else:
                labels.append(2)  # NEUTRAL
        else:
            labels.append(2)  # NEUTRAL
    
    # Pad remaining
    labels.extend([2] * 48)
    
    df_enriched['v8_simple_label'] = labels
    
    # Stats
    print(f"\n   📊 Label Distribution:")
    print(f"      Class 0 (Long):    {(df_enriched['v8_simple_label']==0).sum():5d} ({(df_enriched['v8_simple_label']==0).mean():.1%})")
    print(f"      Class 1 (Short):   {(df_enriched['v8_simple_label']==1).sum():5d} ({(df_enriched['v8_simple_label']==1).mean():.1%})")
    print(f"      Class 2 (Neutral): {(df_enriched['v8_simple_label']==2).sum():5d} ({(df_enriched['v8_simple_label']==2).mean():.1%})")
    
    # Save
    output_path = 'training/data/BTC_5m_2025_v8_simple_labeled.csv'
    df_enriched.to_csv(output_path, index=False)
    print(f"\n   ✅ Saved to {output_path}")
    
    return df_enriched

if __name__ == "__main__":
    generate_v8_simple_labels()
