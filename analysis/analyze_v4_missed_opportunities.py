
import pandas as pd
import numpy as np
import joblib
import os
import sys
import matplotlib.pyplot as plt

# Add root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.fetch_data import fetch_live_data
from utils.feature_engineer import add_all_indicators
from utils.mtf_feature_engineer import MTFFeatureGenerator
from model_engines.mtf_scalper_v3.logic import MTFScalperV3Logic

def analyze_missed_opps():
    print("🚀 Starting V4 Medium-Confidence Analysis...")
    
    # 1. LOAD DATA (Jan 2026)
    start_date = "2026-01-02"
    end_date = "2026-01-14"
    
    print("   📥 Fetching Data...")
    def get_tf_data(tf):
        limit = 4000 if tf == '5m' else 2000
        df = fetch_live_data("BTC", tf, limit=limit)
        if df is not None:
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            start_dt = pd.Timestamp(start_date).tz_localize('UTC')
            end_dt = pd.Timestamp(end_date).tz_localize('UTC') + pd.Timedelta(days=1)
            df = df[(df['timestamp'] >= start_dt) & (df['timestamp'] <= end_dt)]
            df = add_all_indicators(df)
            return df.sort_values('timestamp').reset_index(drop=True)
        return None

    df_5m = get_tf_data('5m')
    df_15m = get_tf_data('15m')
    df_30m = get_tf_data('30m')
    
    if df_5m is None: return

    # 2. LOAD MODEL
    logic = MTFScalperV3Logic()
    
    # 3. GENERATE PREDICTIONS
    print("   🧠 Generating Predictions...")
    gen = MTFFeatureGenerator(df_5m, df_15m, df_30m)
    X_feat, price_df = gen.generate()
    X_feat = X_feat.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    probs = logic.model.predict_proba(X_feat.values)
    
    # 4. ANALYZE MEDIUM CONFIDENCE (0.50 - 0.79)
    print("\n🔍 Analyzing Medium Confidence (0.50 - 0.79) Zone...")
    
    medium_longs = []
    medium_shorts = []
    
    # Indicators for correlation
    atr_values = df_5m['atr_14'].values[-len(X_feat):] # Align length
    rsi_values = df_5m['rsi_14'].values[-len(X_feat):]
    adx_values = df_5m['adx'].values[-len(X_feat):] if 'adx' in df_5m else np.zeros(len(X_feat))
    
    # Align price_df with features
    # price_df comes from generator, should match X_feat length
    # Check if df_5m needs slice
    # Generator uses intersection, so price_df is correct. 
    # But need to Map ATR/RSI from df_5m to price_df index.
    
    full_df = df_5m.set_index('timestamp').reindex(price_df.index)
    
    results = []
    
    for i in range(len(price_df)):
        ts = price_df.index[i]
        close = price_df['close'].iloc[i]
        
        p_long = probs[i][1]
        p_short = probs[i][2]
        
        # Determine actual outcome (Look forward 12 bars / 1 hour approx)
        # Or simple TP/SL check like backtest
        # Let's do a quick "Did it hit 1.5% TP or 0.8% SL first?" check
        # This is computationally heavy for loop, but fine for 4000 candles.
        
        future_window = price_df.iloc[i+1:i+60] # Look ahead 60 bars (5 hours) max
        
        outcome_long = "NEUTRAL"
        outcome_short = "NEUTRAL"
        
        # Check Long Outcome
        for _, row in future_window.iterrows():
            if row['high'] >= close * 1.015: 
                outcome_long = "WIN" 
                break
            if row['low'] <= close * 0.992: 
                outcome_long = "LOSS" 
                break
                
        # Check Short Outcome
        for _, row in future_window.iterrows():
            if row['low'] <= close * 0.985: 
                outcome_short = "WIN"
                break
            if row['high'] >= close * 1.008: 
                outcome_short = "LOSS"
                break
        
        # LOGIC:
        if 0.50 <= p_long < 0.80 and p_long > p_short:
            results.append({
                'type': 'LONG', 'conf': p_long, 'outcome': outcome_long,
                'atr': full_df['atr_14'].iloc[i], 'adx': full_df['adx'].iloc[i], 'rsi': full_df['rsi_14'].iloc[i]
            })
            
        if 0.50 <= p_short < 0.80 and p_short > p_long:
             results.append({
                'type': 'SHORT', 'conf': p_short, 'outcome': outcome_short,
                'atr': full_df['atr_14'].iloc[i], 'adx': full_df['adx'].iloc[i], 'rsi': full_df['rsi_14'].iloc[i]
            })

    # 5. STATS
    df_res = pd.DataFrame(results)
    if df_res.empty:
        print("No medium confidence trades found.")
        return

    print(f"\n📊 Total Medium Confidence Signals: {len(df_res)}")
    
    wins = df_res[df_res['outcome'] == 'WIN']
    losses = df_res[df_res['outcome'] == 'LOSS']
    
    win_rate = len(wins) / (len(wins) + len(losses)) if (len(wins) + len(losses)) > 0 else 0
    print(f"   Raw Win Rate (0.50-0.79): {win_rate:.1%} ({len(wins)} W / {len(losses)} L)")
    
    print("\n🔍 HYPOTHESIS TESTING:")
    
    # ATR Analysis
    print(f"   Avg ATR (Wins):   {wins['atr'].mean():.2f}")
    print(f"   Avg ATR (Losses): {losses['atr'].mean():.2f}")
    
    # ADX Analysis
    print(f"   Avg ADX (Wins):   {wins['adx'].mean():.2f}")
    print(f"   Avg ADX (Losses): {losses['adx'].mean():.2f}")
    
    # Finding the "Golden Filter"
    # Try filtering by ATR < X and ADX > Y
    print("\n🛠️  Simulating Filters on Medium Confidence Trades:")
    
    best_wr = 0
    best_filter = ""
    best_count = 0
    
    for max_atr in [30, 50, 70, 100, 150]:
        filtered = df_res[df_res['atr'] < max_atr]
        f_wins = filtered[filtered['outcome'] == 'WIN']
        f_losses = filtered[filtered['outcome'] == 'LOSS']
        count = len(f_wins) + len(f_losses)
        if count < 5: continue
        wr = len(f_wins) / count
        print(f"   [ATR < {max_atr}]: {len(f_wins)} W / {len(f_losses)} L -> {wr:.1%} WR")
        
        if wr > best_wr and count >= 5:
            best_wr = wr
            best_filter = f"ATR < {max_atr}"
            best_count = count

    print(f"\n🏆 Best Filter Found: {best_filter} (WR: {best_wr:.1%} on {best_count} trades)")

if __name__ == "__main__":
    analyze_missed_opps()
