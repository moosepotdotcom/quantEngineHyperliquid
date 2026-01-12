#!/usr/bin/env python3
"""
📊 Backtest Trade Data Exporter
Generates detailed trade logs from backtest results.
"""

import os
import sys
import pandas as pd
import numpy as np
import xgboost as xgb
import json
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'utils'))

from feature_engineer import add_all_indicators

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')

def generate_backtest_trades(model_name='winner_hunter_1h', timeframe='1h', threshold=0.95):
    """Generate detailed trade log from backtest"""
    
    print(f"\n📊 Generating Backtest Trade Data: {model_name}")
    print("="*70)
    
    # Load model
    model = xgb.XGBClassifier()
    model.load_model(os.path.join(MODEL_DIR, f'{model_name}.json'))
    
    # Load data
    data_path = os.path.join(DATA_DIR, f'BTC_{timeframe}_features.csv')
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Parameters
    tp_pct = 0.015  # 1.5%
    sl_pct = 0.008  # 0.8%
    lookahead = 12  # bars
    
    # Generate predictions
    exclude = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    features = [c for c in df.columns if c not in exclude]
    
    trades = []
    trade_id = 1
    
    for i in range(len(df) - lookahead):
        row = df.iloc[i]
        
        # Get prediction
        try:
            X = row[features].values.reshape(1, -1)
            prob = model.predict_proba(X)[0][1]
        except:
            continue
        
        if prob >= threshold:
            # Signal detected
            entry_price = row['close']
            tp_price = entry_price * (1 + tp_pct)
            sl_price = entry_price * (1 - sl_pct)
            
            # Check outcome
            outcome = None
            exit_price = entry_price
            exit_bar = None
            
            for j in range(1, lookahead + 1):
                if i + j >= len(df):
                    break
                
                future = df.iloc[i + j]
                
                # Check SL first
                if future['low'] <= sl_price:
                    outcome = 'LOSS'
                    exit_price = sl_price
                    exit_bar = j
                    break
                
                # Check TP
                if future['high'] >= tp_price:
                    outcome = 'WIN'
                    exit_price = tp_price
                    exit_bar = j
                    break
            
            # If no outcome, use last price
            if outcome is None:
                exit_price = df.iloc[min(i + lookahead, len(df) - 1)]['close']
                outcome = 'WIN' if exit_price > entry_price else 'LOSS'
                exit_bar = lookahead
            
            # Calculate PnL
            pnl_dollars = exit_price - entry_price
            pnl_pct = (pnl_dollars / entry_price) * 100
            
            # Log trade
            trade = {
                'trade_id': f'BT{trade_id:04d}',
                'entry_time': row['timestamp'].isoformat(),
                'entry_price': float(round(entry_price, 2)),
                'confidence': float(round(prob * 100, 2)),
                'tp_price': float(round(tp_price, 2)),
                'sl_price': float(round(sl_price, 2)),
                'exit_price': float(round(exit_price, 2)),
                'exit_bar': int(exit_bar) if exit_bar else 0,
                'outcome': outcome,
                'pnl_dollars': float(round(pnl_dollars, 2)),
                'pnl_pct': float(round(pnl_pct, 2)),
                'rsi': float(round(row['rsi_14'], 2)),
                'macd': float(round(row['macd_hist'], 2)),
                'atr_pct': float(round((row['atr_14'] / row['close']) * 100, 3))
            }
            
            trades.append(trade)
            trade_id += 1
    
    # Convert to DataFrame
    trades_df = pd.DataFrame(trades)
    
    # Save to CSV
    output_file = os.path.join(DATA_DIR, f'{model_name}_backtest_trades.csv')
    trades_df.to_csv(output_file, index=False)
    
    # Save to JSON
    output_json = os.path.join(DATA_DIR, f'{model_name}_backtest_trades.json')
    with open(output_json, 'w') as f:
        json.dump(trades, f, indent=2)
    
    # Print summary
    print(f"\n✅ Generated {len(trades)} trades")
    print(f"   📁 CSV: {output_file}")
    print(f"   📁 JSON: {output_json}")
    
    # Statistics
    wins = trades_df[trades_df['outcome'] == 'WIN']
    losses = trades_df[trades_df['outcome'] == 'LOSS']
    
    print(f"\n📊 BACKTEST SUMMARY:")
    print(f"   Total Trades: {len(trades)}")
    print(f"   Wins: {len(wins)} ({len(wins)/len(trades)*100:.1f}%)")
    print(f"   Losses: {len(losses)} ({len(losses)/len(trades)*100:.1f}%)")
    print(f"   Total PnL: ${trades_df['pnl_dollars'].sum():,.2f}")
    print(f"   Avg PnL/Trade: ${trades_df['pnl_dollars'].mean():,.2f}")
    print(f"   Avg Confidence: {trades_df['confidence'].mean():.2f}%")
    
    if len(wins) > 0:
        print(f"   Avg Win: ${wins['pnl_dollars'].mean():,.2f}")
    if len(losses) > 0:
        print(f"   Avg Loss: ${losses['pnl_dollars'].mean():,.2f}")
    
    # Show first 5 trades
    print(f"\n📋 SAMPLE TRADES (First 5):")
    print("-" * 70)
    for _, trade in trades_df.head(5).iterrows():
        result_emoji = "✅" if trade['outcome'] == 'WIN' else "❌"
        print(f"\n   {result_emoji} Trade {trade['trade_id']}")
        print(f"      Entry: ${trade['entry_price']:,.2f} @ {trade['entry_time'][:19]}")
        print(f"      Exit: ${trade['exit_price']:,.2f} ({trade['outcome']})")
        print(f"      PnL: ${trade['pnl_dollars']:,.2f} ({trade['pnl_pct']:+.2f}%)")
        print(f"      Confidence: {trade['confidence']:.1f}%")
    
    return trades_df

if __name__ == '__main__':
    # Generate for Winner Hunter (1H)
    print("\n" + "="*70)
    print("🏆 WINNER HUNTER (1H) - BACKTEST TRADE DATA")
    print("="*70)
    df_1h = generate_backtest_trades('winner_hunter_1h', '1h', 0.95)
    
    print("\n" + "="*70)
    print("✅ BACKTEST TRADE DATA EXPORT COMPLETE")
    print("="*70)
