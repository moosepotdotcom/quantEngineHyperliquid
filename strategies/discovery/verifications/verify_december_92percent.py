
import pandas as pd
import numpy as np
import sys
import os
import warnings
warnings.filterwarnings('ignore')

sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION'))
sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION/utils'))

from quant_engine import TradingEngine

def verify_december_92percent():
    print("🚀 GEM SNIPER: DECEMBER 2025 (92% CONFIG - NO FILTER)")
    print("="*70)
    print("⚙️  Settings: Threshold 0.45 | ATR Filter: DISABLED")
    
    # Initialize Engine
    print("📦 Loading Trio Ensemble Models...")
    engine = TradingEngine()
    
    csv_path = 'training/data/BTC_5m_mtf_features.csv'
    try:
        # Load efficiently
        df_raw = pd.read_csv(csv_path)
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return

    # Parse dates
    df_raw['timestamp'] = pd.to_datetime(df_raw['timestamp'])
    df_raw.set_index('timestamp', inplace=True)
    df_raw.sort_index(inplace=True)
    
    # Filter for December 2025
    start_sim = pd.Timestamp("2025-12-01 00:00:00")
    end_sim = pd.Timestamp("2025-12-31 23:59:59")
    
    sim_data = df_raw[(df_raw.index >= start_sim) & (df_raw.index <= end_sim)]
    print(f"✅ Simulation Ready: {len(sim_data)} candles (December 2025)")
    
    # Force Float
    cols = ['open', 'high', 'low', 'close', 'volume']
    for c in cols:
        sim_data[c] = pd.to_numeric(sim_data[c], errors='coerce')
    
    trades = []
    
    print(f"\n{'TIME':<20} | {'SIDE':<5} | {'ENTRY':<10} | {'TP':<10} | {'SL':<10} | {'ATR':<6} | {'DUR':<5} | {'PnL':<10} | {'OUTCOME'}")
    print("-" * 110)
    
    exclude = ['open', 'high', 'low', 'close', 'volume', 'hurst']
    
    for idx, row in sim_data.iterrows():
        # Predict
        row_vals = row.drop(labels=exclude + ['hurst'], errors='ignore')
        X = row_vals.values.reshape(1, -1)
        X = np.nan_to_num(X, nan=0.0)
        
        # PADDING FIX
        if X.shape[1] > 239: 
            X = X[:, :239]
        elif X.shape[1] < 239:
            X = np.pad(X, ((0,0), (0, 239 - X.shape[1])), 'constant')
        
        p1 = engine.mtf_xgb.predict_proba(X)[0]
        p2 = engine.mtf_lgb.predict(X)[0]
        p3 = engine.mtf_cat.predict_proba(X)[0]
        
        avg_prob = (p1 + p2 + p3) / 3
        conf_long, conf_short = avg_prob[1], avg_prob[2]
        
        atr_val = row.get('atr_14', 0)
        
        # LOGIC: Fixed 0.45 Threshold, NO Regime Filter
        threshold = 0.45
        signal = None
        
        if conf_long >= threshold: signal = 'LONG'
        elif conf_short >= threshold: signal = 'SHORT'
        
        if signal:
            # NO ATR CHECK - TAKING THE TRADE
            
            entry_price = row['close']
            tp = entry_price * (1.015 if signal == 'LONG' else 0.985)
            sl = entry_price * (0.992 if signal == 'LONG' else 1.008)
            
            outcome = "OPEN"
            pnl_val = 0.0
            duration = 0
            
            # Future Outcome
            future_data = sim_data[sim_data.index > idx]
            
            # Simple simulation loop
            for f_idx, f_row in future_data.iterrows():
                duration += 1 # 5m candles
                h, l = f_row['high'], f_row['low']
                
                if signal == 'LONG':
                    if h >= tp: 
                        outcome = "WIN"
                        pnl_val = (tp - entry_price) 
                        break
                    if l <= sl: 
                        outcome = "LOSS"
                        pnl_val = (sl - entry_price)
                        break
                else:
                    if l <= tp: 
                        outcome = "WIN"
                        pnl_val = (entry_price - tp)
                        break
                    if h >= sl: 
                        outcome = "LOSS"
                        pnl_val = (entry_price - sl)
                        break
                
                # Timeout / End of Data
                if duration > 500: # Force close after ~40 hours if stuck
                     outcome = "TIMEOUT"
                     close_price = f_row['close']
                     pnl_val = (close_price - entry_price) if signal == 'LONG' else (entry_price - close_price)
                     break
            
            ts = idx.strftime('%Y-%m-%d %H:%M')
            dur_str = f"{duration*5}m"
            
            # Color/Format
            outcome_str = f"✅ {outcome}" if outcome == "WIN" else f"❌ {outcome}"
            
            print(f"{ts:<20} | {signal:<5} | {entry_price:<10.2f} | {tp:<10.2f} | {sl:<10.2f} | {atr_val:<6.1f} | {dur_str:<5} | {pnl_val:<10.2f} | {outcome_str}")
            
            trades.append({'time': ts, 'result': outcome, 'pnl': pnl_val})

    print("-" * 110)
    print(f"📊 DECEMBER RESULT (92% Config)")
    print(f"   Total Trades: {len(trades)}")
    
    if len(trades) > 0:
        wins = [t for t in trades if t['result'] == 'WIN']
        wr = len(wins) / len(trades)
        print(f"   🎯 Win Rate: {wr:.1%}")
        
        total_pnl = sum(t['pnl'] for t in trades)
        print(f"   💰 Total PnL (Points): {total_pnl:+.2f}")
    else:
        print("   No Trades taken.")

if __name__ == "__main__":
    verify_december_92percent()
