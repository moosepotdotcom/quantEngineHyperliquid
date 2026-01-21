
import pandas as pd
import sys
import os
import joblib

# Add root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.v5_feature_engineer import generate_v5_features

def research_v7_simulation():
    print("🎰 Simulating V7 'Jackpot' Strategy (Decision Tree Rules)...")
    
    # 1. Load Data
    data_path = 'training/data/BTC_5m_2025_enriched.csv'
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Filter for Jan 2026
    df = df[df['timestamp'] >= '2026-01-01'].copy().reset_index(drop=True)
    
    # 2. Load Volatility Model
    model = joblib.load('model_engines/v6_grid/weights/vol_model.pkl')
    
    # 3. Features
    print("   🧠 Generating Features...")
    df_enriched = generate_v5_features(df)
    
    # Predict High Vol
    drop_cols_engine = ['timestamp', 'target', 'open', 'high', 'low', 'close', 
                 'taker_buy_base', 'taker_sell_base', 'future_high', 'future_low', 'future_range_pct',
                 'prob_low', 'prob_high', 'jackpot_label']
                 
    features = [c for c in df_enriched.columns if c not in drop_cols_engine]
    
    probs = model.predict_proba(df_enriched[features])
    df_enriched['prob_high_vol'] = probs[:, 2]
    
    # 4. Simulation
    # Rules:
    # BUY: High Vol > 0.70 AND ema_50_15m > price (Price below EMA) AND rsi_15m <= 63
    # SELL: High Vol > 0.70 AND ema_50_15m < price (Price above EMA) AND flow_imbalance_15m < 0.10
    
    balance = 10000.0
    initial_balance = 10000.0
    
    # Aggressive Targets for "Jackpot"
    profit_target = 0.02 # 2% Target
    stop_loss = 0.01     # 1% Stop
    
    wins = 0
    losses = 0
    trades = 0
    
    # Skip warmup
    start_idx = 200 
    
    print("\n   🚀 Running V7 Simulation (Jan 2026)...")
    
    in_trade = None # 'LONG', 'SHORT'
    entry_price = 0
    
    trade_log = []
    
    for i in range(start_idx, len(df_enriched) - 1):
        row = df_enriched.iloc[i]
        
        # Management
        if in_trade:
            if in_trade == 'LONG':
                if row['high'] >= entry_price * (1 + profit_target):
                    wins += 1
                    balance *= (1 + profit_target)
                    in_trade = None
                    trade_log.append("WIN")
                elif row['low'] <= entry_price * (1 - stop_loss):
                    losses += 1
                    balance *= (1 - stop_loss)
                    in_trade = None
                    trade_log.append("LOSS")
                    
            elif in_trade == 'SHORT':
                if row['low'] <= entry_price * (1 - profit_target):
                    wins += 1
                    balance *= (1 + profit_target)
                    in_trade = None
                    trade_log.append("WIN")
                elif row['high'] >= entry_price * (1 + stop_loss):
                    losses += 1
                    balance *= (1 - stop_loss)
                    in_trade = None
                    trade_log.append("LOSS")
            continue 
            
        # Entry Logic (Only if NO trade)
        is_high_vol = row['prob_high_vol'] > 0.70
        if not is_high_vol:
            continue
            
        ema_50 = row.get('ema_50_15m', 0)
        rsi_15m = row.get('rsi_15m', 50)
        imbalance = row.get('flow_imbalance_15m', 0) # Need to ensure this exists or use 'flow_imbalance'
        if 'flow_imbalance_15m' not in row:
             imbalance = row.get('flow_imbalance', 0)
        
        # BUY SIGNAL (Dip Buy)
        # Price < EMA (Dipt) AND RSI Not Overbought
        if row['close'] < ema_50 and rsi_15m <= 63:
            in_trade = 'LONG'
            entry_price = row['close']
            trades += 1
            
        # SELL SIGNAL (Top Sell)
        # Price > EMA (Spike) AND Weak Flow
        elif row['close'] > ema_50 and imbalance < 0.10:
            in_trade = 'SHORT'
            entry_price = row['close']
            trades += 1
            
    print(f"   Trades: {trades}")
    print(f"   Wins: {wins}")
    print(f"   Losses: {losses}")
    
    if trades > 0:
        wr = wins / trades
        print(f"   Win Rate: {wr:.1%}")
        print(f"   Final Balance: ${balance:.2f}")
        print(f"   PnL: {((balance/initial_balance) - 1)*100:.2f}%")
    else:
        print("   No Trades found.")

if __name__ == "__main__":
    research_v7_simulation()
