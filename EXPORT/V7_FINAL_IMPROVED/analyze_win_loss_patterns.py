
import pandas as pd
import sys
import os
import joblib
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.v5_feature_engineer import generate_v5_features

def analyze_win_loss_patterns():
    print("🔬 Deep Analysis: What Separates Winners from Losers?")
    
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
    
    # Simulate trades and collect detailed stats
    tp = 0.005
    sl = 0.0015
    
    trade_records = []
    
    for i in range(200, len(df_enriched) - 48):  # Need future data
        row = df_enriched.iloc[i]
        
        # Entry Logic
        is_high_vol = row['prob_high_vol'] > 0.70
        if not is_high_vol: continue
        
        ema_50 = row.get('ema_50_15m', 0)
        rsi_15m = row.get('rsi_15m', 50)
        imbalance = row.get('flow_imbalance_15m', 0)
        if 'flow_imbalance_15m' not in row: imbalance = row.get('flow_imbalance', 0)
        
        direction = None
        if row['close'] < ema_50 and rsi_15m <= 63:
            direction = 'LONG'
        elif row['close'] > ema_50 and imbalance < 0.10:
            direction = 'SHORT'
        else:
            continue
            
        # Track trade outcome
        entry_price = row['close']
        future = df_enriched.iloc[i+1:i+48]
        
        outcome = 'TIMEOUT'
        exit_candles = 0
        
        for j, (_, candle) in enumerate(future.iterrows()):
            if direction == 'LONG':
                if candle['high'] >= entry_price * (1 + tp):
                    outcome = 'WIN'
                    exit_candles = j + 1
                    break
                if candle['low'] <= entry_price * (1 - sl):
                    outcome = 'LOSS'
                    exit_candles = j + 1
                    break
            else:  # SHORT
                if candle['low'] <= entry_price * (1 - tp):
                    outcome = 'WIN'
                    exit_candles = j + 1
                    break
                if candle['high'] >= entry_price * (1 + sl):
                    outcome = 'LOSS'
                    exit_candles = j + 1
                    break
        
        # Collect features at entry
        trade_records.append({
            'outcome': outcome,
            'direction': direction,
            'prob_vol': row['prob_high_vol'],
            'rsi_15m': rsi_15m,
            'rsi_1h': row.get('rsi_1h', 50),
            'adx_15m': row.get('adx_15m', 0),
            'adx_1h': row.get('adx_1h', 0),
            'cvd_1h': row.get('cvd_1h', 0),
            'volume_delta': row.get('volume_delta', 0),
            'atr_pct': row.get('atr_pct', 0),
            'ema_dist': (row['close'] / ema_50 - 1) * 100,
            'flow_imbalance': imbalance,
            'exit_candles': exit_candles
        })
    
    df_trades = pd.DataFrame(trade_records)
    
    print(f"\n   📊 Total Signals: {len(df_trades)}")
    print(f"   Wins: {len(df_trades[df_trades['outcome']=='WIN'])}")
    print(f"   Losses: {len(df_trades[df_trades['outcome']=='LOSS'])}")
    print(f"   Timeouts: {len(df_trades[df_trades['outcome']=='TIMEOUT'])}")
    
    # Compare Winners vs Losers
    wins = df_trades[df_trades['outcome'] == 'WIN']
    losses = df_trades[df_trades['outcome'] == 'LOSS']
    
    print("\n   🏆 WINNERS vs ❌ LOSERS - Feature Comparison:")
    print("\n   Feature          | Winners (Avg) | Losers (Avg) | Difference")
    print("   " + "-"*65)
    
    for col in ['prob_vol', 'rsi_15m', 'rsi_1h', 'adx_15m', 'adx_1h', 'cvd_1h', 'volume_delta', 'atr_pct', 'ema_dist', 'flow_imbalance']:
        if col in wins.columns and col in losses.columns:
            win_avg = wins[col].mean()
            loss_avg = losses[col].mean()
            diff = win_avg - loss_avg
            print(f"   {col:16} | {win_avg:13.2f} | {loss_avg:12.2f} | {diff:+10.2f}")
    
    # Find the "Golden Filter"
    print("\n   🔍 Testing Additional Filters:")
    
    # Test ADX filter
    for adx_thresh in [20, 25, 30, 35]:
        filtered = df_trades[df_trades['adx_1h'] < adx_thresh]
        if len(filtered) > 0:
            wr = len(filtered[filtered['outcome']=='WIN']) / len(filtered)
            print(f"      ADX_1h < {adx_thresh}: WR={wr:.1%} ({len(filtered)} trades)")
    
    # Test Volume Delta filter
    for vd_thresh in [50, 100, 150, 200]:
        filtered_long = df_trades[(df_trades['direction']=='LONG') & (df_trades['volume_delta'] > vd_thresh)]
        filtered_short = df_trades[(df_trades['direction']=='SHORT') & (df_trades['volume_delta'] < -vd_thresh)]
        filtered = pd.concat([filtered_long, filtered_short])
        if len(filtered) > 0:
            wr = len(filtered[filtered['outcome']=='WIN']) / len(filtered)
            print(f"      |VolDelta| > {vd_thresh}: WR={wr:.1%} ({len(filtered)} trades)")
    
    # Test CVD alignment
    filtered_long = df_trades[(df_trades['direction']=='LONG') & (df_trades['cvd_1h'] > 0)]
    filtered_short = df_trades[(df_trades['direction']=='SHORT') & (df_trades['cvd_1h'] < 0)]
    filtered = pd.concat([filtered_long, filtered_short])
    if len(filtered) > 0:
        wr = len(filtered[filtered['outcome']=='WIN']) / len(filtered)
        print(f"      CVD Aligned: WR={wr:.1%} ({len(filtered)} trades)")

if __name__ == "__main__":
    analyze_win_loss_patterns()
