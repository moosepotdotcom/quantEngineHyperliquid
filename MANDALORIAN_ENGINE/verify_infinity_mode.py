import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime

# Add path to engine
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from phase3_engine import Phase3Trader, CONFIG

def run_verification():
    print("="*60)
    print("🧪 PHASE 3 VERIFICATION: INFINITY MODE (Trailing Stop)")
    print("="*60)
    
    # 1. Load Data
    data_file = "jan2026_binance_data.csv"
    if not os.path.exists(data_file):
        print(f"❌ Missing {data_file}")
        return
        
    print(f"🔄 Loading {data_file}...")
    df = pd.read_csv(data_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Setup Trader in Simulation Mode
    trader = Phase3Trader(dry_run=True)
    trader.state["balance"] = 10000.0 
    trader.state["positions"] = {}
    trader.state["trade_history"] = []
    
    class BacktestTrader(Phase3Trader):
        def fetch_and_prepare_data(self):
            return self.current_slice
            
    test_trader = BacktestTrader(dry_run=True)
    test_trader.state["balance"] = 10000.0
    
    print("   🔧 Pre-calculating Indicators (Batch)...")
    from quant_engine import add_all_indicators, MTF_FEATURE_LIST
    from utils.advanced_features import add_advanced_features

    full_df = add_all_indicators(df)
    full_df = add_advanced_features(full_df)
    
    full_df.set_index('timestamp', inplace=True)
    
    df15 = full_df.resample('15T').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
    df15 = add_all_indicators(df15)
    df15 = add_advanced_features(df15)
    
    df1h = full_df.resample('1H').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
    df1h = add_all_indicators(df1h)
    df1h = add_advanced_features(df1h)
    
    exclude = ['open', 'high', 'low', 'close', 'volume']
    ctx15 = [c for c in df15.columns if c not in exclude]
    df15_renamed = df15[ctx15].rename(columns={c: f"{c}_15m" for c in ctx15})
    full_df = pd.concat([full_df, df15_renamed.reindex(full_df.index, method='ffill')], axis=1)
    
    ctx1h = [c for c in df1h.columns if c not in exclude]
    df1h_renamed = df1h[ctx1h].rename(columns={c: f"{c}_1h" for c in ctx1h})
    full_df = pd.concat([full_df, df1h_renamed.reindex(full_df.index, method='ffill')], axis=1)
    
    full_df.dropna(inplace=True)
    full_df.reset_index(inplace=True)
    
    print(f"   ✅ Data Prepared: {len(full_df)} candles")
    
    X_dict = {c: full_df[c].values for c in MTF_FEATURE_LIST}
    X = np.column_stack([X_dict[c] for c in MTF_FEATURE_LIST])
    X = np.nan_to_num(X, nan=0.0)
    
    print("   🤖 Batch Inference...")
    probas = test_trader.engine.get_ensemble_proba('MTF', X)
    
    print("   🏃 Running Trade Loop with TRAILING STOPS...")
    
    positions = [] 
    history = []
    balance = 10000.0
    
    # INFINITY MODE SETTINGS
    SL_PCT = 0.020 # 2.0% Initial Risk
    THRESHOLD = CONFIG["MODEL_CONF_THRESHOLD"]
    MAX_HOLD = CONFIG["MAX_TRADE_DURATION_HOURS"]
    
    TRAIL_TRIGGER = 0.015 # Start trailing after 1.5% profit
    TRAIL_DIST = 0.005 # Trail 0.5% behind high water mark
    
    wins = 0
    losses = 0
    
    for i in range(len(full_df)):
        row = full_df.iloc[i]
        price = row['close']
        ts = row['timestamp']
        high = row['high']
        low = row['low']
        
        # 1. Manage Positions (Trailing Logic)
        remaining_pos = []
        for p in positions:
            p['duration'] += 1
            exit_type = None
            pnl = 0
            
            # Update High Water Mark (HWM)
            if p['type'] == 'LONG':
                if high > p['hwm']: p['hwm'] = high
                
                # Check Trailing Activation
                gain = (p['hwm'] - p['entry']) / p['entry']
                if gain >= TRAIL_TRIGGER:
                    # Trailing Stop Price
                    new_sl = p['hwm'] * (1 - TRAIL_DIST)
                    if new_sl > p['sl']: p['sl'] = new_sl
            else:
                if low < p['hwm']: p['hwm'] = low
                
                # Check Trailing Activation
                gain = (p['entry'] - p['hwm']) / p['entry']
                if gain >= TRAIL_TRIGGER:
                    # Trailing Stop Price
                    new_sl = p['hwm'] * (1 + TRAIL_DIST)
                    if new_sl < p['sl']: p['sl'] = new_sl # Short SL moves down
            
            # Check Stop Loss (This now acts as Trailing Stop too)
            if p['type'] == 'LONG':
                if low <= p['sl']:
                    exit_type = 'SL' # Could be Profitable SL (Trailing)
                    pnl = (p['sl'] - p['entry']) / p['entry']
            else:
                if high >= p['sl']:
                    exit_type = 'SL'
                    pnl = (p['entry'] - p['sl']) / p['entry']
            
            # Time Exit
            if not exit_type and p['duration'] * 5 / 60 >= MAX_HOLD:
                exit_type = 'EXPIRED'
                if p['type'] == 'LONG': pnl = (price - p['entry']) / p['entry']
                else: pnl = (p['entry'] - price) / p['entry']
                
            if exit_type:
                amount = p['size_usd']
                profit_usd = amount * pnl
                balance += profit_usd
                
                history.append({
                    'entry_time': p['time'],
                    'exit_time': ts,
                    'type': p['type'],
                    'pnl_pct': pnl,
                    'pnl_usd': profit_usd,
                    'reason': 'TRAIL_SL' if exit_type == 'SL' and pnl > 0 else exit_type
                })
                
                if pnl > 0: wins += 1
                else: losses += 1
            else:
                remaining_pos.append(p)
                
        positions = remaining_pos
        
        # 2. Open New?
        if len(positions) >= CONFIG["MAX_CONCURRENT_POSITIONS"]:
            continue
            
        prob_long = probas[i][1]
        prob_short = probas[i][2]
        
        current_threshold = THRESHOLD
        atr_ratio = row.get('atr_ratio', 0)
        hurst = row.get('hurst', 0.5)
        rsi = row.get('rsi_14', 50)
        if atr_ratio > 0.01: current_threshold += 0.05
        
        signal = None
        if prob_long >= current_threshold:
            if not (rsi < 30 and hurst > 0.5): signal = 'LONG'
        elif prob_short >= current_threshold:
            if not (rsi > 70 and hurst > 0.5): signal = 'SHORT'
                
        if signal:
            trade_size = balance * 0.25 # 25% Pro Sizing
            entry = price
            # Initial SL only
            sl = entry * (1 - SL_PCT) if signal == 'LONG' else entry * (1 + SL_PCT)
            
            positions.append({
                'type': signal,
                'entry': entry,
                'sl': sl,
                'hwm': entry, # High Water Mark
                'size_usd': trade_size,
                'time': ts,
                'duration': 0
            })
            
    # Report
    history_df = pd.DataFrame(history)
    print("\n" + "="*60)
    print("🏆 INFINITY MODE RESULTS (Jan 2026)")
    print("="*60)
    
    if len(history_df) > 0:
        total_pnl = history_df['pnl_usd'].sum()
        final_balance = balance
        roi = ((final_balance - 10000) / 10000) * 100
        wr = (wins / (wins + losses)) * 100
        
        print(f"Final Balance: ${final_balance:,.2f}")
        print(f"Total Return:   {roi:+.2f}%")
        print(f"Total Trades:   {len(history_df)}")
        print(f"Win Rate:       {wr:.2f}%")
        print(f"Avg PnL:        ${history_df['pnl_usd'].mean():.2f}")
        
        print("\nBreakdown by Type:")
        print(history_df['reason'].value_counts())
    else:
        print("No trades executed.")

if __name__ == "__main__":
    run_verification()
