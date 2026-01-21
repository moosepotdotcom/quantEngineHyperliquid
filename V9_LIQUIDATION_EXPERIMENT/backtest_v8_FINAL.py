#!/usr/bin/env python3
"""
V8 ENHANCED - CORRECT INTERPRETATION
The model predicts FUTURE VOLATILITY REGIME, not just trades!
We need to verify predictions and only trade when model is confident
"""

import pandas as pd
import numpy as np
import joblib
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'EXPORT'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'EXPORT', 'JACKPOT_V6_V7_CONFIRMED'))

from v5_feature_engineer import generate_v5_features

print("="*70)
print("🎯 V8 ENHANCED - CORRECT INTERPRETATION")
print("="*70)

# Load model
model = joblib.load('EXPORT/V8_UNIFIED_FINAL/v8_unified.pkl')
with open('model_engines/v8_unified/weights/feature_names.txt', 'r') as f:
    feature_cols = [line.strip() for line in f.readlines()]

print(f"✅ Model loaded: {len(feature_cols)} features, {model.n_classes_} classes")

# Load data
df = pd.read_csv('training/data/BTC_5m_2025_enriched.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.tail(1000).copy().reset_index(drop=True)

print(f"✅ Loaded {len(df)} candles")
print(f"   Period: {df['timestamp'].min()} to {df['timestamp'].max()}")

# Keep required columns
required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'taker_buy_base']
df = df[required_cols]

# Generate features
print("\n🔧 Generating V5 features...")
df_enriched = generate_v5_features(df)

# Fill missing
for col in feature_cols:
    if col not in df_enriched.columns:
        df_enriched[col] = 0

# Predict
print("\n🔮 Generating predictions...")
predictions = model.predict(df_enriched[feature_cols])
probas = model.predict_proba(df_enriched[feature_cols])

df_enriched['v8_pred'] = predictions
df_enriched['prob_grid'] = probas[:, 0]
df_enriched['prob_long'] = probas[:, 1]
df_enriched['prob_short'] = probas[:, 2]
df_enriched['prob_neutral'] = probas[:, 3]

# Calculate ACTUAL future volatility for each prediction
print("\n📊 Validating model predictions...")
correct_predictions = 0
total_predictions = 0

for i in range(200, len(df_enriched) - 24):
    row = df_enriched.iloc[i]
    future_24 = df_enriched.iloc[i+1:i+25]
    
    # Calculate actual future volatility
    actual_atr = (future_24['high'] - future_24['low']).mean()
    actual_atr_pct = (actual_atr / row['close']) * 100
    
    # Model prediction
    pred = row['v8_pred']
    
    # Check if prediction was correct
    if pred == 0:  # Predicted Grid (low vol)
        if actual_atr_pct <= 0.3:
            correct_predictions += 1
    elif pred in [1, 2]:  # Predicted Long/Short (high vol)
        if actual_atr_pct > 0.3:
            correct_predictions += 1
    elif pred == 3:  # Predicted Neutral (high vol but uncertain)
        if actual_atr_pct > 0.3:
            correct_predictions += 1
    
    total_predictions += 1

prediction_accuracy = (correct_predictions / total_predictions) * 100
print(f"✅ Model Volatility Prediction Accuracy: {prediction_accuracy:.2f}%")

# Now backtest with CONFIDENCE THRESHOLD
print("\n" + "="*70)
print("💰 BACKTESTING WITH CONFIDENCE THRESHOLD")
print("="*70)

INITIAL_CAPITAL = 1000
POSITION_SIZE_PCT = 0.01
FEE_RATE = 0.0002

# Only trade when model is VERY confident
CONFIDENCE_THRESHOLDS = {
    0: 0.90,  # Grid: only if 90%+ confident it's low vol
    1: 0.85,  # Long: only if 85%+ confident
    2: 0.85,  # Short: only if 85%+ confident
}

PARAMS = {
    'Grid': {'tp': 0.001, 'sl': 0.0005},
    'Long': {'tp': 0.005, 'sl': 0.0015},
    'Short': {'tp': 0.005, 'sl': 0.0015}
}

capital = INITIAL_CAPITAL
trades = []
in_trade = None

for i in range(200, len(df_enriched) - 1):
    row = df_enriched.iloc[i]
    
    # Manage existing trade
    if in_trade:
        params = PARAMS[trade_type]
        
        if trade_type == 'Grid':
            if row['high'] >= entry_price * (1 + params['tp']):
                pnl = POSITION_SIZE_PCT * params['tp'] - (POSITION_SIZE_PCT * FEE_RATE * 2)
                capital *= (1 + pnl)
                trades.append({'type': trade_type, 'outcome': 'win', 'pnl': pnl, 'capital': capital, 'confidence': entry_confidence})
                in_trade = None
            elif row['low'] <= entry_price * (1 - params['sl']):
                pnl = -POSITION_SIZE_PCT * params['sl'] - (POSITION_SIZE_PCT * FEE_RATE * 2)
                capital *= (1 + pnl)
                trades.append({'type': trade_type, 'outcome': 'loss', 'pnl': pnl, 'capital': capital, 'confidence': entry_confidence})
                in_trade = None
        elif trade_type == 'Long':
            if row['high'] >= entry_price * (1 + params['tp']):
                pnl = POSITION_SIZE_PCT * params['tp'] - (POSITION_SIZE_PCT * FEE_RATE * 2)
                capital *= (1 + pnl)
                trades.append({'type': trade_type, 'outcome': 'win', 'pnl': pnl, 'capital': capital, 'confidence': entry_confidence})
                in_trade = None
            elif row['low'] <= entry_price * (1 - params['sl']):
                pnl = -POSITION_SIZE_PCT * params['sl'] - (POSITION_SIZE_PCT * FEE_RATE * 2)
                capital *= (1 + pnl)
                trades.append({'type': trade_type, 'outcome': 'loss', 'pnl': pnl, 'capital': capital, 'confidence': entry_confidence})
                in_trade = None
        elif trade_type == 'Short':
            if row['low'] <= entry_price * (1 - params['tp']):
                pnl = POSITION_SIZE_PCT * params['tp'] - (POSITION_SIZE_PCT * FEE_RATE * 2)
                capital *= (1 + pnl)
                trades.append({'type': trade_type, 'outcome': 'win', 'pnl': pnl, 'capital': capital, 'confidence': entry_confidence})
                in_trade = None
            elif row['high'] >= entry_price * (1 + params['sl']):
                pnl = -POSITION_SIZE_PCT * params['sl'] - (POSITION_SIZE_PCT * FEE_RATE * 2)
                capital *= (1 + pnl)
                trades.append({'type': trade_type, 'outcome': 'loss', 'pnl': pnl, 'capital': capital, 'confidence': entry_confidence})
                in_trade = None
        continue
    
    # Entry logic with CONFIDENCE THRESHOLD
    pred = row['v8_pred']
    
    if pred == 0 and row['prob_grid'] >= CONFIDENCE_THRESHOLDS[0]:
        in_trade = True
        entry_price = row['close']
        trade_type = 'Grid'
        entry_confidence = row['prob_grid']
    elif pred == 1 and row['prob_long'] >= CONFIDENCE_THRESHOLDS[1]:
        in_trade = True
        entry_price = row['close']
        trade_type = 'Long'
        entry_confidence = row['prob_long']
    elif pred == 2 and row['prob_short'] >= CONFIDENCE_THRESHOLDS[2]:
        in_trade = True
        entry_price = row['close']
        trade_type = 'Short'
        entry_confidence = row['prob_short']

# Results
print("\n" + "="*70)
print("📊 RESULTS WITH CONFIDENCE FILTERING")
print("="*70)

if len(trades) > 0:
    wins = sum(1 for t in trades if t['outcome'] == 'win')
    losses = len(trades) - wins
    win_rate = (wins / len(trades)) * 100
    
    total_pnl = capital - INITIAL_CAPITAL
    pnl_percent = ((capital - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100
    
    grid_trades = [t for t in trades if t['type'] == 'Grid']
    long_trades = [t for t in trades if t['type'] == 'Long']
    short_trades = [t for t in trades if t['type'] == 'Short']
    
    print(f"\n📈 OVERALL PERFORMANCE:")
    print(f"   Total Trades: {len(trades)}")
    print(f"   Wins: {wins}")
    print(f"   Losses: {losses}")
    print(f"   Win Rate: {win_rate:.2f}%")
    print(f"")
    print(f"   Initial Capital: ${INITIAL_CAPITAL:.2f}")
    print(f"   Final Capital: ${capital:.2f}")
    print(f"   Total PnL: ${total_pnl:.2f}")
    print(f"   PnL %: {pnl_percent:.2f}%")
    
    print(f"\n📊 BY TRADE TYPE:")
    if grid_trades:
        grid_wins = sum(1 for t in grid_trades if t['outcome'] == 'win')
        print(f"   Grid:  {len(grid_trades)} trades, {grid_wins} wins, {(grid_wins/len(grid_trades))*100:.1f}% WR")
    if long_trades:
        long_wins = sum(1 for t in long_trades if t['outcome'] == 'win')
        print(f"   Long:  {len(long_trades)} trades, {long_wins} wins, {(long_wins/len(long_trades))*100:.1f}% WR")
    if short_trades:
        short_wins = sum(1 for t in short_trades if t['outcome'] == 'win')
        print(f"   Short: {len(short_trades)} trades, {short_wins} wins, {(short_wins/len(short_trades))*100:.1f}% WR")
    
    print(f"\n⚡ VS TARGET:")
    print(f"   Target WR: 90%+")
    print(f"   Achieved WR: {win_rate:.2f}%")
    
    if win_rate >= 90:
        print(f"\n🎯 ✅ TARGET ACHIEVED!")
    else:
        print(f"\n⚠️  Difference: {win_rate - 90:+.2f}%")
    
    # Save
    results_df = pd.DataFrame(trades)
    results_df.to_csv('V9_LIQUIDATION_EXPERIMENT/V8_ENHANCED_CONFIDENCE_FILTERED.csv', index=False)
    print(f"\n💾 Results saved")
else:
    print("\n❌ No high-confidence trades found!")
    print("   Try lowering confidence thresholds")

print("\n" + "="*70)
print("✅ ANALYSIS COMPLETE")
print("="*70)
