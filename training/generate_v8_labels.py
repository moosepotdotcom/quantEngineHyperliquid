
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.v5_feature_engineer import generate_v5_features

def generate_v8_labels():
    """
    Generate 4-class labels for V8 unified model:
    - Class 0: Low Volatility → Grid Strategy
    - Class 1: High Vol + Bullish Setup → Long (0.5% target)
    - Class 2: High Vol + Bearish Setup → Short (0.5% target)
    - Class 3: High Vol + Uncertain → Neutral
    """
    print("🏷️  Generating V8 Unified Labels...")
    
    # Load data
    data_path = 'training/data/BTC_5m_2025_enriched.csv'
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    print(f"   📊 Loaded {len(df)} candles")
    
    # Generate features
    print("   🧠 Generating Features...")
    df_enriched = generate_v5_features(df)
    
    # Calculate future volatility and outcomes
    print("   🔮 Calculating Future Outcomes...")
    
    labels = []
    
    for i in range(len(df_enriched) - 48):  # Need 48 candles (4h) future data
        row = df_enriched.iloc[i]
        future = df_enriched.iloc[i+1:i+49]
        
        # 1. Calculate future volatility (next 2h = 24 candles)
        future_2h = future.iloc[:24]
        future_atr = (future_2h['high'] - future_2h['low']).mean()
        current_price = row['close']
        future_atr_pct = (future_atr / current_price) * 100
        
        # 2. Determine volatility regime
        is_high_vol = future_atr_pct > 0.3  # High if > 0.3%
        
        # 3. If low vol → Class 0 (Grid)
        if not is_high_vol:
            labels.append(0)
            continue
            
        # 4. For high vol, check directional setup and outcome
        entry_price = row['close']
        
        # Check current setup indicators
        ema_50 = row.get('ema_50_15m', 0)
        rsi_15m = row.get('rsi_15m', 50)
        rsi_1h = row.get('rsi_1h', 50)
        cvd_1h = row.get('cvd_1h', 0)
        volume_delta = row.get('volume_delta', 0)
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
        
        # 5. Check outcome (0.5% TP, 0.15% SL)
        tp = 0.005
        sl = 0.0015
        
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
            
            # Only label as Class 1 (Long) if it would win
            if outcome == 'WIN':
                labels.append(1)
            else:
                labels.append(3)  # Neutral (bad setup)
                
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
            
            # Only label as Class 2 (Short) if it would win
            if outcome == 'WIN':
                labels.append(2)
            else:
                labels.append(3)  # Neutral (bad setup)
        else:
            # No clear setup → Neutral
            labels.append(3)
    
    # Pad remaining rows
    labels.extend([3] * 48)
    
    df_enriched['v8_label'] = labels
    
    # Stats
    print(f"\n   📊 Label Distribution:")
    print(f"      Class 0 (Grid):    {(df_enriched['v8_label']==0).sum():5d} ({(df_enriched['v8_label']==0).mean():.1%})")
    print(f"      Class 1 (Long):    {(df_enriched['v8_label']==1).sum():5d} ({(df_enriched['v8_label']==1).mean():.1%})")
    print(f"      Class 2 (Short):   {(df_enriched['v8_label']==2).sum():5d} ({(df_enriched['v8_label']==2).mean():.1%})")
    print(f"      Class 3 (Neutral): {(df_enriched['v8_label']==3).sum():5d} ({(df_enriched['v8_label']==3).mean():.1%})")
    
    # Save
    output_path = 'training/data/BTC_5m_2025_v8_labeled.csv'
    df_enriched.to_csv(output_path, index=False)
    print(f"\n   ✅ Saved to {output_path}")
    
    return df_enriched

if __name__ == "__main__":
    generate_v8_labels()
