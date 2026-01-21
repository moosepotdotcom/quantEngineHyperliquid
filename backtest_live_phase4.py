#!/usr/bin/env python3
"""
Integrated Phase4 Live Signal Backtest
Combines whale events, orderbook imbalance, and funding extremes into a composite signal
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re
import sys

def load_5m_candles(csv_path='data/btc_5m_jan16_2026.csv'):
    """Load 5m candle data from Hyperliquid format."""
    df = pd.read_csv(csv_path)
    # timestamp is in ms epoch
    df['dt'] = pd.to_datetime(df['timestamp'], unit='ms') if 'timestamp' in df.columns else pd.to_datetime(df.iloc[:, 0], unit='ms')
    df = df.sort_values('dt').reset_index(drop=True)
    return df[['dt', 'open', 'high', 'low', 'close', 'volume']].copy()

def load_phase4_features(csv_path='data/phase4_features_jan16.csv'):
    """Load Phase4 imbalance, funding, and liquidation features."""
    df = pd.read_csv(csv_path)
    df['dt'] = pd.to_datetime(df['timestamp'])
    return df[['dt', 'ob_imbalance', 'funding_pct', 'liq_pressure']].copy()

def parse_whale_log(log_file='live_system.log'):
    """Parse whale events from live_system.log and create DataFrame."""
    events = []
    try:
        with open(log_file, 'r') as f:
            for line in f:
                if 'WHALE' in line:
                    # Parse: 2026-01-16 01:42:17,751 - INFO - 🐋 WHALE B: $59,847 @ 95518.0
                    match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),(\d+).*WHALE (\w): \$([0-9,]+)', line)
                    if match:
                        dt_str, ms, direction, usd_str = match.groups()
                        dt = pd.to_datetime(dt_str) + timedelta(milliseconds=int(ms))
                        side = 'BUY' if direction == 'A' else 'SELL' if direction == 'B' else 'NEUTRAL'
                        usd = float(usd_str.replace(',', ''))
                        events.append({'dt': dt, 'side': side, 'usd': usd})
    except FileNotFoundError:
        print(f"Warning: {log_file} not found")
        return pd.DataFrame()
    
    if events:
        df = pd.DataFrame(events)
        return df.sort_values('dt').reset_index(drop=True)
    return pd.DataFrame()

def calculate_atr(candles_df, period=14):
    """Calculate Average True Range."""
    high = candles_df['high']
    low = candles_df['low']
    close = candles_df['close']
    
    tr = pd.concat([
        (high - low).abs(),
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    
    candles_df['atr'] = tr.rolling(period, min_periods=1).mean()
    return candles_df

def merge_whale_events_to_candles(candles_df, whales_df):
    """Aggregate whale events into 5m candles and compute direction bias."""
    candles_df['whale_count'] = 0
    candles_df['whale_usd'] = 0.0
    candles_df['whale_bias'] = 0  # 1=BUY dominant, -1=SELL dominant
    
    if whales_df.empty:
        return candles_df
    
    for idx, row in candles_df.iterrows():
        candle_start = row['dt']
        candle_end = candle_start + timedelta(minutes=5)
        
        # Find all whale events in this candle's time window
        mask = (whales_df['dt'] >= candle_start) & (whales_df['dt'] < candle_end)
        whales_in_window = whales_df[mask]
        
        if not whales_in_window.empty:
            candles_df.at[idx, 'whale_count'] = len(whales_in_window)
            candles_df.at[idx, 'whale_usd'] = whales_in_window['usd'].sum()
            
            buy_count = (whales_in_window['side'] == 'BUY').sum()
            sell_count = (whales_in_window['side'] == 'SELL').sum()
            
            if buy_count > sell_count:
                candles_df.at[idx, 'whale_bias'] = 1
            elif sell_count > buy_count:
                candles_df.at[idx, 'whale_bias'] = -1
    
    return candles_df

def merge_phase4_features(candles_df, phase4_df):
    """Merge Phase4 features to candles by nearest timestamp."""
    candles_df['imbalance'] = 0.0
    candles_df['funding'] = 0.0
    candles_df['liq_pressure'] = 0.0
    
    if phase4_df.empty:
        return candles_df
    
    for idx, row in candles_df.iterrows():
        # Find nearest Phase4 record
        if not phase4_df.empty:
            nearest_idx = (phase4_df['dt'] - row['dt']).abs().idxmin()
            p4_row = phase4_df.iloc[nearest_idx]
            candles_df.at[idx, 'imbalance'] = p4_row['ob_imbalance']
            candles_df.at[idx, 'funding'] = p4_row['funding_pct']
            candles_df.at[idx, 'liq_pressure'] = p4_row['liq_pressure']
    
    return candles_df

def generate_composite_signal(candles_df):
    """Generate composite Phase4 signal from whale + imbalance + funding."""
    candles_df['signal'] = 0.0
    candles_df['confidence'] = 0.0
    
    for idx in range(len(candles_df)):
        row = candles_df.iloc[idx]
        
        # Whale component: requires count AND directional consensus
        whale_component = 0.0
        if row['whale_count'] >= 4:
            whale_usd_ratio = min(1.0, row['whale_usd'] / 400000.0)  # Normalize to ~$400k
            whale_component = row['whale_bias'] * whale_usd_ratio * 0.6
        
        # Imbalance component: strong orderbook imbalance
        imbalance_component = 0.0
        if abs(row['imbalance']) > 0.015:
            imbalance_ratio = min(1.0, abs(row['imbalance']) / 0.08)
            imbalance_component = np.sign(row['imbalance']) * imbalance_ratio * 0.25
        
        # Funding component: extreme funding rates predict reversals
        funding_component = 0.0
        if abs(row['funding']) > 0.02:
            funding_ratio = min(1.0, abs(row['funding']) / 0.08)
            funding_component = -np.sign(row['funding']) * funding_ratio * 0.15  # Contrarian: high funding = reversal down
        
        # Composite score
        composite_score = whale_component + imbalance_component + funding_component
        
        # Generate signal: need >0.25 confidence to trade
        if abs(composite_score) > 0.25:
            candles_df.at[idx, 'signal'] = np.sign(composite_score)
            candles_df.at[idx, 'confidence'] = abs(composite_score)
    
    return candles_df

def run_backtest(candles_df, initial_balance=10000, risk_per_trade=0.02):
    """Execute backtest using composite signals."""
    trades = []
    balance = initial_balance
    position = None
    
    for idx in range(len(candles_df)):
        row = candles_df.iloc[idx]
        current_price = row['close']
        
        # Entry: strong signal + no existing position
        if position is None and row['signal'] != 0 and row['confidence'] > 0.35:
            atr_val = row['atr'] if row['atr'] > 0 else (row['high'] - row['low'])
            side = 'LONG' if row['signal'] == 1 else 'SHORT'
            
            position = {
                'entry_idx': idx,
                'entry_price': current_price,
                'entry_time': row['dt'],
                'side': side,
                'atr': atr_val,
                'size': (balance * risk_per_trade) / current_price
            }
            
            # TP at 2x ATR, SL at 1.5x ATR
            if side == 'LONG':
                position['tp'] = current_price + (atr_val * 2)
                position['sl'] = current_price - (atr_val * 1.5)
            else:
                position['tp'] = current_price - (atr_val * 2)
                position['sl'] = current_price + (atr_val * 1.5)
        
        # Exit: TP/SL or timeout (5 candles)
        elif position is not None:
            should_exit = False
            exit_price = current_price
            exit_reason = None
            
            if position['side'] == 'LONG':
                if row['high'] >= position['tp']:
                    exit_price = position['tp']
                    should_exit = True
                    exit_reason = 'TP'
                elif row['low'] <= position['sl']:
                    exit_price = position['sl']
                    should_exit = True
                    exit_reason = 'SL'
            else:  # SHORT
                if row['low'] <= position['tp']:
                    exit_price = position['tp']
                    should_exit = True
                    exit_reason = 'TP'
                elif row['high'] >= position['sl']:
                    exit_price = position['sl']
                    should_exit = True
                    exit_reason = 'SL'
            
            # Timeout: exit after 5 candles
            if not should_exit and (idx - position['entry_idx']) >= 5:
                exit_price = current_price
                should_exit = True
                exit_reason = 'TIMEOUT'
            
            if should_exit:
                if position['side'] == 'LONG':
                    pnl = (exit_price - position['entry_price']) * position['size']
                else:
                    pnl = (position['entry_price'] - exit_price) * position['size']
                
                balance += pnl
                
                trades.append({
                    'entry_price': position['entry_price'],
                    'exit_price': exit_price,
                    'side': position['side'],
                    'pnl': pnl,
                    'size': position['size'],
                    'reason': exit_reason,
                    'entry_time': position['entry_time'],
                    'duration': idx - position['entry_idx']
                })
                
                position = None
    
    return trades, balance

def main():
    print("=" * 60)
    print("PHASE4 INTEGRATED LIVE SIGNAL BACKTEST")
    print("=" * 60)
    
    # Load all data sources
    print("\n1. Loading data...")
    candles_df = load_5m_candles()
    phase4_df = load_phase4_features()
    whales_df = parse_whale_log()
    
    print(f"   - Candles: {len(candles_df)}")
    print(f"   - Phase4 features: {len(phase4_df)}")
    print(f"   - Whale events: {len(whales_df)}")
    
    # Calculate ATR
    print("\n2. Calculating ATR...")
    candles_df = calculate_atr(candles_df, period=14)
    
    # Merge whale events
    print("\n3. Merging whale events to candles...")
    candles_df = merge_whale_events_to_candles(candles_df, whales_df)
    print(f"   - Candles with whales: {(candles_df['whale_count'] > 0).sum()}")
    
    # Merge Phase4 features
    print("\n4. Merging Phase4 features...")
    candles_df = merge_phase4_features(candles_df, phase4_df)
    
    # Generate composite signal
    print("\n5. Generating composite Phase4 signals...")
    candles_df = generate_composite_signal(candles_df)
    signal_distribution = candles_df['signal'].value_counts()
    print(f"   - BUY signals:  {signal_distribution.get(1.0, 0)}")
    print(f"   - SELL signals: {signal_distribution.get(-1.0, 0)}")
    print(f"   - NEUTRAL:      {signal_distribution.get(0.0, 0)}")
    
    # Run backtest
    print("\n6. Running backtest...")
    trades, final_balance = run_backtest(candles_df, initial_balance=10000, risk_per_trade=0.02)
    
    # Report results
    print("\n" + "=" * 60)
    print("BACKTEST RESULTS")
    print("=" * 60)
    print(f"Total Trades:        {len(trades)}")
    total_pnl = sum(t['pnl'] for t in trades)
    wins = sum(1 for t in trades if t['pnl'] > 0)
    losses = sum(1 for t in trades if t['pnl'] < 0)
    print(f"Wins / Losses:       {wins} / {losses}")
    print(f"Win Rate:            {(wins / len(trades) * 100):.1f}%" if trades else "N/A")
    print(f"Total PnL:           ${total_pnl:.2f}")
    print(f"Final Balance:       ${final_balance:.2f}")
    print(f"Return:              {((final_balance - 10000) / 10000 * 100):.2f}%")
    
    if trades:
        avg_pnl = total_pnl / len(trades)
        print(f"Avg PnL per Trade:   ${avg_pnl:.2f}")
        
        print("\nFirst 15 Trades:")
        print(f"{'#':<3} {'Side':<6} {'Entry':<9} {'Exit':<9} {'PnL':<9} {'Reason':<10}")
        print("-" * 50)
        for i, t in enumerate(trades[:15], 1):
            print(f"{i:<3} {t['side']:<6} ${t['entry_price']:<8.1f} ${t['exit_price']:<8.1f} ${t['pnl']:<8.2f} {t['reason']:<10}")

if __name__ == '__main__':
    main()
