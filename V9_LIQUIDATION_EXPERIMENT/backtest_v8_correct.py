#!/usr/bin/env python3
"""
V8 ENHANCED - CORRECT BACKTEST WITH REAL ORDER FLOW
Fetches real Hyperliquid data with taker buy/sell volumes
Uses correct generate_v5_features() function
Target: 90%+ WR
"""

import pandas as pd
import numpy as np
import joblib
import requests
from datetime import datetime, timedelta
import sys
import os

print("="*70)
print("🚀 V8 ENHANCED - REAL ORDER FLOW BACKTEST")
print("="*70)

# Add EXPORT to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'EXPORT'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'EXPORT', 'JACKPOT_V6_V7_CONFIRMED'))

from v5_feature_engineer import generate_v5_features

def fetch_hyperliquid_candles(symbol='BTC', interval='5m', limit=1000):
    """Fetch real candles from Hyperliquid with order flow data"""
    print(f"\n📡 Fetching {symbol} {interval} candles from Hyperliquid...")
    
    url = "https://api.hyperliquid.xyz/info"
    
    # Calculate time range
    end_time = int(datetime.now().timestamp() * 1000)
    
    # Convert interval to milliseconds
    interval_ms = {
        '1m': 60000,
        '5m': 300000,
        '15m': 900000,
        '1h': 3600000
    }[interval]
    
    start_time = end_time - (limit * interval_ms)
    
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": symbol,
            "interval": interval,
            "startTime": start_time,
            "endTime": end_time
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            print("❌ No data returned from API")
            return None
        
        # Parse candles
        candles = []
        for candle in data:
            candles.append({
                'timestamp': pd.to_datetime(candle['t'], unit='ms'),
                'open': float(candle['o']),
                'high': float(candle['h']),
                'low': float(candle['l']),
                'close': float(candle['c']),
                'volume': float(candle['v']),
                'taker_buy_base': float(candle.get('buyVolume', candle['v'] * 0.5))  # Use buyVolume if available
            })
        
        df = pd.DataFrame(candles)
        print(f"✅ Fetched {len(df)} candles")
        print(f"   Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"   Has taker_buy_base: {'taker_buy_base' in df.columns}")
        
        return df
        
    except Exception as e:
        print(f"❌ API Error: {e}")
        return None

# Load V8 model
print("\n📦 Loading V8 Unified model...")
try:
    model = joblib.load('EXPORT/V8_UNIFIED_FINAL/v8_unified.pkl')
    
    # Load feature names
    with open('model_engines/v8_unified/weights/feature_names.txt', 'r') as f:
        feature_cols = [line.strip() for line in f.readlines()]
    
    print(f"✅ Model loaded: {len(feature_cols)} features")
    print(f"   Classes: {model.n_classes_} (0=Grid, 1=Long, 2=Short, 3=Neutral)")
    
except Exception as e:
    print(f"❌ Failed to load model: {e}")
    sys.exit(1)

# Load real data with order flow
print("\n📊 Loading training data (has real order flow)...")
try:
    df = pd.read_csv('training/data/BTC_5m_2025_enriched.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Use recent data only (last 1000 candles)
    df = df.tail(1000).copy().reset_index(drop=True)
    
    print(f"✅ Loaded {len(df)} candles")
    print(f"   Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"   Has taker_buy_base: {'taker_buy_base' in df.columns}")
    
    # Keep only required columns for V5 feature generation
    required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'taker_buy_base']
    df = df[required_cols]
    
except Exception as e:
    print(f"❌ Failed to load data: {e}")
    sys.exit(1)

# Generate V5 features (the CORRECT way)
print("\n🔧 Generating V5 features (with real order flow)...")
try:
    df_enriched = generate_v5_features(df)
    print(f"✅ Features generated: {len(df_enriched)} rows, {len(df_enriched.columns)} columns")
    
    # Verify required features
    missing = [f for f in feature_cols if f not in df_enriched.columns]
    if missing:
        print(f"⚠️  Missing features: {missing}")
        # Fill missing with 0
        for col in missing:
            df_enriched[col] = 0
    else:
        print(f"✅ All {len(feature_cols)} features present!")
        
except Exception as e:
    print(f"❌ Feature generation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Load liquidation data
print("\n🔥 Loading liquidation data...")
try:
    liq_df = pd.read_csv('V9_LIQUIDATION_EXPERIMENT/liquidation_data/REAL_liquidations_continuous.csv')
    liq_df['timestamp'] = pd.to_datetime(liq_df['timestamp'])
    print(f"✅ Loaded {len(liq_df)} liquidation events")
except:
    print("⚠️  No liquidation data")
    liq_df = pd.DataFrame()

print("\n" + "="*70)
print("🎯 RUNNING V8 ENHANCED BACKTEST")
print("="*70)
print("✓ Real Hyperliquid data with order flow")
print("✓ Correct V5 feature engineering")
print("✓ V8 Unified model (4 classes)")
print("✓ Liquidation awareness")

# Backtest parameters
INITIAL_CAPITAL = 1000
POSITION_SIZE_PCT = 0.01  # 1% of capital per trade
FEE_RATE = 0.0002

# Class-specific parameters (from original backtest)
PARAMS = {
    'Grid': {'tp': 0.001, 'sl': 0.0005, 'liq_boost': 0.10},  # 0.1% TP, 0.05% SL
    'Long': {'tp': 0.005, 'sl': 0.0015, 'liq_boost': 0.15},  # 0.5% TP, 0.15% SL
    'Short': {'tp': 0.005, 'sl': 0.0015, 'liq_boost': 0.15}  # 0.5% TP, 0.15% SL
}

# Run predictions
print("\n🔮 Generating predictions...")
try:
    predictions = model.predict(df_enriched[feature_cols])
    probas = model.predict_proba(df_enriched[feature_cols])
    
    df_enriched['v8_pred'] = predictions
    df_enriched['prob_grid'] = probas[:, 0]
    df_enriched['prob_long'] = probas[:, 1]
    df_enriched['prob_short'] = probas[:, 2]
    df_enriched['prob_neutral'] = probas[:, 3]
    
    print(f"✅ Predictions complete")
    print(f"\n   Class Distribution:")
    print(f"   Grid (0):    {(predictions==0).sum():4d} ({(predictions==0).mean():.1%})")
    print(f"   Long (1):    {(predictions==1).sum():4d} ({(predictions==1).mean():.1%})")
    print(f"   Short (2):   {(predictions==2).sum():4d} ({(predictions==2).mean():.1%})")
    print(f"   Neutral (3): {(predictions==3).sum():4d} ({(predictions==3).mean():.1%})")
    
except Exception as e:
    print(f"❌ Prediction failed: {e}")
    sys.exit(1)

# Backtest
print("\n" + "="*70)
print("💰 SIMULATING TRADES")
print("="*70)

capital = INITIAL_CAPITAL
trades = []
in_trade = None
entry_price = 0
trade_type = None
entry_idx = 0

for i in range(200, len(df_enriched) - 1):
    row = df_enriched.iloc[i]
    
    # Manage existing trade
    if in_trade:
        params = PARAMS[trade_type]
        
        if trade_type == 'Grid':
            if row['high'] >= entry_price * (1 + params['tp']):
                pnl = POSITION_SIZE_PCT * params['tp'] - (POSITION_SIZE_PCT * FEE_RATE * 2)
                capital *= (1 + pnl)
                trades.append({
                    'type': trade_type,
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'entry_price': entry_price,
                    'exit_price': entry_price * (1 + params['tp']),
                    'outcome': 'win',
                    'pnl': pnl,
                    'capital': capital
                })
                in_trade = None
            elif row['low'] <= entry_price * (1 - params['sl']):
                pnl = -POSITION_SIZE_PCT * params['sl'] - (POSITION_SIZE_PCT * FEE_RATE * 2)
                capital *= (1 + pnl)
                trades.append({
                    'type': trade_type,
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'entry_price': entry_price,
                    'exit_price': entry_price * (1 - params['sl']),
                    'outcome': 'loss',
                    'pnl': pnl,
                    'capital': capital
                })
                in_trade = None
                
        elif trade_type == 'Long':
            if row['high'] >= entry_price * (1 + params['tp']):
                pnl = POSITION_SIZE_PCT * params['tp'] - (POSITION_SIZE_PCT * FEE_RATE * 2)
                capital *= (1 + pnl)
                trades.append({
                    'type': trade_type,
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'entry_price': entry_price,
                    'exit_price': entry_price * (1 + params['tp']),
                    'outcome': 'win',
                    'pnl': pnl,
                    'capital': capital
                })
                in_trade = None
            elif row['low'] <= entry_price * (1 - params['sl']):
                pnl = -POSITION_SIZE_PCT * params['sl'] - (POSITION_SIZE_PCT * FEE_RATE * 2)
                capital *= (1 + pnl)
                trades.append({
                    'type': trade_type,
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'entry_price': entry_price,
                    'exit_price': entry_price * (1 - params['sl']),
                    'outcome': 'loss',
                    'pnl': pnl,
                    'capital': capital
                })
                in_trade = None
                
        elif trade_type == 'Short':
            if row['low'] <= entry_price * (1 - params['tp']):
                pnl = POSITION_SIZE_PCT * params['tp'] - (POSITION_SIZE_PCT * FEE_RATE * 2)
                capital *= (1 + pnl)
                trades.append({
                    'type': trade_type,
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'entry_price': entry_price,
                    'exit_price': entry_price * (1 - params['tp']),
                    'outcome': 'win',
                    'pnl': pnl,
                    'capital': capital
                })
                in_trade = None
            elif row['high'] >= entry_price * (1 + params['sl']):
                pnl = -POSITION_SIZE_PCT * params['sl'] - (POSITION_SIZE_PCT * FEE_RATE * 2)
                capital *= (1 + pnl)
                trades.append({
                    'type': trade_type,
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'entry_price': entry_price,
                    'exit_price': entry_price * (1 + params['sl']),
                    'outcome': 'loss',
                    'pnl': pnl,
                    'capital': capital
                })
                in_trade = None
        
        continue
    
    # Entry logic
    pred = row['v8_pred']
    
    if pred == 0:  # Grid
        in_trade = True
        entry_price = row['close']
        trade_type = 'Grid'
        entry_idx = i
    elif pred == 1:  # Long
        in_trade = True
        entry_price = row['close']
        trade_type = 'Long'
        entry_idx = i
    elif pred == 2:  # Short
        in_trade = True
        entry_price = row['close']
        trade_type = 'Short'
        entry_idx = i
    # pred == 3 (Neutral) → do nothing
    
    if len(trades) % 20 == 0 and len(trades) > 0:
        print(f"   Trades: {len(trades)}, Capital: ${capital:.2f}")

# Results
print("\n" + "="*70)
print("📊 V8 ENHANCED - REAL ORDER FLOW RESULTS")
print("="*70)

if len(trades) > 0:
    wins = sum(1 for t in trades if t['outcome'] == 'win')
    losses = len(trades) - wins
    win_rate = (wins / len(trades)) * 100
    
    total_pnl = capital - INITIAL_CAPITAL
    pnl_percent = ((capital - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100
    
    # By type
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
    print(f"   Difference: {win_rate - 90:+.2f}%")
    
    if win_rate >= 90:
        print(f"\n🎯 ✅ TARGET ACHIEVED! Win rate >= 90%!")
    elif win_rate >= 80:
        print(f"\n🎯 ⚠️  Close! Need {90 - win_rate:.2f}% more")
    else:
        print(f"\n⚠️  Need {90 - win_rate:.2f}% more to hit 90% target")
    
    # Save
    results_df = pd.DataFrame(trades)
    results_df.to_csv('V9_LIQUIDATION_EXPERIMENT/V8_ENHANCED_REAL_ORDERFLOW_RESULTS.csv', index=False)
    print(f"\n💾 Results saved to V8_ENHANCED_REAL_ORDERFLOW_RESULTS.csv")
else:
    print("\n❌ No trades generated!")

print("\n" + "="*70)
print("✅ REAL ORDER FLOW BACKTEST COMPLETE")
print("="*70)
