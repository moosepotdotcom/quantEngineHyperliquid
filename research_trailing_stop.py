
import pandas as pd
import sys
import os
import joblib

# Add root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.v5_feature_engineer import generate_v5_features

def research_trailing_stop():
    print("🚀 Digging Deeper: Trailing Stop Simulation (Infinite Upside?)...")
    
    # 1. Load Data
    data_path = 'training/data/BTC_5m_2025_enriched.csv'
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
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
    
    # 4. Simulation: Trailing Stop
    # Activation: When profit > 2.0%
    # Trail Distance: 0.5%
    # Hard Stop: 0.5%
    
    activation = 0.02
    trail_dist = 0.005
    hard_stop = 0.005
    
    balance = 10000.0
    initial_balance = 10000.0
    
    wins = 0
    losses = 0
    trades = 0
    
    trade_log = []
    
    print(f"   ⚙️  Config: Activate@{activation:.1%}, Trail={trail_dist:.1%}, Stop={hard_stop:.1%}")
    
    in_trade = None
    entry_price = 0
    highest_price = 0
    lowest_price = 0
    
    for i in range(200, len(df_enriched) - 1):
        row = df_enriched.iloc[i]
        
        if in_trade:
            if in_trade == 'LONG':
                # Update High
                if row['high'] > highest_price:
                    highest_price = row['high']
                    
                # Calculate Stop Price
                # If activated, stop is High - Trail
                # Else, stop is Entry - Hard Stop
                
                current_profit_pct = (highest_price - entry_price) / entry_price
                
                stop_price = 0
                if current_profit_pct >= activation:
                    stop_price = highest_price * (1 - trail_dist)
                else:
                    stop_price = entry_price * (1 - hard_stop)
                    
                # Check Exit
                if row['low'] <= stop_price:
                    exit_p = stop_price
                    pnl_pct = (exit_p - entry_price) / entry_price
                    balance *= (1 + pnl_pct)
                    
                    if pnl_pct > 0: wins += 1
                    else: losses += 1
                    
                    in_trade = None
                    trade_log.append(pnl_pct)
                    
            elif in_trade == 'SHORT':
                if row['low'] < lowest_price:
                    lowest_price = row['low']
                    
                current_profit_pct = (entry_price - lowest_price) / entry_price
                
                stop_price = 0
                if current_profit_pct >= activation:
                    stop_price = lowest_price * (1 + trail_dist)
                else:
                    stop_price = entry_price * (1 + hard_stop)
                    
                if row['high'] >= stop_price:
                    exit_p = stop_price
                    pnl_pct = (entry_price - exit_p) / entry_price
                    balance *= (1 + pnl_pct)
                    
                    if pnl_pct > 0: wins += 1
                    else: losses += 1
                    in_trade = None
                    trade_log.append(pnl_pct)
            continue
            
        # Entry (V7 Rules)
        is_high_vol = row['prob_high_vol'] > 0.70
        if not is_high_vol: continue
        
        ema_50 = row.get('ema_50_15m', 0)
        rsi_15m = row.get('rsi_15m', 50)
        imbalance = row.get('flow_imbalance_15m', 0)
        if 'flow_imbalance_15m' not in row: imbalance = row.get('flow_imbalance', 0)
        
        if row['close'] < ema_50 and rsi_15m <= 63:
            in_trade = 'LONG'
            entry_price = row['close']
            highest_price = row['close']
            trades += 1
        elif row['close'] > ema_50 and imbalance < 0.10:
            in_trade = 'SHORT'
            entry_price = row['close']
            lowest_price = row['close']
            trades += 1

    print(f"\n   📊 Results:")
    print(f"   Trades: {trades}")
    print(f"   Wins: {wins}")
    print(f"   Losses: {losses}")
    print(f"   Win Rate: {wins/trades:.1%}" if trades > 0 else "0%")
    print(f"   Final Balance: ${balance:.2f}")
    pnl_total = ((balance/initial_balance) - 1)*100
    print(f"   PnL: {pnl_total:.2f}%")
    
    if trades > 0:
        max_win = max(trade_log) * 100
        print(f"   🚀 BIGGEST WIN: +{max_win:.2f}%")

if __name__ == "__main__":
    research_trailing_stop()
