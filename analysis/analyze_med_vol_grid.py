
import pandas as pd
import numpy as np
import os
import sys

# Add root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.fetch_data import fetch_live_data
from utils.feature_engineer import add_all_indicators
from utils.mtf_feature_engineer import MTFFeatureGenerator
from model_engines.mtf_scalper_v3.logic import MTFScalperV3Logic

def analyze_med_vol_grid():
    print("🚀 Grid Search: Medium Volatility (70 <= ATR <= 120)...")
    
    # 1. LOAD DATA
    start_date = "2026-01-02"
    end_date = "2026-01-14"
    
    print("   📥 Fetching Data...")
    def get_data(tf):
        df = fetch_live_data("BTC", tf, limit=4000)
        if df is None: return None
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        s = pd.Timestamp(start_date).tz_localize('UTC')
        e = pd.Timestamp(end_date).tz_localize('UTC') + pd.Timedelta(days=1)
        df = df[(df['timestamp'] >= s) & (df['timestamp'] <= e)]
        df = add_all_indicators(df)
        return df.sort_values('timestamp').reset_index(drop=True)

    df_5m = get_data('5m')
    df_15m = get_data('15m')
    df_30m = get_data('30m')
    
    if df_5m is None: return

    # 2. PREDICT
    print("   🧠 Generating Predictions...")
    logic = MTFScalperV3Logic()
    gen = MTFFeatureGenerator(df_5m, df_15m, df_30m)
    X_feat, price_df = gen.generate()
    X_feat = X_feat.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    probs = logic.model.predict_proba(X_feat.values)
    
    # Align context
    full_df = df_5m.set_index('timestamp').reindex(price_df.index)
    
    # 3. SCAN
    candidates = []
    
    for i in range(len(price_df)):
        close = price_df['close'].iloc[i]
        future = price_df.iloc[i+1:i+60]
        
        outcome_long = "NEUTRAL"
        outcome_short = "NEUTRAL"
        
        for _, row in future.iterrows():
            if row['high'] >= close * 1.015: outcome_long = "WIN"; break
            if row['low'] <= close * 0.992: outcome_long = "LOSS"; break
        for _, row in future.iterrows():
            if row['low'] <= close * 0.985: outcome_short = "WIN"; break
            if row['high'] >= close * 1.008: outcome_short = "LOSS"; break
        
        p_long = probs[i][1]
        p_short = probs[i][2]
        atr = full_df['atr_14'].iloc[i]
        adx = full_df['adx'].iloc[i]
        
        # TARGET ZONE: Medium Volatility
        if 70 <= atr <= 100:
            if 0.50 <= p_long < 0.80 and p_long > p_short:
                candidates.append({'type':'LONG', 'conf':p_long, 'atr':atr, 'adx':adx, 'outcome':outcome_long})
            elif 0.50 <= p_short < 0.80 and p_short > p_long:
                candidates.append({'type':'SHORT', 'conf':p_short, 'atr':atr, 'adx':adx, 'outcome':outcome_short})

    df_res = pd.DataFrame(candidates)
    if df_res.empty: return

    print(f"\n📊 Medium Volatility (70-100) Pile: {len(df_res)} candidates")
    
    # GRID SEARCH
    print("\n   Conf Threshold | ADX Filter | Trades | Win Rate")
    print("   " + "-"*45)
    
    for conf_thresh in [0.50, 0.60, 0.65, 0.70, 0.75]:
        for adx_thresh in [0, 20, 25, 30]:
            subset = df_res[
                (df_res['conf'] >= conf_thresh) & 
                (df_res['adx'] >= adx_thresh)
            ]
            
            wins = len(subset[subset['outcome']=='WIN'])
            losses = len(subset[subset['outcome']=='LOSS'])
            total = wins + losses
            
            if total < 5: continue
            
            wr = wins / total
            # Highlight if promising
            mark = "✨" if wr >= 0.60 else "  "
            print(f"   {mark} > {conf_thresh:.2f}       | > {adx_thresh}      | {total:>3}    | {wr:.1%}")

if __name__ == "__main__":
    analyze_med_vol_grid()
