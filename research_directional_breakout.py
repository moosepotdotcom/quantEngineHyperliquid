
import pandas as pd
import sys
import os
import joblib

# Add root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.v5_feature_engineer import generate_v5_features

def research_directional_breakout():
    print("⚔️  Simulating 'Directional' Breakout Strategy (CVD Filtered)...")
    
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
    
    # Predict High Vol
    drop_cols_engine = ['timestamp', 'target', 'open', 'high', 'low', 'close', 
                 'taker_buy_base', 'taker_sell_base', 'future_high', 'future_low', 'future_range_pct',
                 'prob_low', 'prob_high']
    features = [c for c in df_enriched.columns if c not in drop_cols_engine]
    
    probs = model.predict_proba(df_enriched[features])
    df_enriched['prob_high_vol'] = probs[:, 2]
    
    # 4. Simulation
    # Strategy: 
    # If High Vol (>0.70) AND CVD > 0: Place Buy Stop @ High + 0.1%
    # If High Vol (>0.70) AND CVD < 0: Place Sell Stop @ Low - 0.1%
    # Target: 1.5%
    # Stop: 0.5%
    
    balance = 10000
    profit_target = 0.015
    stop_loss = 0.005
    
    wins = 0
    losses = 0
    skipped = 0
    
    indices = df_enriched[df_enriched['prob_high_vol'] > 0.70].index
    
    print("\n   🚀 Running Simulation...")
    
    for idx in indices:
        if idx >= len(df_enriched) - 48: continue
        
        row = df_enriched.iloc[idx]
        cvd_val = row['cvd_1h']
        
        # Filter: Must mean Business
        # (Optional: Add strength check)
        
        direction = 1 if cvd_val > 0 else -1
        
        # Setup Order
        entry_p = 0
        in_trade = False
        
        trigger_price = 0
        
        if direction == 1:
            trigger_price = row['high'] * 1.001
        else:
            trigger_price = row['low'] * 0.999
            
        # Check Execution
        future = df_enriched.iloc[idx+1:idx+48] # 4 hours
        
        for _, candle in future.iterrows():
            if not in_trade:
                # Try to Enter
                if direction == 1 and candle['high'] > trigger_price:
                    in_trade = True
                    entry_p = trigger_price
                elif direction == -1 and candle['low'] < trigger_price:
                    in_trade = True
                    entry_p = trigger_price
            
            if in_trade:
                # Check Exit
                if direction == 1:
                    if candle['high'] >= entry_p * (1 + profit_target):
                        wins += 1
                        break
                    if candle['low'] <= entry_p * (1 - stop_loss):
                        losses += 1
                        break
                else:
                    if candle['low'] <= entry_p * (1 - profit_target):
                        wins += 1
                        break
                    if candle['high'] >= entry_p * (1 + stop_loss):
                        losses += 1
                        break
                        
    total_trades = wins + losses
    print(f"   Trades: {total_trades}")
    print(f"   Wins: {wins}")
    print(f"   Losses: {losses}")
    if total_trades > 0:
        print(f"   Win Rate: {wins/total_trades:.1%}")
        
        # RR is 1.5 / 0.5 = 3.0
        # Breakeven WR = 25%
        # If WR > 25%, it's profitable.
        
        ev_per_trade = (wins * 1.5) - (losses * 0.5)
        print(f"   Net Points (Unit R): {ev_per_trade:.2f}R")

if __name__ == "__main__":
    research_directional_breakout()
