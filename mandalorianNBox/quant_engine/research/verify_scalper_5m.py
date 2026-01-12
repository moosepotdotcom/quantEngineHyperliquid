#!/usr/bin/env python3
"""
📊 MTF Scalper Verification (5m)
"""

import os
import pandas as pd
import xgboost as xgb

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')

def verify_scalper(threshold=0.90):
    print(f"\n📊 Verifying 5M MTF Scalper @ {threshold:.0%} Threshold")
    print("="*60)
    
    # Load model
    model = xgb.XGBClassifier()
    model.load_model(os.path.join(MODEL_DIR, 'mtf_scalper_5m.json'))
    
    # Load data
    df = pd.read_csv(os.path.join(DATA_DIR, 'BTC_MTF_scalper_5m.csv'))
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Features
    exclude = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    features = [c for c in df.columns if c not in exclude]
    
    # Simulate
    wins, losses, trades = 0, 0, []
    tp_pct, sl_pct, lookahead = 0.008, 0.005, 8
    
    for i in range(len(df) - lookahead):
        row = df.iloc[i]
        X = row[features].values.reshape(1, -1)
        
        try:
            prob = model.predict_proba(X)[0][1]
        except:
            continue
        
        if prob >= threshold:
            entry = row['close']
            tp = entry * (1 + tp_pct)
            sl = entry * (1 - sl_pct)
            
            outcome = None
            exit_price = entry
            
            for j in range(1, lookahead + 1):
                if i + j >= len(df):
                    break
                future = df.iloc[i + j]
                
                if future['low'] <= sl:
                    outcome, exit_price = 'LOSS', sl
                    losses += 1
                    break
                if future['high'] >= tp:
                    outcome, exit_price = 'WIN', tp
                    wins += 1
                    break
            
            if outcome is None:
                exit_price = df.iloc[min(i + lookahead, len(df) - 1)]['close']
                outcome = 'WIN' if exit_price > entry else 'LOSS'
                wins += 1 if outcome == 'WIN' else 0
                losses += 1 if outcome == 'LOSS' else 0
            
            points = exit_price - entry
            trades.append({
                'timestamp': row['timestamp'],
                'entry': entry,
                'exit': exit_price,
                'points': points,
                'outcome': outcome,
                'confidence': prob
            })
    
    # Results
    total = wins + losses
    wr = wins / total if total > 0 else 0
    
    if trades:
        trades_df = pd.DataFrame(trades)
        days = (trades_df['timestamp'].max() - trades_df['timestamp'].min()).days
        days = max(days, 1)
        total_points = trades_df['points'].sum()
        
        print(f"\n📈 RESULTS:")
        print(f"   Total Trades: {total}")
        print(f"   Wins: {wins} | Losses: {losses}")
        print(f"   Win Rate: {wr:.2%}")
        print(f"   Trades/Day: {total/days:.2f}")
        print(f"   Avg Confidence: {trades_df['confidence'].mean():.2%}")
        print(f"   Total Points: ${total_points:,.2f}")
        print(f"   Avg Points/Trade: ${trades_df['points'].mean():,.2f}")
        print(f"   Avg Points/Day: ${total_points/days:,.2f}")
    
    return wr, total

if __name__ == '__main__':
    # Test multiple thresholds
    print("\n🔍 THRESHOLD SWEEP:")
    for thresh in [0.5, 0.7, 0.8, 0.9, 0.95]:
        wr, trades = verify_scalper(thresh)
        print(f"   {thresh:.0%}: WR={wr:.2%}, Trades={trades}")
