
import pandas as pd
import sys
import os
import joblib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.v5_feature_engineer import generate_v5_features

def optimize_filter_strength():
    print("🎯 Finding the Sweet Spot for Filters...")
    
    # Load Data
    data_path = 'training/data/BTC_5m_2025_enriched.csv'
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df[df['timestamp'] >= '2026-01-01'].copy().reset_index(drop=True)
    
    # Load Model
    model = joblib.load('model_engines/v6_grid/weights/vol_model.pkl')
    
    print("   🧠 Generating Features...")
    df_enriched = generate_v5_features(df)
    
    drop_cols_engine = ['timestamp', 'target', 'open', 'high', 'low', 'close', 
                 'taker_buy_base', 'taker_sell_base', 'future_high', 'future_low', 'future_range_pct',
                 'prob_low', 'prob_high', 'jackpot_label']
    features = [c for c in df_enriched.columns if c not in drop_cols_engine]
    
    probs = model.predict_proba(df_enriched[features])
    df_enriched['prob_high_vol'] = probs[:, 2]
    
    # Test different Volume Delta thresholds
    print("\n   🔄 Testing Volume Delta Thresholds:")
    
    for vd_thresh in [0, 10, 20, 30, 40, 50]:
        tp = 0.005
        sl = 0.0015
        
        balance = 10000.0
        wins = 0
        losses = 0
        trades = 0
        
        in_trade = None
        entry_price = 0
        
        for i in range(200, len(df_enriched) - 1):
            row = df_enriched.iloc[i]
            
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
                
            # Entry
            is_high_vol = row['prob_high_vol'] > 0.70
            if not is_high_vol: continue
            
            ema_50 = row.get('ema_50_15m', 0)
            rsi_15m = row.get('rsi_15m', 50)
            rsi_1h = row.get('rsi_1h', 50)
            imbalance = row.get('flow_imbalance_15m', 0)
            if 'flow_imbalance_15m' not in row: imbalance = row.get('flow_imbalance', 0)
            
            cvd_1h = row.get('cvd_1h', 0)
            volume_delta = row.get('volume_delta', 0)
            
            # LONG (with adjustable filter)
            if (row['close'] < ema_50 and 
                rsi_15m <= 63 and
                rsi_1h < 60 and  # Relaxed from 55
                cvd_1h > 0 and
                volume_delta > vd_thresh):
                
                in_trade = 'LONG'
                entry_price = row['close']
                trades += 1
                
            # SHORT (with adjustable filter)
            elif (row['close'] > ema_50 and 
                  imbalance < 0.10 and
                  rsi_1h > 40 and  # Relaxed from 45
                  cvd_1h < 0 and
                  volume_delta < -vd_thresh):
                
                in_trade = 'SHORT'
                entry_price = row['close']
                trades += 1
        
        if trades > 0:
            wr = wins / trades
            pnl = ((balance/10000.0) - 1) * 100
            print(f"      VD > {vd_thresh:2d}: Trades={trades:2d}, WR={wr:.1%}, PnL={pnl:+.2f}%")

if __name__ == "__main__":
    optimize_filter_strength()
