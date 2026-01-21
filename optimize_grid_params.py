
import pandas as pd
import numpy as np
import joblib
import os
import sys

# Add root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.v5_feature_engineer import generate_v5_features

def run_grid_sim(df, model, conf_thresh, grid_spacing):
    """Runs a single simulation with specific parameters"""
    
    # Pre-calculated probs must be in df
    
    initial_balance = 10000
    balance = initial_balance
    trades = 0
    wins = 0
    blowouts = 0
    
    # Fees (0.01% per leg => 0.02% round trip approx)
    fee_rate = 0.0001
    trade_size = 1000
    
    for i in range(len(df) - 1):
        row = df.iloc[i]
        next_row = df.iloc[i+1]
        
        price = row['close']
        
        # LOGIC
        if row['prob_low'] > conf_thresh:
            # TIGHT GRID MODE
            sell_level = price * (1 + grid_spacing)
            buy_level = price * (1 - grid_spacing)
            
            # Hit Sell?
            if next_row['high'] >= sell_level:
                profit = trade_size * grid_spacing
                fee = trade_size * fee_rate
                balance += (profit - fee)
                trades += 1
                wins += 1
                
            # Hit Buy?
            if next_row['low'] <= buy_level:
                profit = trade_size * grid_spacing
                fee = trade_size * fee_rate
                balance += (profit - fee)
                trades += 1
                wins += 1
                
            # BLOWOUT CHECK
            # If we expected Low Vol, but range > 0.5%, we take a penalty
            next_range = (next_row['high'] - next_row['low']) / next_row['open']
            
            # Only penalize if we actually traded? 
            # Realistically, if we have open orders and price smashes through, we hold a bag.
            # Let's say if range > 2x Grid Spacing, it's a blowout.
            if next_range > (grid_spacing * 3):
                # Major move against us
                loss = trade_size * next_range
                balance -= loss
                trades += 1
                blowouts += 1
                
        # High Vol Mode -> Do nothing
        
    pnl_pct = ((balance / initial_balance) - 1) * 100
    return pnl_pct, trades, blowouts

def optimize_grid():
    print("🚀 Starting Grid Parameter Sweep...")
    
    # 1. Load Data & Model (Once)
    data_path = 'training/data/BTC_5m_2025_enriched.csv'
    model_path = 'model_engines/volatility_v1/weights/vol_model.pkl'
    
    if not os.path.exists(data_path) or not os.path.exists(model_path):
        print("❌ Missing Data/Model")
        return
        
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Features
    print("   🧠 Generating Features...")
    df = generate_v5_features(df)
    
    # Test Set
    df = df[df['timestamp'] >= '2026-01-01'].copy().reset_index(drop=True)
    
    # Batch Predict
    print("   🔮 Batch Predicting...")
    model = joblib.load(model_path)
    features = [c for c in df.columns if c not in ['timestamp', 'target', 'open', 'high', 'low', 'close', 
                                                 'taker_buy_base', 'taker_sell_base', 'future_high', 'future_low', 'future_range_pct', 'prob_low', 'prob_high']]
    probs = model.predict_proba(df[features])
    df['prob_low'] = probs[:, 0]
    
    # 2. Parameter Grid
    confidence_levels = [0.50, 0.60, 0.70]
    spacings = [0.001, 0.002, 0.003, 0.004, 0.005] # 0.1% to 0.5%
    
    results = []
    
    print(f"\n   {'Conf':<10} | {'Spacing':<10} | {'PnL %':<10} | {'Trades':<8} | {'Blowouts':<8}")
    print("-" * 65)
    
    for conf in confidence_levels:
        for space in spacings:
            pnl, n_trades, n_blow = run_grid_sim(df, model, conf, space)
            
            print(f"   {conf:<10} | {space:.1%}       | {pnl:>7.2f}%   | {n_trades:<8} | {n_blow:<8}")
            
            results.append({
                'conf': conf,
                'space': space,
                'pnl': pnl,
                'trades': n_trades,
                'blowouts': n_blow
            })
            
    # Find Best
    best = sorted(results, key=lambda x: x['pnl'], reverse=True)[0]
    print("-" * 65)
    print(f"🏆 BEST SETTING: Conf={best['conf']}, Spacing={best['space']:.1%}")
    print(f"   PnL: {best['pnl']:.2f}% | Trades: {best['trades']} | Blowouts: {best['blowouts']}")
    
    # Most Trades (Positive PnL)
    positive_pnls = [r for r in results if r['pnl'] > 0]
    if positive_pnls:
        most_active = sorted(positive_pnls, key=lambda x: x['trades'], reverse=True)[0]
        print(f"⚡ MOST ACTIVE (Profitable): Conf={most_active['conf']}, Spacing={most_active['space']:.1%}")
        print(f"   PnL: {most_active['pnl']:.2f}% | Trades: {most_active['trades']} | Blowouts: {most_active['blowouts']}")

if __name__ == "__main__":
    optimize_grid()
