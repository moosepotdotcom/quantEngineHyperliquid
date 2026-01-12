
import pandas as pd
import numpy as np
import ta
import os
from tabulate import tabulate

def load_data():
    path = os.path.join(os.path.dirname(__file__), '..', 'data', 'BTC_15m.csv')
    df = pd.read_csv(path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    return df

def fuzz_mini_scalper():
    print("🦅 Fuzzing for 'Mini Scalper' Params (Target: 100-300 pts)...")
    df = load_data()
    
    # Pre-calculate Indicators
    # We test a few RSI periods to save time, mostly 14 is standard but let's try 9 and 14
    df['rsi_14'] = ta.momentum.rsi(df['close'], window=14)
    df['rsi_9'] = ta.momentum.rsi(df['close'], window=9)
    
    # Combinations
    rsi_periods = [9, 14]
    # To get more trades, we need to be less picky about "oversold".
    # Try thresholds up to 45 (Aggressive Scalping)
    entry_rsi_longs = [25, 30, 35, 40, 45, 50, 55] 
    
    # Targets in POINTS (BTC Price Delta)
    tp_points = [100, 150, 200, 300]
    sl_points = [50, 75, 100]
    
    results = []
    
    # Vectorized simulation is hard for path-dependent SL/TP (needs row iteration).
    # We will use Numba or refined loop? 
    # Or just iterating over 6000 rows x ~100 configs is fast enough in Python.
    # Let's do a semi-optimized loop.
    
    # Convert to numpy for speed
    closes = df['close'].values
    highs = df['high'].values
    lows = df['low'].values
    times = df.index
    
    rsi_dict = {
        9: df['rsi_9'].values,
        14: df['rsi_14'].values
    }
    
    total_configs = len(rsi_periods) * len(entry_rsi_longs) * len(tp_points) * len(sl_points)
    print(f"   Testing {total_configs} configurations...")
    
    config_idx = 0
    
    for rsi_period in rsi_periods:
        rsi_arr = rsi_dict[rsi_period]
        
        for entry_thresh in entry_rsi_longs:
            # Short thresh symmetric? No, iterate separately or assume symmetric for now to reduce space
            # Let's assume symmetric for simplicity of "Mini Scalper" concept first (RSI < 30 buy, RSI > 70 sell)
            short_thresh = 100 - entry_thresh
            
            for tp in tp_points:
                for sl in sl_points:
                    
                    # Run Backtest
                    trades = 0
                    wins = 0
                    total_pnl = 0
                    
                    in_position = 0 # 1 or -1
                    entry_price = 0
                    
                    # Loop bars
                    for i in range(50, len(closes)):
                        curr_close = closes[i]
                        curr_rsi = rsi_arr[i] # Signal is at close of PREVIOUS bar usually? 
                        # Or live? Backtrader logic: Calculate at close, execute next open.
                        # We'll simulate: Detect at 'i', enter at 'i' (close) or 'i+1' (open).
                        # Let's simplify: Enter at 'i' Close. Check SL/TP on 'i+1' High/Low.
                        
                        if in_position == 0:
                            if curr_rsi < entry_thresh:
                                in_position = 1
                                entry_price = curr_close
                            elif curr_rsi > short_thresh:
                                in_position = -1
                                entry_price = curr_close
                        
                        elif in_position == 1:
                            # Long Check (Check High for TP, Low for SL)
                            # Assuming High happens before Low? Unknown.
                            # Standard conservative: Check SL first? Or Assume worst case.
                            # Or check if BOTH hit -> Loss.
                            
                            # Next bar i+1 is where we hold
                            # Actually we are IN position from prev step.
                            # So at step i, we check against current High/Low
                            
                            if i < len(closes):
                                c_high = highs[i]
                                c_low = lows[i]
                                
                                # Long TP/SL
                                target = entry_price + tp
                                stop = entry_price - sl
                                
                                hit_tp = c_high >= target
                                hit_sl = c_low <= stop
                                
                                if hit_sl and hit_tp:
                                    # Both hit in same candle? Assume LOSE (SL)
                                    wins += 0
                                    total_pnl -= sl
                                    trades += 1
                                    in_position = 0
                                elif hit_sl:
                                    wins += 0
                                    total_pnl -= sl
                                    trades += 1
                                    in_position = 0
                                elif hit_tp:
                                    wins += 1
                                    total_pnl += tp
                                    trades += 1
                                    in_position = 0
                                    
                        elif in_position == -1:
                            # Short Check
                            if i < len(closes):
                                c_high = highs[i]
                                c_low = lows[i]
                                
                                target = entry_price - tp
                                stop = entry_price + sl
                                
                                hit_tp = c_low <= target
                                hit_sl = c_high >= stop
                                
                                if hit_sl and hit_tp:
                                    wins += 0
                                    total_pnl -= sl
                                    trades += 1
                                    in_position = 0
                                elif hit_sl:
                                    wins += 0
                                    total_pnl -= sl
                                    trades += 1
                                    in_position = 0
                                elif hit_tp:
                                    wins += 1
                                    total_pnl += tp
                                    trades += 1
                                    in_position = 0

                    # Filter for Frequency AND Quality
                    # Approx 6000 bars of 15m data = ~62 days.
                    # We want > 1 trade/day => Trades > 60.
                    
                    if trades > 50: # Minimum frequency to be "often"
                        win_rate = (wins / trades) * 100
                        avg_pnl = total_pnl / trades
                        daily_trades = trades / 62.0
                        
                        # We want a scalper that scalps "perfect setups" OFTEN.
                        # So we filter for decent win rate even before ML.
                        # ML will polish it.
                        
                        if avg_pnl > -20: # Slightly relaxed Pnl
                            results.append({
                                'RSI_Period': rsi_period,
                                'Entry_Thresh': entry_thresh,
                                'TP': tp,
                                'SL': sl,
                                'Win_Rate': win_rate,
                                'Details': f"{daily_trades:.1f}/day",
                                'Total_PnL': total_pnl,
                                'Trades': trades
                            })
                            
                    config_idx += 1
                    if config_idx % 1000 == 0:
                        print(f"... checked {config_idx} configs")

    # Sort and Display
    if not results:
        print("❌ No high-frequency configs found. Try broadening search space.")
        return

    df_res = pd.DataFrame(results)
    # Sort by Frequency (Trades) first, then PnL? 
    # User said "perfect setups" (Win Rate) and "often" (Trades).
    # Let's sort by a blended score or just show top frequent ones with +PnL
    df_res = df_res.sort_values(by='Win_Rate', ascending=False).head(20)
    
    print("\n🏆 TOP HIGH-FREQ MINI SCALPER CANDIDATES:")
    print(tabulate(df_res, headers='keys', tablefmt='grid', floatfmt=".2f"))
    
    # Save best
    best = df_res.iloc[0]
    print(f"\n✅ Selected Candidate: RSI {best['RSI_Period']} < {best['Entry_Thresh']} | TP: {best['TP']} | SL: {best['SL']}")
    
    # Save to JSON or just remember for next step
    import json
    with open('research/mini_scalper_config.json', 'w') as f:
        json.dump(best.to_dict(), f)

if __name__ == "__main__":
    fuzz_mini_scalper()
