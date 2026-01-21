
import pandas as pd
import numpy as np
import joblib
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.v5_feature_engineer import generate_v5_features

# Hyperliquid fees
TAKER_FEE = 0.0005  # 0.05%

def backtest_v8_simple():
    print("🎯 Backtesting V8 Simple Strategy (Jan 2026 + Fees)...")
    
    # Load data
    data_path = 'training/data/BTC_5m_2025_enriched.csv'
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Filter to Jan 2026
    df_test = df[df['timestamp'] >= '2026-01-01'].copy().reset_index(drop=True)
    print(f"   📅 Test Period: {df_test['timestamp'].min()} to {df_test['timestamp'].max()}")
    
    # Load model
    model_path = 'model_engines/v8_simple/weights/v8_simple.pkl'
    feature_path = 'model_engines/v8_simple/weights/feature_names.txt'
    
    model = joblib.load(model_path)
    with open(feature_path, 'r') as f:
        feature_cols = [line.strip() for line in f.readlines()]
    
    print(f"   ✅ Loaded V8 Simple model")
    
    # Generate features
    print("   🧠 Generating Features...")
    df_enriched = generate_v5_features(df_test)
    
    # Predict
    predictions = model.predict(df_enriched[feature_cols])
    probs = model.predict_proba(df_enriched[feature_cols])
    
    df_enriched['v8_pred'] = predictions
    df_enriched['prob_long'] = probs[:, 0]
    df_enriched['prob_short'] = probs[:, 1]
    df_enriched['prob_neutral'] = probs[:, 2]
    
    # Simulate trading
    print("\n   🚀 Simulating Trades...")
    
    balance = 10000.0
    tp = 0.005  # 0.5%
    sl = 0.0015  # 0.15%
    
    long_trades = 0
    long_wins = 0
    short_trades = 0
    short_wins = 0
    
    total_fees = 0
    trade_log = []
    
    in_trade = None
    entry_price = 0
    entry_time = None
    trade_type = None
    
    for i in range(200, len(df_enriched) - 1):
        row = df_enriched.iloc[i]
        
        # Manage existing trade
        if in_trade:
            # Calculate fees
            notional = balance
            trade_fee = notional * TAKER_FEE * 2  # Entry + exit
            
            if trade_type == 'LONG':
                if row['high'] >= entry_price * (1 + tp):
                    long_wins += 1
                    gross_pnl = balance * tp
                    net_pnl = gross_pnl - trade_fee
                    balance += net_pnl
                    total_fees += trade_fee
                    trade_log.append({'type': 'LONG', 'outcome': 'WIN', 'gross': gross_pnl, 'fee': trade_fee, 'net': net_pnl})
                    in_trade = None
                elif row['low'] <= entry_price * (1 - sl):
                    gross_pnl = -balance * sl
                    net_pnl = gross_pnl - trade_fee
                    balance += net_pnl
                    total_fees += trade_fee
                    trade_log.append({'type': 'LONG', 'outcome': 'LOSS', 'gross': gross_pnl, 'fee': trade_fee, 'net': net_pnl})
                    in_trade = None
                    
            elif trade_type == 'SHORT':
                if row['low'] <= entry_price * (1 - tp):
                    short_wins += 1
                    gross_pnl = balance * tp
                    net_pnl = gross_pnl - trade_fee
                    balance += net_pnl
                    total_fees += trade_fee
                    trade_log.append({'type': 'SHORT', 'outcome': 'WIN', 'gross': gross_pnl, 'fee': trade_fee, 'net': net_pnl})
                    in_trade = None
                elif row['high'] >= entry_price * (1 + sl):
                    gross_pnl = -balance * sl
                    net_pnl = gross_pnl - trade_fee
                    balance += net_pnl
                    total_fees += trade_fee
                    trade_log.append({'type': 'SHORT', 'outcome': 'LOSS', 'gross': gross_pnl, 'fee': trade_fee, 'net': net_pnl})
                    in_trade = None
            continue
        
        # Entry logic
        pred = row['v8_pred']
        
        if pred == 0:  # Long
            in_trade = True
            entry_price = row['close']
            trade_type = 'LONG'
            long_trades += 1
            
        elif pred == 1:  # Short
            in_trade = True
            entry_price = row['close']
            trade_type = 'SHORT'
            short_trades += 1
    
    # Results
    gross_pnl = balance - 10000 + total_fees
    net_pnl = balance - 10000
    
    print(f"\n   📊 RESULTS:")
    print(f"   Gross PnL (no fees):     +\${gross_pnl:.2f} ({(gross_pnl/10000)*100:+.2f}%)")
    print(f"   Total Fees Paid:         -\${total_fees:.2f} ({(total_fees/10000)*100:.2f}%)")
    print(f"   Net PnL (after fees):    \${net_pnl:.2f} ({(net_pnl/10000)*100:+.2f}%)")
    print(f"\n   Long Trades: {long_trades}, Wins: {long_wins}, WR: {long_wins/long_trades:.1%}" if long_trades > 0 else "   Long Trades: 0")
    print(f"   Short Trades: {short_trades}, Wins: {short_wins}, WR: {short_wins/short_trades:.1%}" if short_trades > 0 else "   Short Trades: 0")
    print(f"\n   Total Trades: {long_trades + short_trades}")
    print(f"   Trades/Day: {(long_trades + short_trades) / 14:.1f}")
    print(f"   Fee per trade: \${total_fees/(long_trades + short_trades):.2f}" if (long_trades + short_trades) > 0 else "")
    
    # Profitability check
    if net_pnl > 0:
        print(f"\n   ✅ PROFITABLE after fees!")
        print(f"   At 27x leverage: {(net_pnl/10000)*27*100:+.2f}%")
    else:
        print(f"\n   ❌ NOT PROFITABLE after fees")

if __name__ == "__main__":
    backtest_v8_simple()
