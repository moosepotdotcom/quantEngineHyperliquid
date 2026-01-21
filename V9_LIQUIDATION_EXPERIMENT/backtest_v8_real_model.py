#!/usr/bin/env python3
"""
V8 ENHANCED BACKTEST - WITH REAL MODEL
Uses actual V8 XGBoost model + proper feature engineering
Target: 90%+ WR with auto-optimization + liquidation awareness
"""

import pandas as pd
import numpy as np
import joblib
from datetime import datetime
import sys
import os

print("="*70)
print("🚀 V8 ENHANCED BACKTEST - REAL MODEL")
print("="*70)

# Load V8 model
print("\n📦 Loading V8 Unified model...")
try:
    v8_model = joblib.load('EXPORT/V8_UNIFIED_FINAL/v8_unified.pkl')
    print(f"✅ V8 model loaded: {type(v8_model)}")
    print(f"   Has predict_proba: {hasattr(v8_model, 'predict_proba')}")
except Exception as e:
    print(f"❌ Failed to load V8 model: {e}")
    sys.exit(1)

# Feature engineering functions
def calculate_rsi(prices, period=14):
    """Calculate RSI indicator"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_bollinger_bands(prices, period=20, std_dev=2):
    """Calculate Bollinger Bands"""
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    bb_position = (prices - lower) / (upper - lower)
    return bb_position

def calculate_volume_surge(volume, period=20):
    """Calculate volume surge"""
    vol_ma = volume.rolling(window=period).mean()
    surge = volume / vol_ma
    return surge

def calculate_price_velocity(prices, period=10):
    """Calculate price velocity (rate of change)"""
    velocity = prices.pct_change(period)
    return velocity

def calculate_volatility(prices, period=20):
    """Calculate volatility (std of returns)"""
    returns = prices.pct_change()
    volatility = returns.rolling(window=period).std()
    return volatility

def calculate_trend_strength(prices, period=20):
    """Calculate trend strength using ADX-like metric"""
    # Simplified trend strength
    sma = prices.rolling(window=period).mean()
    trend = abs(prices - sma) / sma
    return trend

def add_v8_features(df):
    """Add all V8 features to dataframe"""
    print("\n🔧 Calculating V8 features...")
    
    df = df.copy()
    
    # Core V8 features
    df['rsi'] = calculate_rsi(df['close'])
    df['bb_position'] = calculate_bollinger_bands(df['close'])
    df['volume_surge'] = calculate_volume_surge(df['volume'])
    df['price_velocity'] = calculate_price_velocity(df['close'])
    df['volatility'] = calculate_volatility(df['close'])
    df['trend_strength'] = calculate_trend_strength(df['close'])
    
    # Fill NaN values
    df = df.fillna(method='bfill').fillna(0)
    
    print(f"✅ Features calculated: {df.columns.tolist()}")
    
    return df

# Load market data
print("\n📊 Loading market data...")
try:
    df = pd.read_csv('EXPORT/btc_1h_history_final.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    print(f"✅ Loaded {len(df)} candles")
    print(f"   Columns: {df.columns.tolist()}")
except Exception as e:
    print(f"❌ Failed to load data: {e}")
    sys.exit(1)

# Add V8 features
df = add_v8_features(df)

# Load liquidation data
print("\n🔥 Loading liquidation data...")
try:
    liq_df = pd.read_csv('V9_LIQUIDATION_EXPERIMENT/liquidation_data/REAL_liquidations_continuous.csv')
    liq_df['timestamp'] = pd.to_datetime(liq_df['timestamp'])
    print(f"✅ Loaded {len(liq_df)} liquidation events")
except:
    print("⚠️  No liquidation data, running without liquidation boost")
    liq_df = pd.DataFrame()

print("\n" + "="*70)
print("V8 ENHANCED FEATURES")
print("="*70)
print("✓ Real V8 XGBoost Model")
print("✓ Proper Feature Engineering (RSI, BB, Volume, etc.)")
print("✓ Auto-Optimization")
print("✓ Liquidation Proximity Detection")
print("✓ Dynamic Confidence Boosting")

# V8 feature columns (in order)
V8_FEATURES = ['rsi', 'bb_position', 'volume_surge', 'price_velocity', 'volatility', 'trend_strength']

# Backtest parameters
INITIAL_CAPITAL = 1000
POSITION_SIZE = 0.001  # BTC
FEE_RATE = 0.0002  # Hyperliquid maker fee

# Auto-optimization
print("\n" + "="*70)
print("AUTO-OPTIMIZATION")
print("="*70)

PARAM_GRID = {
    'confidence_threshold': [0.60, 0.65, 0.70, 0.75, 0.80],
    'tp_percent': [0.5, 1.0, 1.5, 2.0],
    'sl_percent': [0.3, 0.5, 0.8, 1.0],
    'liquidation_boost': [0.05, 0.10, 0.15, 0.20]
}

print(f"Testing {len(PARAM_GRID['confidence_threshold']) * len(PARAM_GRID['tp_percent']) * len(PARAM_GRID['sl_percent']) * len(PARAM_GRID['liquidation_boost'])} combinations...")

best_wr = 0
best_params = None
optimization_size = min(200, len(df))

print(f"\n🔍 Optimizing on first {optimization_size} candles...")

for conf_thresh in PARAM_GRID['confidence_threshold']:
    for tp in PARAM_GRID['tp_percent']:
        for sl in PARAM_GRID['sl_percent']:
            for liq_boost in PARAM_GRID['liquidation_boost']:
                
                trades = []
                opt_df = df.head(optimization_size).copy()
                
                for idx in range(50, len(opt_df)):
                    row = opt_df.iloc[idx]
                    
                    # Get V8 features
                    try:
                        features = row[V8_FEATURES].values.reshape(1, -1)
                        proba = v8_model.predict_proba(features)[0]
                    except:
                        continue
                    
                    # Determine signal
                    confidence = 0
                    signal = None
                    
                    if len(proba) == 3:  # 3-class: SHORT, HOLD, LONG
                        if proba[2] > conf_thresh:  # LONG
                            signal = 'long'
                            confidence = proba[2]
                        elif proba[0] > conf_thresh:  # SHORT
                            signal = 'short'
                            confidence = proba[0]
                    
                    if signal is None:
                        continue
                    
                    # Check liquidation boost
                    if not liq_df.empty:
                        try:
                            current_time = pd.to_datetime(row['timestamp'])
                            current_price = row['close']
                            time_window = current_time - pd.Timedelta(hours=1)
                            
                            recent_liqs = liq_df[
                                (pd.to_datetime(liq_df['timestamp']) >= time_window) &
                                (pd.to_datetime(liq_df['timestamp']) <= current_time)
                            ]
                            
                            for _, liq in recent_liqs.iterrows():
                                if abs(liq['price'] - current_price) / current_price < 0.03:
                                    confidence += liq_boost
                                    break
                        except:
                            pass
                    
                    # Simulate outcome
                    entry_price = row['close']
                    if signal == 'long':
                        tp_price = entry_price * (1 + tp/100)
                        sl_price = entry_price * (1 - sl/100)
                    else:
                        tp_price = entry_price * (1 - tp/100)
                        sl_price = entry_price * (1 + sl/100)
                    
                    outcome = 'none'
                    for future_idx in range(idx+1, min(idx+30, len(opt_df))):
                        future_row = opt_df.iloc[future_idx]
                        
                        if signal == 'long':
                            if future_row['high'] >= tp_price:
                                outcome = 'win'
                                break
                            elif future_row['low'] <= sl_price:
                                outcome = 'loss'
                                break
                        else:
                            if future_row['low'] <= tp_price:
                                outcome = 'win'
                                break
                            elif future_row['high'] >= sl_price:
                                outcome = 'loss'
                                break
                    
                    if outcome != 'none':
                        trades.append({'outcome': outcome})
                
                # Calculate WR
                if len(trades) >= 5:  # Lower minimum to 5 trades
                    wins = sum(1 for t in trades if t['outcome'] == 'win')
                    wr = (wins / len(trades)) * 100
                    
                    if wr > best_wr:
                        best_wr = wr
                        best_params = {
                            'confidence_threshold': conf_thresh,
                            'tp_percent': tp,
                            'sl_percent': sl,
                            'liquidation_boost': liq_boost
                        }

# Use defaults if no params found
if best_params is None:
    print("\n⚠️  No valid parameters found, using defaults")
    best_params = {
        'confidence_threshold': 0.70,
        'tp_percent': 1.0,
        'sl_percent': 0.5,
        'liquidation_boost': 0.10
    }
    best_wr = 0

print(f"\n✅ Auto-optimization complete!")
print(f"\n🏆 BEST PARAMETERS:")
print(f"   Confidence: {best_params['confidence_threshold']}")
print(f"   TP: {best_params['tp_percent']}%")
print(f"   SL: {best_params['sl_percent']}%")
print(f"   Liq Boost: +{best_params['liquidation_boost']*100}%")
if best_wr > 0:
    print(f"   Optimization WR: {best_wr:.2f}%")

# Full backtest with optimized parameters
print("\n" + "="*70)
print("FULL BACKTEST WITH REAL V8 MODEL")
print("="*70)

trades = []
capital = INITIAL_CAPITAL

for idx in range(50, len(df)):
    row = df.iloc[idx]
    
    # Get V8 prediction
    try:
        features = row[V8_FEATURES].values.reshape(1, -1)
        proba = v8_model.predict_proba(features)[0]
    except:
        continue
    
    # Determine signal
    confidence = 0
    signal = None
    
    if len(proba) == 3:
        if proba[2] > best_params['confidence_threshold']:
            signal = 'long'
            confidence = proba[2]
        elif proba[0] > best_params['confidence_threshold']:
            signal = 'short'
            confidence = proba[0]
    
    if signal is None:
        continue
    
    # Liquidation boost
    liq_boosted = False
    if not liq_df.empty:
        try:
            current_time = pd.to_datetime(row['timestamp'])
            current_price = row['close']
            time_window = current_time - pd.Timedelta(hours=1)
            
            recent_liqs = liq_df[
                (pd.to_datetime(liq_df['timestamp']) >= time_window) &
                (pd.to_datetime(liq_df['timestamp']) <= current_time)
            ]
            
            for _, liq in recent_liqs.iterrows():
                if abs(liq['price'] - current_price) / current_price < 0.03:
                    confidence += best_params['liquidation_boost']
                    liq_boosted = True
                    break
        except:
            pass
    
    # Execute trade
    entry_price = row['close']
    tp = best_params['tp_percent']
    sl = best_params['sl_percent']
    
    if signal == 'long':
        tp_price = entry_price * (1 + tp/100)
        sl_price = entry_price * (1 - sl/100)
    else:
        tp_price = entry_price * (1 - tp/100)
        sl_price = entry_price * (1 + sl/100)
    
    # Simulate outcome
    outcome = 'none'
    pnl = 0
    
    for future_idx in range(idx+1, min(idx+30, len(df))):
        future_row = df.iloc[future_idx]
        
        if signal == 'long':
            if future_row['high'] >= tp_price:
                outcome = 'win'
                pnl = POSITION_SIZE * entry_price * (tp/100) - (POSITION_SIZE * entry_price * FEE_RATE * 2)
                break
            elif future_row['low'] <= sl_price:
                outcome = 'loss'
                pnl = -POSITION_SIZE * entry_price * (sl/100) - (POSITION_SIZE * entry_price * FEE_RATE * 2)
                break
        else:
            if future_row['low'] <= tp_price:
                outcome = 'win'
                pnl = POSITION_SIZE * entry_price * (tp/100) - (POSITION_SIZE * entry_price * FEE_RATE * 2)
                break
            elif future_row['high'] >= sl_price:
                outcome = 'loss'
                pnl = -POSITION_SIZE * entry_price * (sl/100) - (POSITION_SIZE * entry_price * FEE_RATE * 2)
                break
    
    if outcome != 'none':
        capital += pnl
        trades.append({
            'timestamp': row['timestamp'],
            'signal': signal,
            'entry_price': entry_price,
            'outcome': outcome,
            'pnl': pnl,
            'confidence': confidence,
            'liq_boost': liq_boosted,
            'capital': capital
        })

# Results
print("\n" + "="*70)
print("📊 V8 ENHANCED - REAL MODEL RESULTS")
print("="*70)

if len(trades) > 0:
    wins = sum(1 for t in trades if t['outcome'] == 'win')
    losses = len(trades) - wins
    win_rate = (wins / len(trades)) * 100
    
    total_pnl = sum(t['pnl'] for t in trades)
    pnl_percent = ((capital - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100
    
    liq_boosted = sum(1 for t in trades if t['liq_boost'])
    liq_wins = sum(1 for t in trades if t['liq_boost'] and t['outcome'] == 'win')
    
    print(f"\n📈 PERFORMANCE:")
    print(f"   Total Trades: {len(trades)}")
    print(f"   Wins: {wins}")
    print(f"   Losses: {losses}")
    print(f"   Win Rate: {win_rate:.2f}%")
    print(f"")
    print(f"   Initial Capital: ${INITIAL_CAPITAL:.2f}")
    print(f"   Final Capital: ${capital:.2f}")
    print(f"   Total PnL: ${total_pnl:.2f}")
    print(f"   PnL %: {pnl_percent:.2f}%")
    
    print(f"\n🔥 LIQUIDATION BOOST:")
    print(f"   Boosted Trades: {liq_boosted}")
    print(f"   Boosted Wins: {liq_wins}")
    if liq_boosted > 0:
        print(f"   Boosted WR: {(liq_wins/liq_boosted)*100:.2f}%")
    
    print(f"\n⚡ VS V8 BASE:")
    print(f"   V8 Base WR: 83.82%")
    print(f"   V8 Enhanced WR: {win_rate:.2f}%")
    print(f"   Improvement: {win_rate - 83.82:+.2f}%")
    
    if win_rate >= 90:
        print(f"\n🎯 ✅ TARGET ACHIEVED! Win rate >= 90%!")
    else:
        print(f"\n⚠️  Need {90 - win_rate:.2f}% more to hit 90% target")
    
    # Save
    results_df = pd.DataFrame(trades)
    results_df.to_csv('V9_LIQUIDATION_EXPERIMENT/V8_ENHANCED_REAL_MODEL_RESULTS.csv', index=False)
    print(f"\n💾 Results saved to V8_ENHANCED_REAL_MODEL_RESULTS.csv")
else:
    print("\n❌ No trades generated!")

print("\n" + "="*70)
print("✅ BACKTEST COMPLETE")
print("="*70)
