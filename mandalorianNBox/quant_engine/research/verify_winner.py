#!/usr/bin/env python3
"""
📊 Winner Verification
Backtests the Winner Hunter model to confirm win rate.
"""

import os
import pandas as pd
import numpy as np
import xgboost as xgb

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')

def verify_model(timeframe='1h', threshold=0.90, tp_pct=0.015, sl_pct=0.008, lookahead=12):
    """Verify model performance with realistic simulation"""
    
    print(f"\n📊 Verifying Winner Hunter ({timeframe}) @ {threshold:.0%} Threshold")
    print("="*60)
    
    # Load model
    model_path = os.path.join(MODEL_DIR, f'winner_hunter_{timeframe}.json')
    if not os.path.exists(model_path):
        print(f"❌ Model not found: {model_path}")
        return
    
    model = xgb.XGBClassifier()
    model.load_model(model_path)
    print(f"✅ Model loaded: {model_path}")
    
    # Load data
    data_path = os.path.join(DATA_DIR, f'BTC_{timeframe}_features.csv')
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Feature columns
    exclude_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'target']
    feature_cols = [c for c in df.columns if c not in exclude_cols]
    
    # Simulation
    wins = 0
    losses = 0
    trades = []
    total_pnl = 0
    
    for i in range(len(df) - lookahead):
        row = df.iloc[i]
        features = row[feature_cols].values.reshape(1, -1)
        
        # Get prediction
        try:
            prob = model.predict_proba(features)[0][1]
        except:
            continue
        
        if prob >= threshold:
            entry_price = row['close']
            tp_price = entry_price * (1 + tp_pct)
            sl_price = entry_price * (1 - sl_pct)
            
            # Check future bars
            outcome = None
            exit_price = entry_price
            
            for j in range(1, lookahead + 1):
                if i + j >= len(df):
                    break
                future = df.iloc[i + j]
                
                # Check SL first
                if future['low'] <= sl_price:
                    outcome = 'LOSS'
                    exit_price = sl_price
                    losses += 1
                    break
                # Check TP
                if future['high'] >= tp_price:
                    outcome = 'WIN'
                    exit_price = tp_price
                    wins += 1
                    break
            
            if outcome is None:
                # No outcome within lookahead
                exit_price = df.iloc[min(i + lookahead, len(df) - 1)]['close']
                if exit_price > entry_price:
                    outcome = 'WIN'
                    wins += 1
                else:
                    outcome = 'LOSS'
                    losses += 1
            
            pnl = (exit_price - entry_price) / entry_price
            points = exit_price - entry_price
            total_pnl += pnl
            
            trades.append({
                'timestamp': row['timestamp'],
                'entry': entry_price,
                'exit': exit_price,
                'points': points,
                'confidence': prob,
                'outcome': outcome,
                'pnl': pnl
            })
    
    # Results
    total_trades = wins + losses
    win_rate = wins / total_trades if total_trades > 0 else 0
    
    print(f"\n📈 RESULTS:")
    print(f"   Total Trades: {total_trades}")
    print(f"   Wins: {wins} | Losses: {losses}")
    print(f"   Win Rate: {win_rate:.2%}")
    print(f"   Total PnL: {total_pnl*100:.2f}%")
    print(f"   Avg PnL/Trade: {(total_pnl/total_trades)*100:.3f}%" if total_trades > 0 else "   Avg PnL: N/A")
    
    if trades:
        trades_df = pd.DataFrame(trades)
        days = (trades_df['timestamp'].max() - trades_df['timestamp'].min()).days
        days = max(days, 1)
        total_points = trades_df['points'].sum()
        avg_points_per_trade = trades_df['points'].mean()
        avg_points_per_day = total_points / days
        
        print(f"   Trades/Day: {total_trades/days:.2f}")
        print(f"   Avg Confidence: {trades_df['confidence'].mean():.2%}")
        print(f"   Total Points: ${total_points:,.2f}")
        print(f"   Avg Points/Trade: ${avg_points_per_trade:,.2f}")
        print(f"   Avg Points/Day: ${avg_points_per_day:,.2f}")
    
    return win_rate, total_trades, total_pnl

def find_best_threshold(timeframe='1h'):
    """Find the threshold that maximizes win rate while maintaining frequency"""
    
    print(f"\n🔍 Finding Optimal Threshold for {timeframe}...")
    
    results = []
    for thresh in np.arange(0.5, 1.0, 0.05):
        wr, trades, pnl = verify_model(timeframe, thresh)
        results.append({'threshold': thresh, 'win_rate': wr, 'trades': trades, 'pnl': pnl})
    
    results_df = pd.DataFrame(results)
    print("\n" + "="*60)
    print("📋 THRESHOLD ANALYSIS:")
    print(results_df.to_string(index=False))
    
    # Find sweet spot (highest WR with at least 5 trades)
    viable = results_df[results_df['trades'] >= 5]
    if len(viable) > 0:
        best = viable.loc[viable['win_rate'].idxmax()]
        print(f"\n🏆 BEST: Threshold={best['threshold']:.0%} | WR={best['win_rate']:.2%} | Trades={best['trades']}")
    
    return results_df

if __name__ == '__main__':
    # Verify the 1H model (best from training)
    verify_model('1h', threshold=0.90)
    
    # Find optimal threshold
    find_best_threshold('1h')
