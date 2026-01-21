
import pandas as pd
import sys
import os

# Add root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from model_engines.v6_grid.engine import V6GridEngine

def run_production_backtest():
    print("🚀 Starting FINAL V6 Production Backtest (Jan 1-14, 2026)...")
    
    # 1. Initialize Production Engine
    engine = V6GridEngine()
    engine.initialize()
    
    # 2. Load Data
    data_path = 'training/data/BTC_5m_2025_enriched.csv'
    if not os.path.exists(data_path):
        print("❌ Data not found")
        return
        
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Filter for Jan 1-14 2026
    df = df[df['timestamp'] >= '2026-01-01'].copy().reset_index(drop=True)
    print(f"   📊 Loaded {len(df)} candles")
    
    # 3. Simulate Trading
    initial_balance = 10000.0
    balance = initial_balance
    trades = 0
    wins = 0
    
    # Parameters for simulation matching engine
    grid_spacing = 0.001
    fee_rate = 0.0001
    trade_size = 1000.0
    
    # History Window (Warmup)
    start_idx = 1000 
    
    equity_curve = [initial_balance]
    
    print("   🏎️  Processing Candles...")
    
    # We loop through data
    for i in range(start_idx, len(df) - 1):
        # Current slice
        # Ideally we pass only history to analyze() to prevent lookahead
        # But analyze() calculates features on the fly. Doing this 4000 times is slow.
        # OPTIMIZATION: We can pre-calculate features and pass them, but engine.analyze() 
        # is designed to take raw OHLCV.
        # For strict correctness, we pass raw history.
        # To save time, we will assume features are robust (they are rolling) 
        # and checking if we can optimize test speed.
        
        # Actually, let's trust the engine's internal feature generation speed.
        # It takes ~10-20ms per call. 3000 candles * 20ms = 60 seconds. Acceptable.
        
        history = df.iloc[i-1000:i+1].copy()
        next_candle = df.iloc[i+1]
        
        signal = engine.analyze(history)
        
        if signal.signal_type == 'GRID':
            # EXECUTION SIMULATION
            # Buy Limit @ price - 0.1%
            # Sell Limit @ price + 0.1%
            
            buy_price = signal.grid_buy_level
            sell_price = signal.grid_sell_level
            
            # Check Next Candle High/Low
            # Did we get filled on Buy?
            if next_candle['low'] <= buy_price:
                # Filled. Did we exit?
                # Grid usually means: Buy Low, Sell High.
                # If we bought at BuyPrice, we want to sell at Entry (or Entry + Spacing).
                # Simplified Grid: Capture the spread.
                # Profit = Spacing - Fees
                
                # Assume complete cycle capture if volatility is low (reversion)
                profit = trade_size * grid_spacing
                cost = trade_size * fee_rate * 2 # Entry + Exit
                
                balance += (profit - cost)
                trades += 1
                wins += 1
                
            # Did we get filled on Sell?
            if next_candle['high'] >= sell_price:
                profit = trade_size * grid_spacing
                cost = trade_size * fee_rate * 2
                
                balance += (profit - cost)
                trades += 1
                wins += 1
                
            # BLOWOUT CHECK (Same as prior logic)
            # If range > 3x spacing, assume we got run over
            rng = (next_candle['high'] - next_candle['low']) / next_candle['open']
            if rng > (grid_spacing * 3):
                loss = trade_size * rng
                balance -= loss
                
        equity_curve.append(balance)
        
        if i % 100 == 0:
            print(f"   📅 {df.iloc[i]['timestamp']} | Bal: ${balance:.2f}", end='\r')
            
    print(f"\n   🏁 FINAL RESULT:")
    print(f"      Initial: ${initial_balance}")
    print(f"      Final:   ${balance:.2f}")
    print(f"      PnL:     {((balance/initial_balance)-1)*100:.2f}%")
    print(f"      Trades:  {trades}")
    print(f"      Win Rate: N/A (Grid)")
    
if __name__ == "__main__":
    run_production_backtest()
