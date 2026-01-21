
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.v5_feature_engineer import generate_v5_features
from model_engines.v7_handcrafted.engine import V7HandcraftedEngine

# Hyperliquid fees
TAKER_FEE = 0.0005  # 0.05%

def backtest_v7_final():
    print("🎯 Backtesting V7 Hand-Crafted Strategy (Jan 2026 + Fees)...")
    
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
    print(f"   ✅ Loaded {engine.name}")
    
    # Simulate trading
    print("\n   🚀 Simulating Trades...")
    
    balance = 10000.0
    tp = 0.005
    sl = 0.0015
    
    long_trades = 0
    long_wins = 0
    short_trades = 0
    short_wins = 0
    
    total_fees_pct = 0
    trade_log = []
    
    in_trade = None
    entry_price = 0
    trade_type = None
    
    for i in range(200, len(df_enriched) - 1):
        row = df_enriched.iloc[i]
        
        # Manage existing trade
        if in_trade:
            if trade_type == 'LONG':
                if row['high'] >= entry_price * (1 + tp):
                    long_wins += 1
                    gross_pnl_pct = tp
                    fee_pct = TAKER_FEE * 2
                    net_pnl_pct = gross_pnl_pct - fee_pct
                    total_fees_pct += fee_pct
                    trade_log.append({'type': 'LONG', 'outcome': 'WIN', 'net_pnl_pct': net_pnl_pct})
                    in_trade = None
                elif row['low'] <= entry_price * (1 - sl):
                    gross_pnl_pct = -sl
                    fee_pct = TAKER_FEE * 2
                    net_pnl_pct = gross_pnl_pct - fee_pct
                    total_fees_pct += fee_pct
                    trade_log.append({'type': 'LONG', 'outcome': 'LOSS', 'net_pnl_pct': net_pnl_pct})
                    in_trade = None
                    
            elif trade_type == 'SHORT':
                if row['low'] <= entry_price * (1 - tp):
                    short_wins += 1
                    gross_pnl_pct = tp
                    fee_pct = TAKER_FEE * 2
                    net_pnl_pct = gross_pnl_pct - fee_pct
                    total_fees_pct += fee_pct
                    trade_log.append({'type': 'SHORT', 'outcome': 'WIN', 'net_pnl_pct': net_pnl_pct})
                    in_trade = None
                elif row['high'] >= entry_price * (1 + sl):
                    gross_pnl_pct = -sl
                    fee_pct = TAKER_FEE * 2
                    net_pnl_pct = gross_pnl_pct - fee_pct
                    total_fees_pct += fee_pct
                    trade_log.append({'type': 'SHORT', 'outcome': 'LOSS', 'net_pnl_pct': net_pnl_pct})
                    in_trade = None
            continue
        
        # Get signal from engine
        signal = engine.analyze(df_enriched.iloc[:i+1])
        
        if signal['signal'] == 'LONG':
            in_trade = True
            entry_price = row['close']
            trade_type = 'LONG'
            long_trades += 1
            
        elif signal['signal'] == 'SHORT':
            in_trade = True
            entry_price = row['close']
            trade_type = 'SHORT'
            short_trades += 1
    
    # Calculate results
    total_trades = long_trades + short_trades
    total_wins = long_wins + short_wins
    
    gross_pnl_pct = sum([t['net_pnl_pct'] + (TAKER_FEE * 2) for t in trade_log])
    net_pnl_pct = sum([t['net_pnl_pct'] for t in trade_log])
    
    print(f"\n   📊 RESULTS:")
    print(f"   Gross PnL (no fees):     {gross_pnl_pct*100:+.2f}%")
    print(f"   Total Fees:              -{total_fees_pct*100:.2f}%")
    print(f"   Net PnL (after fees):    {net_pnl_pct*100:+.2f}%")
    print(f"\n   Long: {long_trades} trades, {long_wins} wins, WR: {long_wins/long_trades:.1%}" if long_trades > 0 else "   Long: 0 trades")
    print(f"   Short: {short_trades} trades, {short_wins} wins, WR: {short_wins/short_trades:.1%}" if short_trades > 0 else "   Short: 0 trades")
    print(f"\n   Total Trades: {total_trades}")
    print(f"   Total Wins: {total_wins}")
    print(f"   Overall WR: {total_wins/total_trades:.1%}" if total_trades > 0 else "   No trades")
    print(f"   Trades/Day: {total_trades/14:.1f}")
    
    if net_pnl_pct > 0:
        print(f"\n   ✅ PROFITABLE after fees!")
        print(f"   Final Balance: ${10000 * (1 + net_pnl_pct):.2f}")
        print(f"   At 27x leverage: {net_pnl_pct * 27 * 100:+.2f}%")
    else:
        print(f"\n   ❌ NOT PROFITABLE after fees")
        print(f"   Loss: ${10000 * abs(net_pnl_pct):.2f}")

if __name__ == "__main__":
    backtest_v7_final()
