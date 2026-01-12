
import os
import sys
import pandas as pd
import numpy as np
import joblib

# Setup Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from research.mtf_feature_engineer import MTFFeatureGenerator
from research.mtf_meta_learner_xgb import create_labels

def analyze_stats():
    base_dir = os.path.join(os.path.dirname(__file__), '..', 'datasets')
    model_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'scalp_mtf_xgb.pkl')
    
    # Load Data
    df_5m = pd.read_csv(os.path.join(base_dir, "BTCUSD-5m-max-data.csv"))
    df_15m = pd.read_csv(os.path.join(base_dir, "BTCUSD-15m-max-data.csv"))
    df_30m = pd.read_csv(os.path.join(base_dir, "BTCUSD-30m-max-data.csv"))
    
    # Standardize
    for df in [df_5m, df_15m, df_30m]:
        col = 'datetime' if 'datetime' in df.columns else 'timestamp'
        df[col] = pd.to_datetime(df[col])
        if col != 'datetime': df.rename(columns={col: 'datetime'}, inplace=True)

    # Generate
    gen = MTFFeatureGenerator(df_5m, df_15m, df_30m)
    df = gen.generate()
    # We need to recreate the "Outcome" to measure actual movement, not just binary target
    
    # Predict
    model = joblib.load(model_path)
    features = [c for c in df.columns if c not in ['open', 'high', 'low', 'close', 'volume', 'target', 'dividends', 'stock splits', 'open_15m', 'close_15m', 'high_15m', 'low_15m', 'volume_15m', 'open_30m', 'close_30m']]
    X = df[features]
    probs = model.predict_proba(X)[:, 1]
    
    # Filter for signals
    THRESHOLD = 0.75
    signals = probs > THRESHOLD
    
    df['signal'] = signals
    
    # Analyze Moves
    trades = []
    closes = df['close'].values
    highs = df['high'].values
    lows = df['low'].values
    times = df.index # or df['datetime'] if index is not set
    
    hold_period = 24 # 2 hours max
    tp_pct = 0.005
    sl_pct = 0.005
    
    total_points = 0
    total_pct = 0
    wins = 0
    losses = 0
    
    for i in np.where(signals)[0]:
        if i >= len(df) - hold_period: continue
        
        entry_price = closes[i]
        tp_price = entry_price * (1 + tp_pct)
        sl_price = entry_price * (1 - sl_pct)
        
        outcome = 0 # 0=running/timed_out, 1=win, -1=loss
        exit_price = closes[i+hold_period] # Default exit at time limit
        
        # Check hitting bounds
        window_h = highs[i+1 : i+1+hold_period]
        window_l = lows[i+1 : i+1+hold_period]
        
        # Find index of first hit
        # We need relative index
        hit_tp_idx = np.where(window_h >= tp_price)[0]
        hit_sl_idx = np.where(window_l <= sl_price)[0]
        
        first_tp = hit_tp_idx[0] if len(hit_tp_idx) > 0 else 9999
        first_sl = hit_sl_idx[0] if len(hit_sl_idx) > 0 else 9999
        
        if first_tp < first_sl:
            # Win
            outcome = 1
            exit_price = tp_price
            wins += 1
        elif first_sl < first_tp:
            # Loss
            outcome = -1
            exit_price = sl_price
            losses += 1
        else:
            # Timed out clearly
            pass
            
        pnl_pct = (exit_price - entry_price) / entry_price
        pnl_points = exit_price - entry_price
        
        trades.append({
            'entry': entry_price,
            'exit': exit_price,
            'pnl_pct': pnl_pct,
            'pnl_points': pnl_points,
            'outcome': outcome
        })
        
        total_points += pnl_points
        total_pct += pnl_pct
        
    avg_pct = total_pct / len(trades) if trades else 0
    avg_points = total_points / len(trades) if trades else 0
    win_rate = wins / len(trades) if trades else 0
    
    print(f"STATS FOR THRESHOLD {THRESHOLD}")
    print(f"Total Trades: {len(trades)}")
    print(f"Win Rate: {win_rate:.2%}")
    print(f"Average PnL: {avg_pct:.4%} per trade")
    print(f"Average Points: {avg_points:.2f} BTC points")
    print(f"Projected Daily Points (approx): {avg_points * (len(trades)/(len(df)/288)):.2f}")

if __name__ == "__main__":
    analyze_stats()
