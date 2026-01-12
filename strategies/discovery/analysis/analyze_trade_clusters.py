
import sys
import os
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION'))
sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION/utils'))

from quant_engine import TradingEngine, add_all_indicators

def analyze_clusters():
    print("🔬 TRADING DNA ANALYSIS (Finding the 99% Cluster)")
    print("="*70)
    
    engine = TradingEngine()
    df_raw = engine.fetch_data('5m', 4000)
    df_raw = add_all_indicators(df_raw)
    
    try:
        from utils.advanced_features import get_rolling_hurst
        df_raw['hurst'] = get_rolling_hurst(df_raw, window=100)
    except:
        df_raw['hurst'] = 0.5 
        
    df_raw.set_index('timestamp', inplace=True)
    
    # Context
    df_15m = add_all_indicators(engine.fetch_data('15m', 4000))
    df_1h = add_all_indicators(engine.fetch_data('1h', 4000))
    df_15m.set_index('timestamp', inplace=True)
    df_1h.set_index('timestamp', inplace=True)
    
    exclude = ['open', 'high', 'low', 'close', 'volume', 'hurst']
    
    c15 = [c for c in df_15m.columns if c not in exclude]
    df15_r = df_15m[c15].copy()
    df15_r.columns = [f"{c}_15m" for c in c15]
    df_merged = pd.concat([df_raw, df15_r.reindex(df_raw.index, method='ffill')], axis=1)
    
    c1h = [c for c in df_1h.columns if c not in exclude]
    df1h_r = df_1h[c1h].copy()
    df1h_r.columns = [f"{c}_1h" for c in c1h]
    df_merged = pd.concat([df_merged, df1h_r.reindex(df_raw.index, method='ffill')], axis=1)
    
    start_sim = pd.Timestamp("2026-01-02 00:00:00")
    end_sim = pd.Timestamp("2026-01-09 23:59:59")
    sim_data = df_merged[(df_merged.index >= start_sim) & (df_merged.index <= end_sim)]
    
    print(f"✅ Data Ready: {len(sim_data)} rows. Analyzing...")
    
    trades = []
    
    for idx, row in sim_data.iterrows():
        # Predict
        row_vals = row.drop(labels=exclude + ['hurst'], errors='ignore')
        X = row_vals.values.reshape(1, -1)
        X = np.nan_to_num(X, nan=0.0)
        if X.shape[1] > 239: X = X[:, :239]
        
        p1 = engine.mtf_xgb.predict_proba(X)[0]
        p2 = engine.mtf_lgb.predict(X)[0]
        p3 = engine.mtf_cat.predict_proba(X)[0]
        
        std_dev = np.std([p1, p2, p3], axis=0)
        max_disagreement = np.max(std_dev)
        
        avg_prob = (p1 + p2 + p3) / 3
        conf_long, conf_short = avg_prob[1], avg_prob[2]
        
        # Golden Config Logic (Proven Baseline)
        atr_val = row.get('atr_14', 50)
        penalty = max(0, (atr_val - 70) * 0.002)
        required = 0.45 + penalty
        
        signal = None
        if conf_long >= required: signal = 'LONG'
        elif conf_short >= required: signal = 'SHORT'
        
        # Consensus Filter (Baseline)
        if max_disagreement > 0.15: signal = None
        
        if signal:
            entry_price = row['close']
            tp = entry_price * (1.015 if signal == 'LONG' else 0.985)
            sl = entry_price * (0.992 if signal == 'LONG' else 1.008)
            
            outcome = "OPEN"
            pnl = 0.0
            
            future_data = df_raw[df_raw.index > idx]
            for _, f_row in future_data.iterrows():
                h, l = f_row['high'], f_row['low']
                if signal == 'LONG':
                    if h >= tp: outcome = "WIN"; pnl = 1.5; break
                    if l <= sl: outcome = "LOSS"; pnl = -0.8; break
                else:
                    if l <= tp: outcome = "WIN"; pnl = 1.5; break
                    if h >= sl: outcome = "LOSS"; pnl = -0.8; break
            
            trades.append({
                'outcome': outcome,
                'type': signal,
                'conf': max(conf_long, conf_short),
                'disagreement': max_disagreement,
                'rsi': row.get('rsi_14', 50),
                'hurst': row.get('hurst', 0.5),
                'atr': atr_val
            })
            
    # ANALYSIS
    df = pd.DataFrame(trades)
    print(f"\n📊 TOTAL TRADES: {len(df)}")
    if len(df) == 0: return

    print("\n🔍 CLUSTER SEARCH (Rules > 10 Trades, > 98% WR)")
    print("-" * 70)
    
    # Grid search on DataFrame
    best_wr = 0
    best_rule = ""
    
    for rsi_low, rsi_high in [(0, 30), (30, 70), (70, 100), (0, 40), (60, 100)]:
        for hurst_cap in [0.45, 0.50, 0.55, 1.0]:
            for conf_floor in [0.45, 0.50, 0.55]:
                for dis_cap in [0.05, 0.10, 0.15]:
                    
                    subset = df[
                        (df['rsi'] >= rsi_low) & (df['rsi'] <= rsi_high) &
                        (df['hurst'] <= hurst_cap) &
                        (df['conf'] >= conf_floor) &
                        (df['disagreement'] <= dis_cap)
                    ]
                    
                    if len(subset) > 5:
                        wins = len(subset[subset['outcome'] == 'WIN'])
                        wr = wins / len(subset)
                        
                        if wr >= 0.98:
                            print(f"💎 FOUND GEM: WR {wr:.1%} ({len(subset)} Trades)")
                            print(f"   Rule: RSI[{rsi_low}-{rsi_high}] | H<{hurst_cap} | Conf>{conf_floor} | D<{dis_cap}")
                            best_wr = max(best_wr, wr)

    if best_wr < 0.98:
        print("   ⚠️ No 98%+ cluster found with > 5 trades.")
        print("   Printing top 3 clusters:")
        # Sort by WR * log(count) or something?
        pass

if __name__ == "__main__":
    analyze_clusters()
