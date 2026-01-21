
import pandas as pd
import sys
import os
import joblib

# Add root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.v5_feature_engineer import generate_v5_features

def research_breakouts():
    print("🔎 Researching High Volatility Breakouts...")
    
    # 1. Load Data
    data_path = 'training/data/BTC_5m_2025_enriched.csv'
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Filter for Jan 2026 (Test Set)
    df = df[df['timestamp'] >= '2026-01-01'].copy().reset_index(drop=True)
    
    # 2. Load Volatility Model
    model_path = 'model_engines/v6_grid/weights/vol_model.pkl'
    if not os.path.exists(model_path):
        print("❌ Model not found")
        return
    model = joblib.load(model_path)
    
    # 3. Generate Features
    print("   🧠 Generating Features...")
    df_enriched = generate_v5_features(df)
    
    # Drop non-feature columns for prediction
    feature_cols = [c for c in df_enriched.columns if c not in [
        'timestamp', 'target', 'open', 'high', 'low', 'close', 
        'taker_buy_base', 'taker_sell_base', 'future_high', 'future_low', 'future_range_pct',
        'prob_low', 'prob_high', 'volume_delta', 'cvd_1h', 'cvd_4h' 
    ]]
    
    # Actually, we need to match the exact feature set used in training.
    # The safest way is to check the feature names from the model if possible,
    # or rely on the same dropped columns as V6GridEngine.
    
    # From V6GridEngine:
    drop_cols_engine = ['timestamp', 'target', 'open', 'high', 'low', 'close', 
                 'taker_buy_base', 'taker_sell_base', 'future_high', 'future_low', 'future_range_pct',
                 'prob_low', 'prob_high']
    
    features = [c for c in df_enriched.columns if c not in drop_cols_engine]
    
    print("   🔮 Predicting Volatility Regimes...")
    probs = model.predict_proba(df_enriched[features])
    
    df_enriched['prob_high_vol'] = probs[:, 2] # Class 2 = High Vol
    
    # 4. Analyze High Volatility Follow-through
    print("\n   📊 Analysis: Behavior AFTER High Volatility Signal (Prob > 0.70)")
    
    threshold = 0.70
    signal_indices = df_enriched[df_enriched['prob_high_vol'] > threshold].index
    
    trends = []
    
    for idx in signal_indices:
        if idx >= len(df_enriched) - 24: # Need 2h of future data
            continue
            
        current_candle = df_enriched.iloc[idx]
        future_window = df_enriched.iloc[idx+1:idx+25] # Next 2 hours (24 candles)
        
        entry_price = current_candle['close']
        
        # Max Excursion
        max_high = future_window['high'].max()
        min_low = future_window['low'].min()
        
        pct_up = (max_high - entry_price) / entry_price
        pct_down = (entry_price - min_low) / entry_price
        
        # Did it move more than 1%?
        big_move = max(pct_up, pct_down) > 0.01
        
        trends.append({
            "timestamp": current_candle['timestamp'],
            "prob_high_vol": current_candle['prob_high_vol'],
            "pct_up": pct_up,
            "pct_down": pct_down,
            "big_move": big_move
        })
        
    res = pd.DataFrame(trends)
    
    if len(res) == 0:
        print("   ⚠️ No High Vol signals found.")
        return

    print(f"   Signals Found: {len(res)}")
    print(f"   Big Moves (>1% in 2h): {res['big_move'].sum()} ({res['big_move'].mean():.1%})")
    print(f"   Avg Up Move: {res['pct_up'].mean():.2%}")
    print(f"   Avg Down Move: {res['pct_down'].mean():.2%}")
    
    # 5. Simulate Breakout Strategy
    # Strategy: Buy Stop @ High + 0.1%, Sell Stop @ Low - 0.1% of Signal Candle
    print("\n   ⚔️  Simulating 'Straddle' Breakout Strategy...")
    
    balance = 10000
    profit_target = 0.015 # 1.5% Target
    stop_loss = 0.005 # 0.5% SL
    
    wins = 0
    losses = 0
    
    for idx in signal_indices:
        if idx >= len(df_enriched) - 48: continue
        
        row = df_enriched.iloc[idx]
        
        # Setup Straddle
        buy_trigger = row['high'] * 1.001
        sell_trigger = row['low'] * 0.999
        
        # Check next candles for trigger
        in_trade = None # 'LONG' or 'SHORT'
        entry_p = 0
        
        future = df_enriched.iloc[idx+1:idx+48] # 4 hours validity
        
        for _, candle in future.iterrows():
            if in_trade is None:
                # Check Triggers
                if candle['high'] > buy_trigger:
                    in_trade = 'LONG'
                    entry_p = buy_trigger
                elif candle['low'] < sell_trigger:
                    in_trade = 'SHORT'
                    entry_p = sell_trigger
            
            if in_trade == 'LONG':
                # Check Exit
                if candle['high'] >= entry_p * (1 + profit_target):
                    wins += 1
                    break
                if candle['low'] <= entry_p * (1 - stop_loss):
                    losses += 1
                    break
                    
            elif in_trade == 'SHORT':
                if candle['low'] <= entry_p * (1 - profit_target):
                    wins += 1
                    break
                if candle['high'] >= entry_p * (1 + stop_loss):
                    losses += 1
                    break
                    
    print(f"   Trades Taken: {wins + losses}")
    print(f"   Wins (Target {profit_target*100}%): {wins}")
    print(f"   Losses (SL {stop_loss*100}%): {losses}")
    if (wins+losses) > 0:
        print(f"   Win Rate: {wins/(wins+losses):.1%}")

if __name__ == "__main__":
    research_breakouts()
