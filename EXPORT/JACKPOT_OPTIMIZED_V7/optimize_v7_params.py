
import pandas as pd
import sys
import os
import joblib
import itertools

# Add root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.v5_feature_engineer import generate_v5_features

def optimize_v7_params():
    print("🧪 Optimizing V7 Jackpot Parameters (Risk/Reward Sweep)...")
    
    # 1. Load Data
    data_path = 'training/data/BTC_5m_2025_enriched.csv'
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Filter for Jan 2026
    df = df[df['timestamp'] >= '2026-01-01'].copy().reset_index(drop=True)
    
    # 2. Load Model
    model = joblib.load('model_engines/v6_grid/weights/vol_model.pkl')
    
    # 3. Features
    print("   🧠 Generating Features...")
    df_enriched = generate_v5_features(df)
    
    drop_cols_engine = ['timestamp', 'target', 'open', 'high', 'low', 'close', 
                 'taker_buy_base', 'taker_sell_base', 'future_high', 'future_low', 'future_range_pct',
                 'prob_low', 'prob_high', 'jackpot_label']
                 
    features = [c for c in df_enriched.columns if c not in drop_cols_engine]
    
    probs = model.predict_proba(df_enriched[features])
    df_enriched['prob_high_vol'] = probs[:, 2]
    
    # 4. Sweep Parameters
    # TP: 1.5% to 4.0%
    # SL: 0.5% to 1.5%
    
    tp_range = [0.015, 0.02, 0.025, 0.03, 0.04]
    sl_range = [0.005, 0.0075, 0.01, 0.0125, 0.015]
    
    results = []
    
    print(f"\n   🔄 Testing {len(tp_range) * len(sl_range)} combinations...")
    
    for tp, sl in itertools.product(tp_range, sl_range):
        # Skip invalid RR (we want at least 1:1.5)
        if tp / sl < 1.5: continue
        
        balance = 10000.0
        wins = 0
        losses = 0
        trades = 0
        
        in_trade = None
        entry_price = 0
        
        for i in range(200, len(df_enriched) - 1):
            row = df_enriched.iloc[i]
            
            # Management
            if in_trade:
                if in_trade == 'LONG':
                    if row['high'] >= entry_price * (1 + tp):
                        wins += 1
                        balance *= (1 + tp)
                        in_trade = None
                    elif row['low'] <= entry_price * (1 - sl):
                        losses += 1
                        balance *= (1 - sl)
                        in_trade = None
                elif in_trade == 'SHORT':
                    if row['low'] <= entry_price * (1 - tp):
                        wins += 1
                        balance *= (1 + tp)
                        in_trade = None
                    elif row['high'] >= entry_price * (1 + sl):
                        losses += 1
                        balance *= (1 - sl)
                        in_trade = None
                continue
                
            # Entry Logic (V7 Rules)
            is_high_vol = row['prob_high_vol'] > 0.70
            if not is_high_vol: continue
            
            ema_50 = row.get('ema_50_15m', 0)
            rsi_15m = row.get('rsi_15m', 50)
            imbalance = row.get('flow_imbalance_15m', 0)
            if 'flow_imbalance_15m' not in row: imbalance = row.get('flow_imbalance', 0)
            
            if row['close'] < ema_50 and rsi_15m <= 63:
                in_trade = 'LONG'
                entry_price = row['close']
                trades += 1
            elif row['close'] > ema_50 and imbalance < 0.10:
                in_trade = 'SHORT'
                entry_price = row['close']
                trades += 1
                
        pnl = ((balance / 10000.0) - 1) * 100
        wr = wins / trades if trades > 0 else 0
        rr = tp / sl
        
        results.append({
            "TP": tp,
            "SL": sl,
            "RR": rr,
            "Trades": trades,
            "WR": wr,
            "PnL": pnl
        })
        
    # Sort by PnL
    df_res = pd.DataFrame(results).sort_values(by='PnL', ascending=False)
    
    print("\n   🏆 TOP 5 CONFIGURATIONS:")
    print(df_res.head(5).to_string(index=False))
    
    best = df_res.iloc[0]
    print(f"\n   ✅ BEST: TP={best['TP']:.1%}, SL={best['SL']:.1%}, PnL={best['PnL']:.2f}%")

if __name__ == "__main__":
    optimize_v7_params()
