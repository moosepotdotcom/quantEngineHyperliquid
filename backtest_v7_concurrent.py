
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.v5_feature_engineer import generate_v5_features
from model_engines.v7_handcrafted.engine import V7HandcraftedEngine

# Hyperliquid fees
TAKER_FEE = 0.0005  # 0.05%

def backtest_v7_concurrent():
    print("🎯 V7 Hand-Crafted with CONCURRENT TRADES (Jan 2026)...")
    
    # Load data
    data_path = 'training/data/BTC_5m_2025_enriched.csv'
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Filter to Jan 2026
    df_test = df[df['timestamp'] >= '2026-01-01'].copy().reset_index(drop=True)
    print(f"   📅 Test Period: {df_test['timestamp'].min()} to {df_test['timestamp'].max()}")
    
    # Generate features
    print("   🧠 Generating Features...")
    df_enriched = generate_v5_features(df_test)
    
    # Initialize engine
    engine = V7HandcraftedEngine()
    
    # Simulate with CONCURRENT TRADES
    print("\n   🚀 Simulating with Multiple Concurrent Positions...")
    
    balance = 10000.0
    tp = 0.005
    sl = 0.0015
    
    # Track multiple active trades
    active_trades = []
    completed_trades = []
    
    max_concurrent = 0
    
    for i in range(200, len(df_enriched) - 1):
        row = df_enriched.iloc[i]
        
        # Manage active trades
        for trade in active_trades[:]:  # Copy list to allow removal during iteration
            if trade['type'] == 'LONG':
                if row['high'] >= trade['tp']:
                    # Win
                    gross_pnl_pct = tp
                    fee_pct = TAKER_FEE * 2
                    net_pnl_pct = gross_pnl_pct - fee_pct
                    completed_trades.append({
                        'type': 'LONG',
                        'outcome': 'WIN',
                        'gross_pnl_pct': gross_pnl_pct,
                        'fee_pct': fee_pct,
                        'net_pnl_pct': net_pnl_pct
                    })
                    active_trades.remove(trade)
                elif row['low'] <= trade['sl']:
                    # Loss
                    gross_pnl_pct = -sl
                    fee_pct = TAKER_FEE * 2
                    net_pnl_pct = gross_pnl_pct - fee_pct
                    completed_trades.append({
                        'type': 'LONG',
                        'outcome': 'LOSS',
                        'gross_pnl_pct': gross_pnl_pct,
                        'fee_pct': fee_pct,
                        'net_pnl_pct': net_pnl_pct
                    })
                    active_trades.remove(trade)
                    
            elif trade['type'] == 'SHORT':
                if row['low'] <= trade['tp']:
                    # Win
                    gross_pnl_pct = tp
                    fee_pct = TAKER_FEE * 2
                    net_pnl_pct = gross_pnl_pct - fee_pct
                    completed_trades.append({
                        'type': 'SHORT',
                        'outcome': 'WIN',
                        'gross_pnl_pct': gross_pnl_pct,
                        'fee_pct': fee_pct,
                        'net_pnl_pct': net_pnl_pct
                    })
                    active_trades.remove(trade)
                elif row['high'] >= trade['sl']:
                    # Loss
                    gross_pnl_pct = -sl
                    fee_pct = TAKER_FEE * 2
                    net_pnl_pct = gross_pnl_pct - fee_pct
                    completed_trades.append({
                        'type': 'SHORT',
                        'outcome': 'LOSS',
                        'gross_pnl_pct': gross_pnl_pct,
                        'fee_pct': fee_pct,
                        'net_pnl_pct': net_pnl_pct
                    })
                    active_trades.remove(trade)
        
        # Check for new signal
        signal = engine.analyze(df_enriched.iloc[:i+1])
        
        if signal['signal'] == 'LONG':
            active_trades.append({
                'type': 'LONG',
                'entry': row['close'],
                'tp': row['close'] * (1 + tp),
                'sl': row['close'] * (1 - sl)
            })
            
        elif signal['signal'] == 'SHORT':
            active_trades.append({
                'type': 'SHORT',
                'entry': row['close'],
                'tp': row['close'] * (1 - tp),
                'sl': row['close'] * (1 + sl)
            })
        
        # Track max concurrent
        if len(active_trades) > max_concurrent:
            max_concurrent = len(active_trades)
    
    # Calculate results
    df_trades = pd.DataFrame(completed_trades)
    
    total_trades = len(df_trades)
    wins = len(df_trades[df_trades['outcome'] == 'WIN'])
    losses = len(df_trades[df_trades['outcome'] == 'LOSS'])
    
    gross_pnl_pct = df_trades['gross_pnl_pct'].sum()
    total_fees_pct = df_trades['fee_pct'].sum()
    net_pnl_pct = df_trades['net_pnl_pct'].sum()
    
    print(f"\n   📊 RESULTS:")
    print(f"   Total Trades: {total_trades}")
    print(f"   Wins: {wins}, Losses: {losses}")
    print(f"   Win Rate: {wins/total_trades:.1%}" if total_trades > 0 else "   No trades")
    print(f"   Max Concurrent: {max_concurrent} positions")
    print(f"   Trades/Day: {total_trades/14:.1f}")
    print()
    print(f"   Gross PnL (no fees):     {gross_pnl_pct*100:+.2f}%")
    print(f"   Total Fees:              -{total_fees_pct*100:.2f}%")
    print(f"   Net PnL (after fees):    {net_pnl_pct*100:+.2f}%")
    
    if net_pnl_pct > 0:
        print(f"\n   ✅ PROFITABLE after fees!")
        print(f"   Final Balance: ${10000 * (1 + net_pnl_pct):.2f}")
        print(f"   At 27x leverage: {net_pnl_pct * 27 * 100:+.2f}%")
    else:
        print(f"\n   ❌ NOT PROFITABLE after fees")

if __name__ == "__main__":
    backtest_v7_concurrent()
