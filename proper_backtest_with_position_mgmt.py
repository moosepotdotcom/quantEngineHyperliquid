#!/usr/bin/env python3
"""
PROPER Backtest with Position Management
- Only ONE position at a time
- Waits for TP/SL before next trade
- Realistic simulation
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests

sys.path.insert(0, '/Users/alifiyaa/Downloads/quantEngineHyperliquid/EXPORT')
from quant_engine import TradingEngine

def fetch_data(start_date='2026-01-02', end_date='2026-01-11', interval='5m'):
    """Fetch historical data"""
    print(f"\n📡 Fetching {interval} data...")
    print(f"   Range: {start_date} to {end_date}")
    
    url = 'https://api.hyperliquid.xyz/info'
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
    
    start_time = int(start_dt.timestamp() * 1000)
    end_time = int(end_dt.timestamp() * 1000)
    
    payload = {
        'type': 'candleSnapshot',
        'req': {
            'coin': 'BTC',
            'interval': interval,
            'startTime': start_time,
            'endTime': end_time
        }
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=30)
        data = resp.json()
        
        df_data = []
        for candle in data:
            df_data.append([
                candle['t'],
                float(candle['o']),
                float(candle['h']),
                float(candle['l']),
                float(candle['c']),
                float(candle['v'])
            ])
        
        df = pd.DataFrame(df_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        print(f"✅ Fetched {len(df)} candles")
        return df
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def simulate_with_position_management(df, capital=53, leverage=27):
    """
    Proper backtest with ONE position at a time
    """
    print("\n" + "="*70)
    print("🎯 PROPER BACKTEST - WITH POSITION MANAGEMENT")
    print("="*70)
    print(f"Capital: ${capital}")
    print(f"Leverage: {leverage}x")
    print(f"TP: 1.5% | SL: 0.8%")
    print("Rule: ONLY ONE POSITION AT A TIME")
    print("="*70)
    
    # Calculate position size
    buying_power = capital * leverage
    
    trades = []
    current_position = None  # Track if we have an open position
    balance = capital
    
    print(f"\n🔄 Simulating {len(df)} candles...")
    print(f"   Checking every 12 candles (1 hour)")
    
    for i in range(100, len(df), 12):  # Check every hour
        current_time = df.iloc[i]['timestamp']
        current_price = df.iloc[i]['close']
        
        # --- CHECK IF WE HAVE AN OPEN POSITION ---
        if current_position is not None:
            # We have an open position - check if TP/SL hit
            entry_price = current_position['entry']
            tp_price = current_position['tp']
            sl_price = current_position['sl']
            direction = current_position['direction']
            
            # Check subsequent candles for TP/SL
            for j in range(i, min(i+288, len(df))):  # Check next 24 hours max
                candle_high = df.iloc[j]['high']
                candle_low = df.iloc[j]['low']
                exit_time = df.iloc[j]['timestamp']
                
                if direction == 'LONG':
                    if candle_high >= tp_price:
                        # TP HIT!
                        pnl = (tp_price - entry_price) / entry_price * buying_power
                        balance += pnl
                        
                        trades.append({
                            'entry_time': current_position['time'],
                            'exit_time': exit_time,
                            'direction': direction,
                            'entry': entry_price,
                            'exit': tp_price,
                            'outcome': 'WIN',
                            'pnl': pnl,
                            'balance': balance
                        })
                        
                        print(f"✅ WIN: {current_position['time'].strftime('%m-%d %H:%M')} → "
                              f"{exit_time.strftime('%m-%d %H:%M')} | "
                              f"${entry_price:,.0f} → ${tp_price:,.0f} | "
                              f"+${pnl:.2f}")
                        
                        current_position = None
                        break
                    
                    elif candle_low <= sl_price:
                        # SL HIT!
                        pnl = (sl_price - entry_price) / entry_price * buying_power
                        balance += pnl
                        
                        trades.append({
                            'entry_time': current_position['time'],
                            'exit_time': exit_time,
                            'direction': direction,
                            'entry': entry_price,
                            'exit': sl_price,
                            'outcome': 'LOSS',
                            'pnl': pnl,
                            'balance': balance
                        })
                        
                        print(f"❌ LOSS: {current_position['time'].strftime('%m-%d %H:%M')} → "
                              f"{exit_time.strftime('%m-%d %H:%M')} | "
                              f"${entry_price:,.0f} → ${sl_price:,.0f} | "
                              f"${pnl:.2f}")
                        
                        current_position = None
                        break
            
            # If position still open, skip signal check
            if current_position is not None:
                continue
        
        # --- NO POSITION - CHECK FOR SIGNALS ---
        # For simplicity, we'll use a basic signal check
        # In reality, this would call the full engine
        
        # Simplified: Check if price is in uptrend (for demo)
        if i >= 120:
            sma_20 = df.iloc[i-20:i]['close'].mean()
            
            if current_price > sma_20:
                # LONG signal (simplified)
                position_size = buying_power / current_price
                
                # Calculate TP/SL
                tp_price = current_price * 1.015  # 1.5%
                sl_price = current_price * 0.992  # 0.8%
                
                current_position = {
                    'time': current_time,
                    'entry': current_price,
                    'tp': tp_price,
                    'sl': sl_price,
                    'direction': 'LONG',
                    'size': position_size
                }
                
                print(f"\n📍 POSITION OPENED: {current_time.strftime('%m-%d %H:%M')} | "
                      f"LONG @ ${current_price:,.0f} | "
                      f"TP: ${tp_price:,.0f} | SL: ${sl_price:,.0f}")
    
    # Final results
    print("\n" + "="*70)
    print("📊 FINAL RESULTS")
    print("="*70)
    
    if len(trades) == 0:
        print("❌ No trades completed")
        return None
    
    df_trades = pd.DataFrame(trades)
    
    wins = len(df_trades[df_trades['outcome'] == 'WIN'])
    losses = len(df_trades[df_trades['outcome'] == 'LOSS'])
    total = len(df_trades)
    
    win_rate = (wins / total * 100) if total > 0 else 0
    total_pnl = df_trades['pnl'].sum()
    final_balance = balance
    roi = ((final_balance - capital) / capital * 100)
    
    print(f"\nTotal Trades: {total}")
    print(f"Wins: {wins}")
    print(f"Losses: {losses}")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"\nStarting Capital: ${capital:.2f}")
    print(f"Final Balance: ${final_balance:.2f}")
    print(f"Total P&L: ${total_pnl:.2f}")
    print(f"ROI: {roi:+.1f}%")
    print("="*70)
    
    return df_trades

def main():
    print("\n🚀 PROPER BACKTEST WITH POSITION MANAGEMENT")
    print("="*70)
    
    # Fetch data
    df = fetch_data()
    
    if df is None:
        return
    
    # Run simulation
    results = simulate_with_position_management(df, capital=53, leverage=27)
    
    if results is not None:
        # Save results
        results.to_csv('PROPER_BACKTEST_RESULTS.csv', index=False)
        print(f"\n💾 Results saved to: PROPER_BACKTEST_RESULTS.csv")

if __name__ == '__main__':
    main()
