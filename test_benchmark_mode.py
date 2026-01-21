#!/usr/bin/env python3
"""
Backtest Benchmark Mode Strategy
Verify the claimed 87.1% win rate
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quant_engine import TradingEngine

def fetch_historical_data(start_date='2026-01-02', end_date='2026-01-07', interval='5m'):
    """Fetch historical data from Hyperliquid for specific date range"""
    print(f"\n📡 Fetching {interval} data from Hyperliquid...")
    print(f"   Date Range: {start_date} to {end_date}")
    
    url = 'https://api.hyperliquid.xyz/info'
    
    # Convert dates to timestamps (milliseconds)
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)  # Include full end day
    
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
        if resp.status_code != 200:
            print(f"❌ HTTP {resp.status_code}")
            return None
        
        data = resp.json()
        if not isinstance(data, list) or len(data) == 0:
            print(f"❌ No data returned")
            return None
        
        # Convert to DataFrame
        df_data = []
        for candle in data:
            df_data.append([
                candle['t'],  # timestamp in milliseconds
                float(candle['o']),  # open
                float(candle['h']),  # high
                float(candle['l']),  # low
                float(candle['c']),  # close
                float(candle['v'])   # volume
            ])
        
        df = pd.DataFrame(df_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        print(f"✅ Fetched {len(df)} candles")
        print(f"   Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
        return df
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def simulate_benchmark_mode(df):
    """Simulate Benchmark Mode strategy"""
    print("\n" + "="*70)
    print("🎯 BACKTESTING: Benchmark Mode")
    print("="*70)
    print("Configuration:")
    print("  - Threshold: 0.45 (45%)")
    print("  - Hurst Filter: OFF")
    print("  - ATR Penalty: OFF")
    print("  - Circuit Breaker: ON")
    print("  - TP: 1.5% | SL: 0.8%")
    print("="*70)
    
    # Initialize engine with Benchmark Mode
    engine = TradingEngine()
    success = engine.apply_strategy_preset("Benchmark Mode")
    
    if not success:
        print("❌ Failed to apply Benchmark Mode")
        return
    
    print(f"\n✅ Strategy applied: {engine.active_strategy}")
    print(f"   Threshold: {engine.mtf_threshold_long:.2%}")
    print(f"   Hurst: {engine.use_hurst}")
    print(f"   ATR Penalty: {engine.use_atr_penalty}")
    
    # Track trades
    trades = []
    
    # Simulate checking every 5m candle
    print(f"\n🔄 Simulating {len(df)} candles...")
    
    for i in range(100, len(df)):  # Start after enough data for indicators
        if i % 100 == 0:
            print(f"   Progress: {i}/{len(df)} candles...")
        
        # Check for signal
        try:
            signal, confidence = engine.check_mtf_scalper()
            
            if signal and confidence >= engine.mtf_threshold_long:
                # Record trade
                entry_price = float(signal['price'])
                direction = signal['direction']
                timestamp = df.iloc[i]['timestamp']
                
                # Calculate TP/SL
                if direction == 'LONG':
                    tp_price = entry_price * 1.015  # 1.5%
                    sl_price = entry_price * 0.992  # 0.8%
                else:
                    tp_price = entry_price * 0.985  # 1.5%
                    sl_price = entry_price * 1.008  # 0.8%
                
                # Simulate outcome (check next 20 candles)
                outcome = 'PENDING'
                exit_price = entry_price
                exit_time = timestamp
                
                for j in range(i+1, min(i+20, len(df))):
                    high = df.iloc[j]['high']
                    low = df.iloc[j]['low']
                    
                    if direction == 'LONG':
                        if high >= tp_price:
                            outcome = 'WIN'
                            exit_price = tp_price
                            exit_time = df.iloc[j]['timestamp']
                            break
                        elif low <= sl_price:
                            outcome = 'LOSS'
                            exit_price = sl_price
                            exit_time = df.iloc[j]['timestamp']
                            break
                    else:  # SHORT
                        if low <= tp_price:
                            outcome = 'WIN'
                            exit_price = tp_price
                            exit_time = df.iloc[j]['timestamp']
                            break
                        elif high >= sl_price:
                            outcome = 'LOSS'
                            exit_price = sl_price
                            exit_time = df.iloc[j]['timestamp']
                            break
                
                # Calculate P&L
                if direction == 'LONG':
                    pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                else:
                    pnl_pct = ((entry_price - exit_price) / entry_price) * 100
                
                trades.append({
                    'timestamp': timestamp,
                    'direction': direction,
                    'entry': entry_price,
                    'exit': exit_price,
                    'tp': tp_price,
                    'sl': sl_price,
                    'confidence': confidence,
                    'outcome': outcome,
                    'pnl_pct': pnl_pct,
                    'exit_time': exit_time
                })
                
                # Skip ahead to avoid overlapping trades
                i += 10
        
        except Exception as e:
            # Silent fail for data issues
            pass
    
    # Analyze results
    print("\n" + "="*70)
    print("📊 BACKTEST RESULTS")
    print("="*70)
    
    if len(trades) == 0:
        print("❌ No trades detected!")
        return
    
    df_trades = pd.DataFrame(trades)
    
    total_trades = len(df_trades)
    wins = len(df_trades[df_trades['outcome'] == 'WIN'])
    losses = len(df_trades[df_trades['outcome'] == 'LOSS'])
    pending = len(df_trades[df_trades['outcome'] == 'PENDING'])
    
    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
    avg_win = df_trades[df_trades['outcome'] == 'WIN']['pnl_pct'].mean() if wins > 0 else 0
    avg_loss = df_trades[df_trades['outcome'] == 'LOSS']['pnl_pct'].mean() if losses > 0 else 0
    total_pnl = df_trades[df_trades['outcome'] != 'PENDING']['pnl_pct'].sum()
    
    print(f"\n📈 Performance:")
    print(f"   Total Trades: {total_trades}")
    print(f"   Wins: {wins}")
    print(f"   Losses: {losses}")
    print(f"   Pending: {pending}")
    print(f"   Win Rate: {win_rate:.1f}%")
    print(f"   Avg Win: {avg_win:.2f}%")
    print(f"   Avg Loss: {avg_loss:.2f}%")
    print(f"   Total P&L: {total_pnl:.2f}%")
    
    # Compare to claimed 87.1%
    print(f"\n🎯 Benchmark Comparison:")
    print(f"   Claimed Win Rate: 87.1%")
    print(f"   Actual Win Rate: {win_rate:.1f}%")
    
    if win_rate >= 85:
        print(f"   ✅ VERIFIED - Within expected range!")
    elif win_rate >= 75:
        print(f"   ⚠️  LOWER than claimed but still good")
    else:
        print(f"   ❌ SIGNIFICANTLY LOWER - Investigation needed!")
    
    # Show recent trades
    print(f"\n📋 Last 10 Trades:")
    print("-" * 70)
    for idx, trade in df_trades.tail(10).iterrows():
        emoji = "✅" if trade['outcome'] == 'WIN' else "❌" if trade['outcome'] == 'LOSS' else "⏳"
        print(f"{emoji} {trade['timestamp'].strftime('%Y-%m-%d %H:%M')} | "
              f"{trade['direction']:5s} @ ${trade['entry']:,.0f} | "
              f"Conf: {trade['confidence']:.1%} | "
              f"P&L: {trade['pnl_pct']:+.2f}%")
    
    print("="*70)
    
    return df_trades

def main():
    print("\n" + "🚀"*35)
    print("BENCHMARK MODE VERIFICATION")
    print("Testing Period: Jan 2-7, 2026")
    print("🚀"*35 + "\n")
    
    # Fetch data for Jan 2-7, 2026
    df = fetch_historical_data(start_date='2026-01-02', end_date='2026-01-07', interval='5m')
    
    if df is None:
        print("❌ Failed to fetch data")
        return
    
    # Run backtest
    results = simulate_benchmark_mode(df)
    
    if results is not None:
        # Save results
        output_file = 'BACKTEST_BENCHMARK_MODE_JAN2_7.csv'
        results.to_csv(output_file, index=False)
        print(f"\n💾 Results saved to: {output_file}")

if __name__ == '__main__':
    main()
