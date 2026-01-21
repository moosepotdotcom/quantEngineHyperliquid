#!/usr/bin/env python3
"""
BRAIN V7: FEATURE & LABEL GENERATOR (JAN 2026)
1. Load 5m, 15m, 1h Jan 2026 data.
2. Generate Indicators.
3. Merge MTF.
4. Generate Labels (0.5% TP, 0.3% SL).
"""
import sys
import os
import pandas as pd
import numpy as np

# Add utils path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.feature_engineer import add_all_indicators

DATA_DIR = 'training/data'

def load_and_enrich(interval):
    print(f"\n📊 Processing {interval} data...")
    filename = f"{DATA_DIR}/BTC_{interval}_jan2026.csv"
    if not os.path.exists(filename):
        print(f"❌ File not found: {filename}")
        return None
    
    df = pd.read_csv(filename)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Generate features
    print(f"   Generating indicators for {len(df)} candles...")
    df = add_all_indicators(df)
    
    # Drop initial NaN from indicators
    df.dropna(inplace=True)
    print(f"   Cleaned data: {len(df)} rows")
    
    return df

def merge_mtf(df_5m, df_15m, df_1h):
    print(f"\n🔗 Merging Multi-Timeframe Features...")
    
    df_5m = df_5m.set_index('timestamp')
    df_15m = df_15m.set_index('timestamp')
    df_1h = df_1h.set_index('timestamp')
    
    exclude = ['open', 'high', 'low', 'close', 'volume', 'label']
    
    # Process 15m Context
    ctx_cols_15m = [c for c in df_15m.columns if c not in exclude]
    df_15m_ctx = df_15m[ctx_cols_15m].copy()
    df_15m_ctx.columns = [f"{c}_15m" for c in ctx_cols_15m]
    df_15m_resampled = df_15m_ctx.reindex(df_5m.index, method='ffill')
    
    # Process 1h Context
    ctx_cols_1h = [c for c in df_1h.columns if c not in exclude]
    df_1h_ctx = df_1h[ctx_cols_1h].copy()
    df_1h_ctx.columns = [f"{c}_1h" for c in ctx_cols_1h]
    df_1h_resampled = df_1h_ctx.reindex(df_5m.index, method='ffill')
    
    # Merge
    df_mtf = pd.concat([df_5m, df_15m_resampled, df_1h_resampled], axis=1)
    df_mtf.dropna(inplace=True)
    df_mtf.reset_index(inplace=True)
    
    print(f"   Final MTF Dataset: {len(df_mtf)} rows, {len(df_mtf.columns)} columns")
    return df_mtf

def generate_labels(df, tp_pct=0.005, sl_pct=0.003, lookahead=120): # 120 candles = 10 hours
    print(f"\n🏷️  Generating V7 Labels (TP: {tp_pct*100:.1f}%, SL: {sl_pct*100:.1f}%)")
    
    labels = []
    long_wins = 0
    short_wins = 0
    neutrals = 0
    
    # Create numpy arrays for faster processing
    closes = df['close'].values
    highs = df['high'].values
    lows = df['low'].values
    length = len(df)
    
    print("   Processing...")
    
    for i in range(length):
        if i >= length - lookahead:
            labels.append(0)
            neutrals += 1
            continue
            
        entry = closes[i]
        
        # Targets
        long_tp = entry * (1 + tp_pct)
        long_sl = entry * (1 - sl_pct)
        short_tp = entry * (1 - tp_pct)
        short_sl = entry * (1 + sl_pct)
        
        # Lookahead window
        window_highs = highs[i+1 : i+1+lookahead]
        window_lows = lows[i+1 : i+1+lookahead]
        
        # Check Long
        # First index where High >= TP or Low <= SL
        long_win_idx = -1
        long_loss_idx = -1
        
        # Vectorized check is hard with First Occurrence logic, using loop for correctness
        # Optimization: Use np.argmax > threshold
        
        # Faster check
        hit_ltp = np.where(window_highs >= long_tp)[0]
        hit_lsl = np.where(window_lows <= long_sl)[0]
        
        first_ltp = hit_ltp[0] if len(hit_ltp) > 0 else 9999
        first_lsl = hit_lsl[0] if len(hit_lsl) > 0 else 9999
        
        is_long_win = (first_ltp < first_lsl)
        is_long_loss = (first_lsl < first_ltp)
        
        # Check Short
        hit_stp = np.where(window_lows <= short_tp)[0]
        hit_ssl = np.where(window_highs >= short_sl)[0]
        
        first_stp = hit_stp[0] if len(hit_stp) > 0 else 9999
        first_ssl = hit_ssl[0] if len(hit_ssl) > 0 else 9999
        
        is_short_win = (first_stp < first_ssl)
        is_short_loss = (first_ssl < first_stp)
        
        label = 0
        if is_long_win and not is_short_win:
            label = 1
            long_wins += 1
        elif is_short_win and not is_long_win:
            label = 2
            short_wins += 1
        elif is_long_win and is_short_win:
            # Both won? Pick the one that happened fastest? Or Neutral?
            # V7 Policy: Neutral if ambiguous, or pick based on slope?
            # Safe: Neutral
            label = 0
            neutrals += 1
        else:
            neutrals += 1
            
        labels.append(label)
        
    df['label'] = labels
    
    print(f"   Target Distribution:")
    print(f"   LONG (1): {long_wins} ({long_wins/length:.1%})")
    print(f"   SHORT (2): {short_wins} ({short_wins/length:.1%})")
    print(f"   NEUTRAL (0): {neutrals} ({neutrals/length:.1%})")
    
    return df

def main():
    print("="*70)
    print("🧠 BRAIN V7 FEATURE PIPELINE")
    print("="*70)
    
    # 1. Load & Enrich
    df_5m = load_and_enrich('5m')
    df_15m = load_and_enrich('15m')
    df_1h = load_and_enrich('1h')
    
    if df_5m is None or df_15m is None or df_1h is None:
        print("❌ Missing data files. Run fetch_jan2026_full.py first.")
        return
        
    # 2. Merge MTF
    df_mtf = merge_mtf(df_5m, df_15m, df_1h)
    
    # 3. Generate Labels
    df_labeled = generate_labels(df_mtf)
    
    # 4. Save
    output_file = f"{DATA_DIR}/BTC_5m_jan2026_mtf_labeled.csv"
    df_labeled.to_csv(output_file, index=False)
    print(f"\n✅ SAVED: {output_file}")
    print("ready for training.")

if __name__ == "__main__":
    main()
