
import pandas as pd
import sys
import os
import joblib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.v5_feature_engineer import generate_v5_features

def test_improved_v7():
    print("🚀 Testing IMPROVED V7 with Golden Filters...")
    
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
    
    # Parameters
    tp = 0.005
    sl = 0.0015
    
    balance = 10000.0
    wins = 0
    losses = 0
    trades = 0
    
    in_trade = None
    entry_price = 0
    
    print("\n   ⚡ NEW FILTERS:")
    print("      1. CVD must align with direction")
    print("      2. |Volume Delta| > 50")
    print("      3. RSI < 55 (not overbought)")
    print("\n   🚀 Running Simulation...")
    
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
            
        # Entry Logic (IMPROVED V7)
        is_high_vol = row['prob_high_vol'] > 0.70
        if not is_high_vol: continue
        
        ema_50 = row.get('ema_50_15m', 0)
        rsi_15m = row.get('rsi_15m', 50)
        rsi_1h = row.get('rsi_1h', 50)
        imbalance = row.get('flow_imbalance_15m', 0)
        if 'flow_imbalance_15m' not in row: imbalance = row.get('flow_imbalance', 0)
        
        cvd_1h = row.get('cvd_1h', 0)
        volume_delta = row.get('volume_delta', 0)
        
        # LONG Signal (IMPROVED)
        if (row['close'] < ema_50 and 
            rsi_15m <= 63 and
            rsi_1h < 55 and  # NEW: Not overbought on 1h
            cvd_1h > 0 and  # NEW: Buyers in control
            volume_delta > 50):  # NEW: Strong buying pressure
            
            in_trade = 'LONG'
            entry_price = row['close']
            trades += 1
            
        # SHORT Signal (IMPROVED)
        elif (row['close'] > ema_50 and 
              imbalance < 0.10 and
              rsi_1h > 45 and  # NEW: Not oversold on 1h
              cvd_1h < 0 and  # NEW: Sellers in control
              volume_delta < -50):  # NEW: Strong selling pressure
            
            in_trade = 'SHORT'
            entry_price = row['close']
            trades += 1
    
    print(f"\n   📊 RESULTS:")
    print(f"   Trades: {trades}")
    print(f"   Wins: {wins}")
    print(f"   Losses: {losses}")
    
    if trades > 0:
        wr = wins / trades
        print(f"   Win Rate: {wr:.1%}")
        print(f"   Trades/Day: {trades/14:.1f}")
        pnl = ((balance/10000.0) - 1) * 100
        print(f"   PnL: {pnl:.2f}%")
        
        # Compare to original
        print(f"\n   📈 IMPROVEMENT:")
        print(f"      Original WR: 29.8%")
        print(f"      New WR: {wr:.1%}")
        print(f"      Gain: +{(wr-0.298)*100:.1f} percentage points")

if __name__ == "__main__":
    test_improved_v7()
