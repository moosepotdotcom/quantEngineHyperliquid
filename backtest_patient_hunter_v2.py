import pandas as pd
import numpy as np
import os
from datetime import datetime

# Configuration
SYMBOL = 'BTC'
TP_TARGET = 0.005 # 0.5%
SL_LIMIT = -0.002 # -0.2%
LIQ_PROXY_MULT = 5.0 # Volume spike multiplier for liquidation proxy
WHALE_WALL_DIST = 0.0005 # 0.05% proximity to wall

def run_backtest(symbol):
    print(f"\n📊 Backtesting Patient Hunter V2 for {symbol}...")
    file_path = f'data/{symbol}_1m_Jan18_19_2026.csv'
    if not os.path.exists(file_path):
        print(f"❌ Missing data: {file_path}")
        return
    
    df = pd.read_csv(file_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # 1. GENERATE PROXIES
    # Volume Mean for spike detection
    df['vol_sma'] = df['volume'].rolling(20).mean()
    df['vol_spike'] = df['volume'] > (df['vol_sma'] * LIQ_PROXY_MULT)
    
    # "Liquidation Pulse" Proxy
    # A true pulse involves a big move + high volume
    df['price_move'] = df['close'].pct_change().abs()
    df['is_hyped'] = df['vol_spike'] & (df['price_move'] > 0.0005)
    
    # "Persistent Wall" Proxy
    # We find local support/resistance that holds for > 5 bars (minutes)
    df['lowest_5m'] = df['low'].rolling(5).min()
    df['highest_5m'] = df['high'].rolling(5).max()
    
    # OI Velocity Proxy (Volume Momentum)
    df['vol_mom'] = df['volume'].pct_change(5)
    
    # 2. SIMULATE
    trades = []
    current_pos = None
    
    for i in range(20, len(df)):
        row = df.iloc[i]
        ts = row['timestamp']
        px = row['close']
        
        # --- POSITION MANAGEMENT ---
        if current_pos:
            # Calculate PnL
            if current_pos['side'] == 'LONG':
                pnl = (px - current_pos['entry']) / current_pos['entry']
            else:
                pnl = (current_pos['entry'] - px) / current_pos['entry']
            
            # Update Peak PnL for trailing
            if pnl > current_pos['peak_pnl']:
                current_pos['peak_pnl'] = pnl
            
            # EXIT LOGIC
            exit_reason = None
            # 1. Trailing Stop
            if current_pos['peak_pnl'] > 0.001 and (current_pos['peak_pnl'] - pnl) > 0.0015:
                exit_reason = "Trailing Stop"
            # 2. Stop Loss
            elif pnl < SL_LIMIT:
                exit_reason = "Stop Loss"
            # 3. Take Profit
            elif pnl >= TP_TARGET:
                exit_reason = "Take Profit"
            
            if exit_reason:
                trades.append({
                    'symbol': symbol,
                    'entry_ts': current_pos['entry_ts'],
                    'exit_ts': ts,
                    'side': current_pos['side'],
                    'entry_px': current_pos['entry'],
                    'exit_px': px,
                    'pnl': pnl,
                    'reason': exit_reason
                })
                current_pos = None
            continue
            
        # --- ENTRY LOGIC ---
        # 1. "Liquidation" Pulse Detected
        if row['is_hyped']:
            # 2. Check for Persistent Wall (Local Bottom/Top)
            # Long: Price near rolling 5m low
            dist_to_low = (px - row['lowest_5m']) / px
            # Short: Price near rolling 5m high
            dist_to_high = (row['highest_5m'] - px) / px
            
            # 3. Entry
            if dist_to_low < WHALE_WALL_DIST and row['vol_mom'] > 0.5: # Vol surge + support
                current_pos = {
                    'symbol': symbol,
                    'entry_ts': ts,
                    'side': 'LONG',
                    'entry': px,
                    'peak_pnl': 0
                }
            elif dist_to_high < WHALE_WALL_DIST and row['vol_mom'] > 0.5: # Vol surge + resistance
                current_pos = {
                    'symbol': symbol,
                    'entry_ts': ts,
                    'side': 'SHORT',
                    'entry': px,
                    'peak_pnl': 0
                }

    # 3. RESULTS
    if not trades:
        print(f"❌ No trades for {symbol}")
        return
    
    t_df = pd.DataFrame(trades)
    win_rate = (t_df['pnl'] > 0).mean() * 100
    total_pnl = t_df['pnl'].sum()
    
    print(f"✅ Completed {len(t_df)} trades")
    print(f"📈 Win Rate: {win_rate:.2f}%")
    print(f"💰 Total PnL: {total_pnl*100:.2f}%")
    print(t_df[['entry_ts', 'side', 'pnl', 'reason']].tail(10))
    
    return t_df

def main():
    all_trades = []
    for s in ['BTC', 'ETH', 'SOL']:
        res = run_backtest(s)
        if res is not None:
            all_trades.append(res)
            
    if all_trades:
        final_df = pd.concat(all_trades)
        print("\n" + "="*30)
        print("🌍 GLOBAL PERFORMANCE")
        print("="*30)
        print(f"Total Trades: {len(final_df)}")
        print(f"Global WR: {(final_df['pnl'] > 0).mean()*100:.2f}%")
        print(f"Net ROI: {final_df['pnl'].sum()*100:.2f}%")
        
        final_df.to_csv('Jan18_19_Backtest_Results.csv', index=False)

if __name__ == "__main__":
    main()
