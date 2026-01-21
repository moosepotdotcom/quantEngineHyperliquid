#!/usr/bin/env python3
"""
SCALPER V1 BACKTEST - Jan 2-11, 2026
Tests new scalping models with 0.5% TP / 0.3% SL
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("\n" + "🚀"*35)
print("SCALPER V1 BACKTEST - JAN 2-11, 2026")
print("Testing: 0.5% TP / 0.3% SL with new models")
print("🚀"*35)

# Load models
print("\n📦 Loading Scalper V1 models...")

import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
import pickle

model_dir = '/Users/alifiyaa/Downloads/quantEngineHyperliquid/SCALPER_EXPORT_V1/scalping'

xgb_model = xgb.XGBClassifier()
xgb_model.load_model(f'{model_dir}/xgb_scalper.json')
print("   ✅ XGBoost loaded")

lgb_model = lgb.Booster(model_file=f'{model_dir}/lgb_scalper.txt')
print("   ✅ LightGBM loaded")

cat_model = CatBoostClassifier()
cat_model.load_model(f'{model_dir}/cat_scalper.cbm')
print("   ✅ CatBoost loaded")

with open(f'{model_dir}/feature_names.pkl', 'rb') as f:
    feature_names = pickle.load(f)
print(f"   ✅ Features loaded ({len(feature_names)})")

# Load historical data
print("\n📥 Loading historical data...")
df = pd.read_csv('/Users/alifiyaa/Downloads/quantEngineHyperliquid/EXPORT/btc_5m_history_final.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df.set_index('timestamp', inplace=True)

# Filter to Jan 2-11
start_date = "2026-01-02"
end_date = "2026-01-11 23:59:59"
mask = (df.index >= start_date) & (df.index <= end_date)
df_test = df[mask].copy()

print(f"✅ Loaded {len(df_test)} candles (Jan 2-11)")

# Add indicators
print("\n🔧 Adding indicators...")

def add_simple_indicators(df):
    """Add same indicators as training"""
    df = df.copy()
    
    df['sma_10'] = df['close'].rolling(10).mean()
    df['sma_20'] = df['close'].rolling(20).mean()
    df['sma_50'] = df['close'].rolling(50).mean()
    df['ema_10'] = df['close'].ewm(span=10).mean()
    df['ema_20'] = df['close'].ewm(span=20).mean()
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi_14'] = 100 - (100 / (1 + rs))
    
    df['atr_14'] = (df['high'] - df['low']).rolling(14).mean()
    df['volatility'] = df['close'].pct_change().rolling(20).std()
    
    df['price_change'] = df['close'].pct_change()
    df['high_low_ratio'] = df['high'] / df['low']
    df['close_open_ratio'] = df['close'] / df['open']
    
    df['volume_sma'] = df['volume'].rolling(20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_sma']
    
    df['momentum_5'] = df['close'] / df['close'].shift(5) - 1
    df['momentum_10'] = df['close'] / df['close'].shift(10) - 1
    
    return df

df_features = add_simple_indicators(df_test)
df_clean = df_features.dropna()

print(f"✅ Indicators added. Clean samples: {len(df_clean)}")

# Prepare features
X = df_clean[feature_names].values
X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

# Get predictions
print("\n🤖 Generating predictions...")

proba_xgb = xgb_model.predict_proba(X)
proba_lgb = lgb_model.predict(X)
proba_cat = cat_model.predict_proba(X)

# Ensemble
proba_ensemble = (proba_xgb + proba_lgb + proba_cat) / 3

# Get signals
predictions = np.argmax(proba_ensemble, axis=1)
confidences = np.max(proba_ensemble, axis=1)

print(f"✅ Predictions generated")

# Find signals above threshold
threshold = 0.45
signal_mask = (confidences >= threshold) & (predictions != 0)
signal_indices = np.where(signal_mask)[0]

print(f"\n📊 Signals found: {len(signal_indices)} (threshold: {threshold*100:.0f}%)")

# Simulate trades
print("\n🔄 Simulating trades with position management...")

tp_pct = 0.005  # 0.5%
sl_pct = 0.003  # 0.3%

trades = []
current_position = None

for i, (timestamp, row) in enumerate(df_clean.iterrows()):
    # Check if we have an open position
    if current_position is not None:
        entry_price = current_position['price']
        tp_price = current_position['tp']
        sl_price = current_position['sl']
        direction = current_position['dir']
        
        h, l = row['high'], row['low']
        
        if direction == 'LONG':
            if h >= tp_price:
                outcome = 'WIN'
                hold_hours = (timestamp - current_position['time']).total_seconds() / 3600
                current_position['outcome'] = outcome
                current_position['exit_time'] = timestamp
                current_position['hold_hours'] = hold_hours
                trades.append(current_position.copy())
                
                print(f"   ✅ WIN: {current_position['time'].strftime('%m-%d %H:%M')} → "
                      f"{timestamp.strftime('%m-%d %H:%M')} ({hold_hours:.1f}h) | "
                      f"${entry_price:,.0f} → ${tp_price:,.0f}")
                
                current_position = None
                continue
                
            elif l <= sl_price:
                outcome = 'LOSS'
                hold_hours = (timestamp - current_position['time']).total_seconds() / 3600
                current_position['outcome'] = outcome
                current_position['exit_time'] = timestamp
                current_position['hold_hours'] = hold_hours
                trades.append(current_position.copy())
                
                print(f"   ❌ LOSS: {current_position['time'].strftime('%m-%d %H:%M')} → "
                      f"{timestamp.strftime('%m-%d %H:%M')} ({hold_hours:.1f}h) | "
                      f"${entry_price:,.0f} → ${sl_price:,.0f}")
                
                current_position = None
                continue
        
        else:  # SHORT
            if l <= tp_price:
                outcome = 'WIN'
                hold_hours = (timestamp - current_position['time']).total_seconds() / 3600
                current_position['outcome'] = outcome
                current_position['exit_time'] = timestamp
                current_position['hold_hours'] = hold_hours
                trades.append(current_position.copy())
                
                print(f"   ✅ WIN: {current_position['time'].strftime('%m-%d %H:%M')} → "
                      f"{timestamp.strftime('%m-%d %H:%M')} ({hold_hours:.1f}h)")
                
                current_position = None
                continue
                
            elif h >= sl_price:
                outcome = 'LOSS'
                hold_hours = (timestamp - current_position['time']).total_seconds() / 3600
                current_position['outcome'] = outcome
                current_position['exit_time'] = timestamp
                current_position['hold_hours'] = hold_hours
                trades.append(current_position.copy())
                
                print(f"   ❌ LOSS: {current_position['time'].strftime('%m-%d %H:%M')} → "
                      f"{timestamp.strftime('%m-%d %H:%M')} ({hold_hours:.1f}h)")
                
                current_position = None
                continue
        
        continue
    
    # No position - check for signals
    if i in signal_indices:
        entry_price = row['close']
        direction = 'LONG' if predictions[i] == 1 else 'SHORT'
        confidence = confidences[i]
        
        if direction == 'LONG':
            tp_price = entry_price * (1 + tp_pct)
            sl_price = entry_price * (1 - sl_pct)
        else:
            tp_price = entry_price * (1 - tp_pct)
            sl_price = entry_price * (1 + sl_pct)
        
        current_position = {
            'time': timestamp,
            'dir': direction,
            'conf': confidence,
            'price': entry_price,
            'tp': tp_price,
            'sl': sl_price,
            'outcome': 'OPEN'
        }
        
        print(f"\n   📍 POSITION OPENED: {timestamp.strftime('%m-%d %H:%M')} | "
              f"{direction} @ ${entry_price:,.0f} | Conf: {confidence:.1%}")

# Calculate results
print("\n" + "="*70)
print("📊 BACKTEST RESULTS")
print("="*70)

if len(trades) > 0:
    wins = len([t for t in trades if t['outcome'] == 'WIN'])
    losses = len([t for t in trades if t['outcome'] == 'LOSS'])
    total = len(trades)
    win_rate = wins / total * 100
    avg_hold = sum([t['hold_hours'] for t in trades]) / total
    
    # Calculate P&L
    capital = 53
    leverage = 27
    buying_power = capital * leverage
    
    pnl_per_win = buying_power * tp_pct
    pnl_per_loss = buying_power * sl_pct
    total_pnl = (wins * pnl_per_win) - (losses * pnl_per_loss)
    final_balance = capital + total_pnl
    roi = (total_pnl / capital) * 100
    
    print(f"\nTotal Trades: {total}")
    print(f"Wins: {wins} | Losses: {losses}")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"Avg Hold Time: {avg_hold:.1f} hours")
    print(f"\nP&L Analysis ($53 capital, 27x leverage):")
    print(f"  Wins: {wins} × ${pnl_per_win:.2f} = +${wins * pnl_per_win:.2f}")
    print(f"  Losses: {losses} × ${pnl_per_loss:.2f} = -${losses * pnl_per_loss:.2f}")
    print(f"  Total P&L: ${total_pnl:+.2f}")
    print(f"  Final Balance: ${final_balance:.2f}")
    print(f"  ROI: {roi:+.1f}%")
    
    print("\n" + "="*70)
    print("🎯 COMPARISON WITH CURRENT MODEL")
    print("="*70)
    print(f"{'Metric':<20} {'Current (Swing)':<20} {'Scalper V1':<20}")
    print("-"*70)
    print(f"{'TP/SL':<20} {'1.5% / 0.8%':<20} {'0.5% / 0.3%':<20}")
    print(f"{'Trades':<20} {'7':<20} {total:<20}")
    print(f"{'Win Rate':<20} {'71.4%':<20} {f'{win_rate:.1f}%':<20}")
    print(f"{'Avg Hold':<20} {'8-12h':<20} {f'{avg_hold:.1f}h':<20}")
    print(f"{'ROI':<20} {'+159%':<20} {f'{roi:+.1f}%':<20}")
    print("="*70)
    
else:
    print("❌ No trades completed")

print("\n✅ BACKTEST COMPLETE!")
