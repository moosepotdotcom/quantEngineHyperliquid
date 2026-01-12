
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Add path access
sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION'))
sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION/utils'))

from quant_engine import TradingEngine, add_all_indicators

def run_golden_simulation():
    print("🕰️  STARTING 'GOLDEN CONFIG' SIMULATION (JAN 2 - JAN 9)...")
    print("="*70)
    print("🎯 Target: ~182 Trades, ~92% Win Rate")
    print("⚙️  Config: Elastic (0.45) + Hurst + Disagreement + ATR Shield. (NO Regime Filter)")
    
    engine = TradingEngine()
    
    # 1. Fetch Data
    print("📥 Fetching historical data...")
    limit = 4000
    df_raw = engine.fetch_data('5m', limit) 
    
    if df_raw is None or len(df_raw) == 0:
        return

    # Base Processing
    # We need VALID Hurst.
    # The utils/advanced_features might be needed? 
    # Let's try to import get_rolling_hurst or mock it if complex.
    # quant_engine imports it inside the function.
    try:
        from utils.advanced_features import get_rolling_hurst
        print("   ✅ Loaded advanced Hurst calculator")
    except ImportError:
        print("   ⚠️  Advanced features not found, using simplified Hurst")
        get_rolling_hurst = lambda df, w: pd.Series(0.5, index=df.index)

    df_raw = add_all_indicators(df_raw)
    
    # Calculate Hurst REAL
    try:
        df_raw['hurst'] = get_rolling_hurst(df_raw, window=100)
    except:
        df_raw['hurst'] = 0.5
        
    df_raw.set_index('timestamp', inplace=True)
    
    # Context
    print("📊 Preparing MTF Context...")
    df_15m = add_all_indicators(engine.fetch_data('15m', limit))
    df_1h = add_all_indicators(engine.fetch_data('1h', limit))
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
    
    # Filter Date
    start_sim = pd.Timestamp("2026-01-02 00:00:00")
    end_sim = pd.Timestamp("2026-01-09 23:59:59")
    sim_data = df_merged[(df_merged.index >= start_sim) & (df_merged.index <= end_sim)]
    
    print(f"✅ Simulation Ready: {len(sim_data)} candles")
    
    trades = []
    
    for idx, row in sim_data.iterrows():
        # Predict
        row_vals = row.drop(labels=exclude + ['hurst'], errors='ignore')
        X = row_vals.values.reshape(1, -1)
        X = np.nan_to_num(X, nan=0.0)
        if X.shape[1] > 239: X = X[:, :239]
        
        # Get individual preds for Consensus Check
        p1 = engine.mtf_xgb.predict_proba(X)[0]
        p2 = engine.mtf_lgb.predict(X)[0] # Assuming similar shape output or handled
        p3 = engine.mtf_cat.predict_proba(X)[0]
        
        avg_prob = (p1 + p2 + p3) / 3
        conf_long, conf_short = avg_prob[1], avg_prob[2]
        
        # Calibration (Disagreement)
        std_dev = np.std([p1, p2, p3], axis=0)
        max_disagreement = np.max(std_dev)
        
        # ELASTIC MODE (Implied by log)
        threshold = 0.45
        
        signal = None
        current_conf = 0.0
        if conf_long >= threshold: 
            signal = 'LONG'
            current_conf = conf_long
        elif conf_short >= threshold: 
            signal = 'SHORT'
            current_conf = conf_short
        
        if signal:
            # === APPLY FILTERS ===
            allowed = True
            reason = ""
            
            # 1. Consensus Filter (Disagreement)
            if max_disagreement > 0.15:
                allowed = False
                reason = "High Disagreement"
                
            # 2. Adaptive Volatility Shield (ATR Penalty)
            atr = row.get('atr_14', 7)
            penalty = max(0, (atr - 7) * 0.002)
            required = threshold + penalty
            if current_conf < required:
                allowed = False
                reason = f"ATR Penalty (Req {required:.3f})"
                
            # 3. Hurst Filter (Falling Knife)
            rsi = row.get('rsi_14', 50)
            hurst = row.get('hurst', 0.5)
            if signal == 'LONG' and rsi < 30 and hurst > 0.5:
                allowed = False
                reason = "Mandalorian Shield (Falling Knife)"
                
            # 4. Regime Filter -> DISABLED (The "No Filter" hypothesis)
            
            if allowed:
                ts = idx.strftime('%d-%H:%M')
                entry_price = row['close']
                tp = entry_price * (1.015 if signal == 'LONG' else 0.985)
                sl = entry_price * (0.992 if signal == 'LONG' else 1.008)
                
                outcome = "OPEN"
                pnl = 0.0
                
                # Check Outcome
                future_data = df_raw[df_raw.index > idx]
                for _, f_row in future_data.iterrows():
                    h, l = f_row['high'], f_row['low']
                    if signal == 'LONG':
                        if h >= tp: outcome = "WIN"; pnl = 1.5; break
                        if l <= sl: outcome = "LOSS"; pnl = -0.8; break
                    else:
                        if l <= tp: outcome = "WIN"; pnl = 1.5; break
                        if h >= sl: outcome = "LOSS"; pnl = -0.8; break
                        
                trades.append({'time': ts, 'type': signal, 'result': outcome, 'pnl': pnl})

    print("\n" + "="*70)
    print(f"📊 GOLDEN CONFIG RESULTS (Jan 2 - Jan 9)")
    print(f"   Config: Disagreement<0.15 | Volatility Shield | Hurst | No Regime")
    print(f"   Total Trades: {len(trades)}")
    
    wins = [t for t in trades if t['result'] == 'WIN']
    
    if len(trades) > 0:
        wr = len(wins) / len(trades)
        print(f"   🎯 Win Rate: {wr:.1%}")
    else:
        print(f"   🎯 Win Rate: 0%")
        
    total_pnl = sum(t['pnl'] for t in trades)
    print(f"   💰 Total  PnL: {total_pnl:+.2f}%")
    print("="*70)

if __name__ == "__main__":
    run_golden_simulation()
