
import pandas as pd
import numpy as np
import joblib
import os
import sys

# Add root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.v5_feature_engineer import generate_v5_features

def backtest_grid():
    print("🚀 Starting Dynamic Grid Backtest (Jan 2026)...")
    
    # 1. Load Data
    data_path = 'training/data/BTC_5m_2025_enriched.csv'
    if not os.path.exists(data_path):
        print("❌ Data not found")
        return
        
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # 2. Load Model
    model_path = 'model_engines/volatility_v1/weights/vol_model.pkl'
    if not os.path.exists(model_path):
        print("❌ Model not found")
        return
        
    model = joblib.load(model_path)
    
    # 3. Features
    print("   🧠 Generating Features...")
    df = generate_v5_features(df)
    
    # 4. Filter for Test Period (Jan 2026)
    df = df[df['timestamp'] >= '2026-01-01'].copy().reset_index(drop=True)
    print(f"   📊 Test Data: {len(df)} candles")
    
    # 5. Predict Volatility
    features = [c for c in df.columns if c not in ['timestamp', 'target', 'open', 'high', 'low', 'close', 
                                                 'taker_buy_base', 'taker_sell_base', 'future_high', 'future_low', 'future_range_pct']]
                                                 
    print("   🔮 Predicting Regimes...")
    probs = model.predict_proba(df[features])
    df['prob_low'] = probs[:, 0]
    df['prob_high'] = probs[:, 2]
    
    # 6. Grid Simulation
    # Simple Grid Logic:
    # - If Prob(Low) > 0.7: Place Grid +/- 0.2%. If High/Low touches these levels within 5m, we profit.
    # - If Prob(High) > 0.7: Stay Out / Close Positions.
    
    initial_balance = 10000
    balance = initial_balance
    positions = 0
    
    equity_curve = []
    trades = 0
    wins = 0
    
    # Fees (Hyperliquid Taker: 0.035%, Maker: 0.01% ... let's assume Maker rebates or low fee for Limit orders)
    # Grid bots usually pay Maker fees. Let's assume 0.01% fee per leg.
    fee_rate = 0.0001
    
    print("   🤖 Running Grid Simulation...")
    
    for i in range(len(df) - 1):
        row = df.iloc[i]
        next_row = df.iloc[i+1] # Look at NEXT candle to see if grid was hit
        
        price = row['close']
        
        # DECISION LOGIC
        if row['prob_low'] > 0.70:
            # MODE: TIGHT GRID (CHOP FARMING)
            # Strategy: Sell Limit @ +0.2%, Buy Limit @ -0.2%
            # If Price moves through them, we accumulate profit.
            # Simplified: If High > LimitSell or Low < LimitBuy
            
            grid_spacing = 0.002 # 0.2%
            sell_level = price * (1 + grid_spacing)
            buy_level = price * (1 - grid_spacing)
            
            # Check if Hit in NEXT candle
            # (We assume we placed orders at Close of candle 'i')
            
            # Hit Sell?
            if next_row['high'] >= sell_level:
                # We sold. Profit is the spread? 
                # Grid profit logic: You buy low, sell high. 
                # A single leg execution isn't profit yet, but for simplicity:
                # Assume we successfully capture the "wiggle".
                # Profit = Position Size * Grid Spacing
                
                # Let's say we trade $1000 size
                trade_size = 1000
                profit = trade_size * grid_spacing
                fee = trade_size * fee_rate
                
                balance += (profit - fee)
                trades += 1
                wins += 1 # Grid hit is a win
                
            # Hit Buy?
            if next_row['low'] <= buy_level:
                trade_size = 1000
                profit = trade_size * grid_spacing
                fee = trade_size * fee_rate
                
                balance += (profit - fee)
                trades += 1
                wins += 1
                
        elif row['prob_high'] > 0.70:
            # MODE: DANGER / HEDGE
            # Here we just stay out.
            # Ideally we would close existing positions, but this sim is stateless per candle
            pass
            
        # Drawdown check?
        # If we are in a grid and price blasts through ONE side without returning, we hold a bag.
        # This simple sim assumes mean reversion.
        # We need to penalize if "High Vol" actually happens while we are in "Low Vol" mode.
        
        # Penalty Logic:
        # If we predicted Low Vol, but Next Candle Range > 0.5%, we take a LOSS.
        next_range = (next_row['high'] - next_row['low']) / next_row['open']
        if row['prob_low'] > 0.70 and next_range > 0.005:
            # We got run over.
            # Loss = Position * Move
            loss = 1000 * next_range
            balance -= loss
            wins -= 1 # Correct the win count? Or just add a loss?
            trades += 1
            # (Strictly this is a "failed grid" event)
            
        equity_curve.append(balance)

    # Report
    print(f"\n   🏁 Backtest Complete")
    print(f"      Initial: ${initial_balance}")
    print(f"      Final:   ${balance:.2f}")
    print(f"      PnL:     {((balance/initial_balance)-1)*100:.2f}%")
    print(f"      Trades:  {trades}")
    print(f"      Grid Hits vs Blowouts included.")

if __name__ == "__main__":
    backtest_grid()
