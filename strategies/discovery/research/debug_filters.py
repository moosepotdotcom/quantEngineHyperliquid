
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION'))
sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION/utils'))

from quant_engine import TradingEngine, add_all_indicators

def debug_filters():
    print("🕵️  DEBUGGING FILTERS (JAN 2 - JAN 9)...")
    print("="*70)
    
    engine = TradingEngine()
    df_raw = engine.fetch_data('5m', 4000) 
    if len(df_raw) == 0: return

    # Hurst Logic
    try:
        from utils.advanced_features import get_rolling_hurst
        df_raw['hurst'] = get_rolling_hurst(df_raw, window=100)
    except:
        df_raw['hurst'] = 0.5
        
    df_raw = add_all_indicators(df_raw)
    df_raw.set_index('timestamp', inplace=True)
    
    # Context (Simplified for speed - reusing raw mostly fine for logic check)
    # Actually need correct shape for model
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
    
    print(f"✅ Data Ready: {len(sim_data)} rows. Testing filters...")
    
    stats = {
        'total_signals': 0,
        'blocked_disagreement': 0,
        'blocked_atr': 0,
        'blocked_hurst': 0,
        'passed': 0
    }
    
    for idx, row in sim_data.iterrows():
        row_vals = row.drop(labels=exclude + ['hurst'], errors='ignore')
        X = row_vals.values.reshape(1, -1)
        X = np.nan_to_num(X, nan=0.0)
        if X.shape[1] > 239: X = X[:, :239]
        
        p1 = engine.mtf_xgb.predict_proba(X)[0]
        p2 = engine.mtf_lgb.predict(X)[0]
        p3 = engine.mtf_cat.predict_proba(X)[0]
        avg_prob = (p1 + p2 + p3) / 3
        
        std_dev = np.std([p1, p2, p3], axis=0)
        max_disagreement = np.max(std_dev)
        
        threshold = 0.45
        conf_long, conf_short = avg_prob[1], avg_prob[2]
        
        signal = None
        current_conf = 0.0
        if conf_long >= threshold: 
            signal = 'LONG'; current_conf = conf_long
        elif conf_short >= threshold: 
            signal = 'SHORT'; current_conf = conf_short
            
        if signal:
            stats['total_signals'] += 1
            
            # Check Filters
            is_blocked = False
            
            # 1. Disagreement
            if max_disagreement > 0.15:
                stats['blocked_disagreement'] += 1
                is_blocked = True
                
            # 2. ATR
            if not is_blocked:
                atr = row.get('atr_14', 7)
                penalty = (atr - 7) * 0.002
                if penalty < 0: penalty = 0
                if current_conf < (threshold + penalty):
                    stats['blocked_atr'] += 1
                    is_blocked = True
                    # print(f"ATR Block: Conf {current_conf:.2f} < {threshold+penalty:.2f} (ATR {atr:.1f})")
            
            # 3. Hurst
            if not is_blocked:
                rsi = row.get('rsi_14', 50)
                hurst = row.get('hurst', 0.5)
                # Falling Knife logic: Long + RSI<30 + Hurst>0.5
                if signal == 'LONG' and rsi < 30 and hurst > 0.5:
                    stats['blocked_hurst'] += 1
                    is_blocked = True
            
            if not is_blocked:
                stats['passed'] += 1

    print("\n" + "="*70)
    print("📊 FILTER DIAGNOSTICS")
    print(f"   Total Signals (Triggering 0.45): {stats['total_signals']}")
    print("-" * 30)
    print(f"   🚫 Blocked by Consensus (>0.15): {stats['blocked_disagreement']}")
    print(f"   🚫 Blocked by ATR Shield:        {stats['blocked_atr']}")
    print(f"   🚫 Blocked by Hurst Shield:      {stats['blocked_hurst']}")
    print("-" * 30)
    print(f"   ✅ PASSED TRADES:                {stats['passed']}")
    print("="*70)

if __name__ == "__main__":
    debug_filters()
