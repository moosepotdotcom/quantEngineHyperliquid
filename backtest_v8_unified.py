
import pandas as pd
import numpy as np
import joblib
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.v5_feature_engineer import generate_v5_features

def backtest_v8_unified():
    print("🎯 Backtesting V8 Unified Strategy (Jan 2026)...")
    
    # Load data
    data_path = 'training/data/BTC_5m_2025_enriched.csv'
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Filter to Jan 2026 ONLY (out-of-sample)
    df_test = df[df['timestamp'] >= '2026-01-01'].copy().reset_index(drop=True)
    print(f"   📅 Test Period: {df_test['timestamp'].min()} to {df_test['timestamp'].max()}")
    print(f"   📊 Candles: {len(df_test)}")
    
    # Load model and feature names
    model_path = 'model_engines/v8_unified/weights/v8_unified.pkl'
    feature_path = 'model_engines/v8_unified/weights/feature_names.txt'
    
    model = joblib.load(model_path)
    with open(feature_path, 'r') as f:
        feature_cols = [line.strip() for line in f.readlines()]
    
    print(f"   ✅ Loaded V8 model with {len(feature_cols)} features")
    
    # Generate features
    print("   🧠 Generating Features...")
    df_enriched = generate_v5_features(df_test)
    
    # Predict
    print("   🔮 Running Predictions...")
    
    # Ensure all required features exist (fill missing with 0)
    for col in feature_cols:
        if col not in df_enriched.columns:
            df_enriched[col] = 0
            print(f"      ⚠️ Missing feature '{col}', filled with 0")
    
    predictions = model.predict(df_enriched[feature_cols])
    probs = model.predict_proba(df_enriched[feature_cols])
    
    df_enriched['v8_pred'] = predictions
    df_enriched['prob_grid'] = probs[:, 0]
    df_enriched['prob_long'] = probs[:, 1]
    df_enriched['prob_short'] = probs[:, 2]
    df_enriched['prob_neutral'] = probs[:, 3]
    
    # Simulate trading
    print("\n   🚀 Simulating Trades...")
    
    balance = 10000.0
    initial_balance = 10000.0
    
    grid_trades = 0
    grid_wins = 0
    long_trades = 0
    long_wins = 0
    short_trades = 0
    short_wins = 0
    
    in_trade = None
    entry_price = 0
    trade_type = None
    entry_time = None
    
    trade_log = []
    
    for i in range(200, len(df_enriched) - 1):
        row = df_enriched.iloc[i]
        
        # Manage existing trade
        if in_trade:
            if trade_type == 'GRID':
                # Grid: 0.1% target, 0.05% stop
                tp_price = entry_price * 1.001
                sl_price = entry_price * 0.9995
                
                if row['high'] >= tp_price:
                    grid_wins += 1
                    pnl = (tp_price - entry_price) / entry_price * 100
                    balance *= 1.001
                    trade_log.append({
                        'entry_time': entry_time,
                        'exit_time': row['timestamp'],
                        'type': 'GRID',
                        'entry_price': entry_price,
                        'tp_price': tp_price,
                        'sl_price': sl_price,
                        'exit_price': tp_price,
                        'exit_reason': 'TP_HIT',
                        'pnl_pct': pnl,
                        'pnl_usd': (balance - 10000) if grid_wins == 1 else None,
                        'outcome': 'WIN'
                    })
                    in_trade = None
                elif row['low'] <= sl_price:
                    pnl = (sl_price - entry_price) / entry_price * 100
                    balance *= 0.9995
                    trade_log.append({
                        'entry_time': entry_time,
                        'exit_time': row['timestamp'],
                        'type': 'GRID',
                        'entry_price': entry_price,
                        'tp_price': tp_price,
                        'sl_price': sl_price,
                        'exit_price': sl_price,
                        'exit_reason': 'SL_HIT',
                        'pnl_pct': pnl,
                        'pnl_usd': (balance - 10000) if grid_trades - grid_wins == 1 else None,
                        'outcome': 'LOSS'
                    })
                    in_trade = None
                    
            elif trade_type == 'LONG':
                # Long: 0.5% target, 0.15% stop
                if row['high'] >= entry_price * 1.005:
                    long_wins += 1
                    balance *= 1.005
                    in_trade = None
                elif row['low'] <= entry_price * 0.9985:
                    balance *= 0.9985
                    in_trade = None
                    
            elif trade_type == 'SHORT':
                # Short: 0.5% target, 0.15% stop
                if row['low'] <= entry_price * 0.995:
                    short_wins += 1
                    balance *= 1.005
                    in_trade = None
                elif row['high'] >= entry_price * 1.0015:
                    balance *= 0.9985
                    in_trade = None
            continue
        
        # Entry logic based on prediction
        pred = row['v8_pred']
        
        if pred == 0:  # Grid
            in_trade = True
            entry_price = row['close']
            entry_time = row['timestamp']
            trade_type = 'GRID'
            grid_trades += 1
            
        elif pred == 1:  # Long
            in_trade = True
            entry_price = row['close']
            entry_time = row['timestamp']
            trade_type = 'LONG'
            long_trades += 1
            
        elif pred == 2:  # Short
            in_trade = True
            entry_price = row['close']
            trade_type = 'SHORT'
            short_trades += 1
        
        # pred == 3 (Neutral) → do nothing
    
    # Results
    pnl = ((balance / initial_balance) - 1) * 100
    
    print(f"\n   📊 RESULTS:")
    print(f"   Final Balance: ${balance:.2f}")
    print(f"   PnL: {pnl:+.2f}%")
    print(f"\n   Grid Trades: {grid_trades}, Wins: {grid_wins}, WR: {grid_wins/grid_trades:.1%}" if grid_trades > 0 else "   Grid Trades: 0")
    print(f"   Long Trades: {long_trades}, Wins: {long_wins}, WR: {long_wins/long_trades:.1%}" if long_trades > 0 else "   Long Trades: 0")
    print(f"   Short Trades: {short_trades}, Wins: {short_wins}, WR: {short_wins/short_trades:.1%}" if short_trades > 0 else "   Short Trades: 0")
    print(f"\n   Total Trades: {grid_trades + long_trades + short_trades}")
    print(f"   Trades/Day: {(grid_trades + long_trades + short_trades) / 14:.1f}")
    
    # Save trade log
    if trade_log:
        df_log = pd.DataFrame(trade_log)
        log_path = 'V8_TRADE_LOG_DETAILED.csv'
        df_log.to_csv(log_path, index=False)
        print(f"\n   📝 Detailed trade log saved to {log_path}")
        
        # Show sample trades with ALL details
        print(f"\n   📋 Sample Trades (first 5 with complete details):")
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        print(df_log.head(5).to_string(index=False))
        
        # Show last 5 trades
        print(f"\n   📋 Last 5 Trades:")
        print(df_log.tail(5).to_string(index=False))
        
        # Statistics
        print(f"\n   📊 Trade Statistics:")
        print(f"      Avg Win: +{df_log[df_log['outcome']=='WIN']['pnl_pct'].mean():.3f}%")
        print(f"      Avg Loss: {df_log[df_log['outcome']=='LOSS']['pnl_pct'].mean():.3f}%")
        print(f"      Largest Win: +{df_log['pnl_pct'].max():.3f}%")
        print(f"      Largest Loss: {df_log['pnl_pct'].min():.3f}%")
        
        # Daily breakdown
        df_log['date'] = pd.to_datetime(df_log['entry_time']).dt.date
        daily = df_log.groupby('date').agg({
            'outcome': 'count',
            'pnl_pct': 'sum'
        }).rename(columns={'outcome': 'trades', 'pnl_pct': 'daily_pnl'})
        print(f"\n   📅 Daily Breakdown:")
        print(daily.to_string())

if __name__ == "__main__":
    backtest_v8_unified()
