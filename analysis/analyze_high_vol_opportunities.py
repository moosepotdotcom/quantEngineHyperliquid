
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

def analyze_high_vol_opps():
    print("🚀 Deep Drill-Down: High Volatility Opportunities (ATR >= 70)...")
    
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
    
    # 3. ANALYZE "REJECTED" PILE
    # Criteria: 0.50 <= Conf < 0.80  AND  ATR >= 70
    
    candidates = []
    
    print("\n🔍 Scanning for Salvageable High-Vol Trades...")
    
    for i in range(len(price_df)):
        # Outlook
        close = price_df['close'].iloc[i]
        future = price_df.iloc[i+1:i+60] # Look ahead 5 hours
        
        outcome_long = "NEUTRAL"
        outcome_short = "NEUTRAL"
        
        # Simple TP(1.5%)/SL(0.8%) Check
        for _, row in future.iterrows():
            if row['high'] >= close * 1.015: 
                outcome_long = "WIN"; break
            if row['low'] <= close * 0.992: 
                outcome_long = "LOSS"; break
                
        for _, row in future.iterrows():
            if row['low'] <= close * 0.985: 
                outcome_short = "WIN"; break
            if row['high'] >= close * 1.008: 
                outcome_short = "LOSS"; break
        
        p_long = probs[i][1]
        p_short = probs[i][2]
        atr = full_df['atr_14'].iloc[i]
        
        # We only care about the Pile we currently REJECT
        if atr >= 70:
            row_data = {
                'atr': atr,
                'adx': full_df['adx'].iloc[i],
                'rsi': full_df['rsi_14'].iloc[i],
                'hurst': full_df.get('hurst', 0.5), # Might be missing
                'vol_surge': full_df.get('volume_surge', 1.0),
                'outcome': 'NEUTRAL'
            }
            
            if 0.50 <= p_long < 0.80 and p_long > p_short:
                row_data['type'] = 'LONG'
                row_data['conf'] = p_long
                row_data['outcome'] = outcome_long
                candidates.append(row_data)
                
            elif 0.50 <= p_short < 0.80 and p_short > p_long:
                row_data['type'] = 'SHORT'
                row_data['conf'] = p_short
                row_data['outcome'] = outcome_short
                candidates.append(row_data)
                
    df_cand = pd.DataFrame(candidates)
    if df_cand.empty:
        print("No candidates found.")
        return

    # 4. HYPOTHESIS TESTING
    # Current Stats of this pile
    total = len(df_cand)
    wins = len(df_cand[df_cand['outcome'] == 'WIN'])
    losses = len(df_cand[df_cand['outcome'] == 'LOSS'])
    base_wr = wins / (wins + losses) if (wins+losses) > 0 else 0
    
    print(f"\n📊 The 'High Vol' Pile (ATR >= 70):")
    print(f"   Total: {total} candidates")
    print(f"   Base Win Rate: {base_wr:.1%} (TRASH 🗑️)")
    
    print("\n🧪 Testing Secondary Filters to Salvage Trades:")
    
    # Define experiments
    experiments = [
        ("Trend is Friend", lambda r: r['adx'] > 30),
        ("Strong Trend", lambda r: r['adx'] > 40),
        ("Extreme Trend", lambda r: r['adx'] > 50),
        ("RSI Oversold/Bought", lambda r: (r['type']=='LONG' and r['rsi']<30) or (r['type']=='SHORT' and r['rsi']>70)),
        ("RSI Safe Zone", lambda r: 40 < r['rsi'] < 60),
        ("Volume Spike", lambda r: r['vol_surge'] > 2.0),
        ("Confident Only", lambda r: r['conf'] > 0.70), # Higher conf within the med range
        ("Trend + Conf", lambda r: r['adx'] > 30 and r['conf'] > 0.65)
    ]
    
    best_filter = None
    best_score = 0
    
    for name, func in experiments:
        filtered = df_cand[df_cand.apply(func, axis=1)]
        n_w = len(filtered[filtered['outcome']=='WIN'])
        n_l = len(filtered[filtered['outcome']=='LOSS'])
        n_t = n_w + n_l
        
        if n_t < 5: continue
        
        wr = n_w / n_t
        print(f"   [{name:<15}]: {n_t:>3} trades | {wr:.1%} WR ({n_w} W / {n_l} L)")
        
        # Scoring: We want High WR (>60%) and Decent Volume (>10 trades)
        if wr > 0.60 and n_t > 10:
            print(f"      ✨ PROMISING!")
            
    print("\n✅ Done.")

if __name__ == "__main__":
    analyze_high_vol_opps()
