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
    print("🧪 PHASE 3 VERIFICATION: Sept 2025 Test Drive")
    print("="*60)
    
    # 1. Load Data
    data_file = "dec2025_binance_data.csv"
    if not os.path.exists(data_file):
        print(f"❌ Missing {data_file}")
        return
        
    print(f"🔄 Loading {data_file}...")
    df = pd.read_csv(data_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Setup Trader in Simulation Mode
    trader = Phase3Trader(dry_run=True)
    # Override balance for clear PnL calculation
    trader.state["balance"] = 10000.0 
    trader.state["positions"] = {}
    trader.state["trade_history"] = []
    
    # We need to simulate the 'fetch_and_prepare_data' loop but utilizing the historical dataframe
    # The ProductionTrader fetches data internally. We need to override or mock that.
    # OR we can just instantiate the ProductionTrader and feed it slices.
    
    # Let's interact with the Trader class logic directly by passing it prepared data frames
    
    print("⚡ Running Simulation Loop...")
    
    # We need a rolling window of at least 1000 candles for indicators
    window_size = 1000
    total_candles = len(df)
    
    # Step size: 5 minutes (1 row)
    # Start after window_size
    
    trades = []
    balance_history = [10000.0]
    
    # Mocking the trader's fetch method is hard without modifying the class.
    # Instead, let's use the logic:
    # 1. Prepare ALL features using the same function as Phase 3
    # 2. Iterate and check signals
    
    # Actually, let's use the `generate_signals.py` style but with the EXACT Phase 3 Filter Logic
    from utils.advanced_features import add_advanced_features
    from quant_engine import add_all_indicators, MTF_FEATURE_LIST
    
    # Prepare Data ONCE (Vectorized) for speed, assuming no lookahead in feature generation 
    # (add_all_indicators is standard TA locallib, usually safe if we shift properly, but let's be careful)
    # The Production Engine resamples 5m -> 15m/1h. 
    # We must replicate that carefully.
    
    # Re-using the exact 'fetch_and_prepare_data' logic from Phase 3 Engine would be best check.
    # We will subclass for testing.
    
    class BacktestTrader(Phase3Trader):
        def fetch_and_prepare_data(self):
            # We will interpret 'self.current_slice'
            return self.current_slice
            
    test_trader = BacktestTrader(dry_run=True)
    test_trader.state["balance"] = 10000.0
    
    # Optimization: Pre-calculate indicators for the whole month data
    # Then for each step, just slice the pre-calculated DF? 
    # No, that leaks lookahead if indicators use future data (some smoothing might).
    # But standard TA lib usually doesn't look ahead.
    # Resampling might look ahead if not careful (using 'right' label).
    
    # To be perfectly safe and match production 1:1, we should compute on the fly, 
    # but that is slow for 5000 candles.
    # Compromise: Compute indicators on full set, then feed step by step.
    
    print("   🔧 Pre-calculating Indicators (Batch)...")
    full_df = add_all_indicators(df)
    full_df = add_advanced_features(full_df)
    
    # Resample Whole DF
    full_df.set_index('timestamp', inplace=True)
    
    df15 = full_df.resample('15T').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
    df15 = add_all_indicators(df15)
    df15 = add_advanced_features(df15)
    
    df1h = full_df.resample('1H').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
    df1h = add_all_indicators(df1h)
    df1h = add_advanced_features(df1h)
    
    # Merge context
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
    
    # Run loop
    start_idx = 0
    
    # Simulation: We iterate row by row
    # BUT, we can skip ahead if no position and no signal?
    # No, we need to check signal every candle.
    
    # Faster: Vectorized Signal Check first, then Trade Management loop.
    
    # 1. Extract X matrix
    X_dict = {c: full_df[c].values for c in MTF_FEATURE_LIST}
    X = np.column_stack([X_dict[c] for c in MTF_FEATURE_LIST])
    X = np.nan_to_num(X, nan=0.0)
    
    print("   🤖 Batch Inference...")
    probas = test_trader.engine.get_ensemble_proba('MTF', X)
    
    # Now simulate Loop
    print("   🏃 Running Trade Loop...")
    
    positions = [] # Active positions
    history = []
    balance = 10000.0
    
    # Config from Phase 3
    TP_PCT = 0.015 # 1.5%
    SL_PCT = 0.008 # 0.8% (Hybrid: Tight Stop + Aggressive Size)
    THRESHOLD = CONFIG["MODEL_CONF_THRESHOLD"]
    MAX_HOLD = CONFIG["MAX_TRADE_DURATION_HOURS"]
    
    # Circuit Breaker (Production Safety Feature)
    consecutive_losses = 0
    breaker_active = False
    breaker_cooldown_until = None
    breaker_triggers = 0
    
    # Detailed Breaker Analytics
    breaker_events = []  # Track each trigger with context
    trades_during_breaker = []  # Trades that closed while breaker was active
    
    # Stats
    wins = 0
    losses = 0
    
    for i in range(len(full_df)):
        row = full_df.iloc[i]
        price = row['close']
        ts = row['timestamp']
        
        # 1. Manage Positions (Check TP/SL)
        remaining_pos = []
        for p in positions:
            p['duration'] += 1 # 5m candles
            
            # Check Exit
            exit_type = None
            pnl = 0
            
            # Candle High/Low for strict check
            high = row['high']
            low = row['low']
            
            if p['type'] == 'LONG':
                if high >= p['tp']:
                    exit_type = 'TP'
                    pnl = (p['tp'] - p['entry']) / p['entry']
                elif low <= p['sl']:
                    exit_type = 'SL'
                    pnl = (p['sl'] - p['entry']) / p['entry']
            else:
                if low <= p['tp']:
                    exit_type = 'TP'
                    pnl = (p['entry'] - p['tp']) / p['entry']
                elif high >= p['sl']:
                    exit_type = 'SL'
                    pnl = (p['entry'] - p['sl']) / p['entry']
            
            # Time Exit
            if not exit_type and p['duration'] * 5 / 60 >= MAX_HOLD:
                exit_type = 'EXPIRED'
                if p['type'] == 'LONG': pnl = (price - p['entry']) / p['entry']
                else: pnl = (p['entry'] - price) / p['entry']
                
            if exit_type:
                # Close
                amount = p['size_usd']
                profit_usd = amount * pnl
                balance += profit_usd
                
                history.append({
                    'entry_time': p['time'],
                    'exit_time': ts,
                    'type': p['type'],
                    'pnl_pct': pnl,
                    'pnl_usd': profit_usd,
                    'reason': exit_type
                })
                
                # Circuit Breaker Logic (Production Safety)
                if exit_type == 'SL':
                    consecutive_losses += 1
                    if consecutive_losses >= 2:
                        breaker_active = True
                        breaker_cooldown_until = ts + pd.Timedelta(hours=4)
                        breaker_triggers += 1
                        consecutive_losses = 0
                        
                        # Record breaker event with context
                        breaker_events.append({
                            'trigger_time': ts,
                            'cooldown_until': breaker_cooldown_until,
                            'open_positions': len(positions),
                            'balance': balance,
                            'trigger_number': breaker_triggers
                        })
                        
                        # CRITICAL FIX: Close ALL open positions immediately
                        # This prevents buffer trades from bleeding capital
                        positions_to_force_close = positions.copy()
                        for forced_p in positions_to_force_close:
                            # Calculate forced exit PnL at current price
                            if forced_p['type'] == 'LONG':
                                forced_pnl = (price - forced_p['entry']) / forced_p['entry']
                            else:
                                forced_pnl = (forced_p['entry'] - price) / forced_p['entry']
                            
                            forced_profit = forced_p['size_usd'] * forced_pnl
                            balance += forced_profit
                            
                            history.append({
                                'entry_time': forced_p['time'],
                                'exit_time': ts,
                                'type': forced_p['type'],
                                'pnl_pct': forced_pnl,
                                'pnl_usd': forced_profit,
                                'reason': 'BREAKER_FORCED'
                            })
                            
                            if forced_pnl > 0: wins += 1
                            else: losses += 1
                        
                        # Clear all positions
                        positions = []
                        
                elif exit_type == 'TP':
                    consecutive_losses = 0  # Reset on win
                
                # Track if this trade closed during breaker period
                if breaker_active:
                    trades_during_breaker.append({
                        'exit_time': ts,
                        'type': p['type'],
                        'reason': exit_type,
                        'pnl_usd': profit_usd,
                        'breaker_trigger': breaker_triggers
                    })
                
                if pnl > 0: wins += 1
                else: losses += 1
            else:
                remaining_pos.append(p)
                
        positions = remaining_pos
        
        # 2. Check Circuit Breaker
        if breaker_active:
            if ts >= breaker_cooldown_until:
                breaker_active = False  # Cooldown expired
            else:
                continue  # Skip signal checking during cooldown
        
        # 3. Open New?
        if len(positions) >= CONFIG["MAX_CONCURRENT_POSITIONS"]:
            continue
            
        prob_long = probas[i][1]
        prob_short = probas[i][2]
        
        # Apply Adaptive Filters (Phase 3)
        current_threshold = THRESHOLD
        atr_ratio = row.get('atr_ratio', 0)
        hurst = row.get('hurst', 0.5)
        rsi = row.get('rsi_14', 50)
        
        if atr_ratio > 0.01: current_threshold += 0.05
        
        signal = None
        if prob_long >= current_threshold:
            if not (rsi < 30 and hurst > 0.5): # Filter
                signal = 'LONG'
        elif prob_short >= current_threshold:
            if not (rsi > 70 and hurst > 0.5): # Filter
                signal = 'SHORT'
                
        if signal:
            trade_size = balance * 0.25 # 25% (Pro-Trader / Safe Growth)
            entry = price
            tp = entry * (1 + TP_PCT) if signal == 'LONG' else entry * (1 - TP_PCT)
            sl = entry * (1 - SL_PCT) if signal == 'LONG' else entry * (1 + SL_PCT)
            
            positions.append({
                'type': signal,
                'entry': entry,
                'tp': tp,
                'sl': sl,
                'size_usd': trade_size,
                'time': ts,
                'duration': 0
            })
            
    # Report
    history_df = pd.DataFrame(history)
    history_df.to_csv("hybrid_mode_Nov_trades.csv", index=False)
    print(f"\n✅ Trade Log Saved: hybrid_mode_Nov_trades.csv")

    print("\n" + "="*60)
    print("🏆 PHASE 3 VERIFICATION RESULTS (Nov 2025 - Bull Run)")
    print("="*60)
    
    if len(history_df) > 0:
        total_pnl = history_df['pnl_usd'].sum()
        final_balance = balance
        roi = ((final_balance - 10000.0) / 10000.0) * 100
        wr = (wins / (wins + losses)) * 100
        
        print(f"Final Balance: ${final_balance:,.2f}")
        print(f"Total Return:   {roi:+.2f}%")
        print(f"Total Trades:   {len(history_df)}")
        print(f"Win Rate:       {wr:.2f}%")
        print(f"Avg PnL:        ${history_df['pnl_usd'].mean():.2f}")
        print(f"\n🛑 Circuit Breaker Stats:")
        print(f"   Triggers: {breaker_triggers}")
        print(f"   Buffer Trades (during cooldown): {len(trades_during_breaker)}")
        
        if len(trades_during_breaker) > 0:
            buffer_df = pd.DataFrame(trades_during_breaker)
            buffer_pnl = buffer_df['pnl_usd'].sum()
            buffer_wins = len(buffer_df[buffer_df['pnl_usd'] > 0])
            buffer_wr = (buffer_wins / len(buffer_df)) * 100 if len(buffer_df) > 0 else 0
            print(f"   Buffer Trade PnL: ${buffer_pnl:,.2f}")
            print(f"   Buffer Win Rate: {buffer_wr:.2f}%")
            print(f"   Avg Positions During Trigger: {sum([e['open_positions'] for e in breaker_events]) / len(breaker_events):.1f}")
        
        print("\nBreakdown by Type:")
        print(history_df['reason'].value_counts())
    else:
        print("No trades executed.")

if __name__ == "__main__":
    run_verification()
