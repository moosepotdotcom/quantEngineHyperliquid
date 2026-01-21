#!/usr/bin/env python3
"""
DECEMBER 2025 BACKTEST - Using Yahoo Finance Data
Full month backtest with 8,928 5-minute candles
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, '/Users/alifiyaa/Downloads/quantEngineHyperliquid/MANDALORIAN_ENGINE')
from quant_engine import TradingEngine, add_all_indicators, MTF_FEATURE_LIST

class CustomCircuitBreaker:
    def __init__(self, max_losses=2, window_minutes=60, cooldown_hours=4):
        self.max_losses = max_losses
        self.window_minutes = window_minutes
        self.cooldown_hours = cooldown_hours
        self.losses = []
        self.cooldown_until = None
    
    def record_loss(self, timestamp):
        self.losses = [t for t in self.losses if (timestamp - t).total_seconds() < self.window_minutes * 60]
        self.losses.append(timestamp)
        
        if len(self.losses) >= self.max_losses:
            self.cooldown_until = timestamp + pd.Timedelta(hours=self.cooldown_hours)
            return True
        return False
    
    def reset(self):
        self.losses = []

class OpenPosition:
    def __init__(self, id, timestamp, direction, entry_price, confidence, size_btc):
        self.id = id
        self.entry_time = timestamp
        self.direction = direction
        self.entry_price = entry_price
        self.confidence = confidence
        self.size_btc = size_btc
        
        if direction == "LONG":
            self.tp_price = entry_price * 1.015
            self.sl_price = entry_price * 0.992
        else:
            self.tp_price = entry_price * 0.985
            self.sl_price = entry_price * 1.008
        
        self.exit_price = None
        self.exit_time = None
        self.exit_reason = None
        self.pnl = 0.0
    
    def check_exit(self, high, low, close, timestamp, max_duration_hours=12):
        if self.direction == "LONG":
            if high >= self.tp_price:
                self.close(self.tp_price, "TP", timestamp)
                return True
            elif low <= self.sl_price:
                self.close(self.sl_price, "SL", timestamp)
                return True
        else:
            if low <= self.tp_price:
                self.close(self.tp_price, "TP", timestamp)
                return True
            elif high >= self.sl_price:
                self.close(self.sl_price, "SL", timestamp)
                return True
        
        duration = (timestamp - self.entry_time).total_seconds() / 3600
        if duration >= max_duration_hours:
            self.close(close, "EXPIRED", timestamp)
            return True
        
        return False
    
    def close(self, exit_price, reason, timestamp):
        self.exit_price = exit_price
        self.exit_reason = reason
        self.exit_time = timestamp
        
        if self.direction == "LONG":
            price_change = exit_price - self.entry_price
        else:
            price_change = self.entry_price - exit_price
        
        self.pnl = price_change * self.size_btc

def run_dec_backtest_yfinance():
    print("=" * 80)
    print("🎯 DECEMBER 2025 BACKTEST - Yahoo Finance Data")
    print("=" * 80)
    print("Full Month: Dec 1-31, 2025")
    print("Config: 12 positions | 12h max | Compounding")
    print("=" * 80)
    
    engine = TradingEngine()
    breaker = CustomCircuitBreaker(max_losses=2, window_minutes=60, cooldown_hours=4)
    
    INITIAL_BALANCE = 100000.0
    MAX_CONCURRENT = 12
    MAX_DURATION_HOURS = 12
    
    balance = INITIAL_BALANCE
    
    print("\n📊 Loading December 2025 data from Yahoo Finance...")
    
    # Load the CSV we just downloaded
    df5 = pd.read_csv('/Users/alifiyaa/Downloads/quantEngineHyperliquid/MANDALORIAN_ENGINE/dec2025_yfinance_data.csv')
    
    # Rename columns to match our format
    df5.rename(columns={
        'Datetime': 'timestamp',
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'Volume': 'volume'
    }, inplace=True)
    
    df5['timestamp'] = pd.to_datetime(df5['timestamp'])
    
    print(f"✅ Loaded {len(df5)} 5-minute candles")
    print(f"Date range: {df5['timestamp'].min()} to {df5['timestamp'].max()}")
    
    # Add indicators
    print("🔧 Adding indicators...")
    df5 = add_all_indicators(df5)
    
    # For simplicity, use 5m data for all timeframes (since we don't have 15m/1h from yfinance)
    # In production, you'd resample or fetch separately
    df5.set_index('timestamp', inplace=True)
    
    # Create MTF features (simplified - using 5m for all)
    df_merged = df5.copy()
    
    # Add placeholder MTF columns
    for col in df5.columns:
        if col not in ['open', 'high', 'low', 'close', 'volume']:
            df_merged[f"{col}_15m"] = df5[col]
            df_merged[f"{col}_1h"] = df5[col]
    
    df_merged.dropna(inplace=True)
    
    print(f"🔄 Running backtest on {len(df_merged)} candles...\n")
    
    open_positions = []
    closed_trades = []
    position_counter = 0
    
    for i, (timestamp, row) in enumerate(df_merged.iterrows()):
        # Check exits
        still_open = []
        for pos in open_positions:
            if pos.check_exit(row['high'], row['low'], row['close'], timestamp, MAX_DURATION_HOURS):
                balance += pos.pnl
                closed_trades.append(pos)
                
                emoji = "✅" if pos.exit_reason == "TP" else "❌" if pos.exit_reason == "SL" else "⏱️"
                wins = len([t for t in closed_trades if t.exit_reason == "TP"])
                losses = len([t for t in closed_trades if t.exit_reason == "SL"])
                total = wins + losses
                wr = (wins / total * 100) if total > 0 else 0
                
                if len(closed_trades) % 50 == 0:
                    print(f"{emoji} Trade #{len(closed_trades)}: Balance: ${balance:,.0f} | WR: {wr:.1f}%")
                
                if pos.exit_reason == "SL":
                    breaker.record_loss(timestamp)
                else:
                    breaker.reset()
            else:
                still_open.append(pos)
        
        open_positions = still_open
        
        # Check for new signals
        if len(open_positions) < MAX_CONCURRENT:
            if breaker.cooldown_until and timestamp < breaker.cooldown_until:
                continue
            
            X_dict = {c: row.get(c, 0.0) for c in MTF_FEATURE_LIST}
            X = np.array([X_dict[c] for c in MTF_FEATURE_LIST]).reshape(1, -1)
            X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
            
            probas = engine.get_ensemble_proba('MTF', X)[0]
            prob_long, prob_short = float(probas[1]), float(probas[2])
            
            direction = None
            confidence = 0.0
            
            if prob_long >= 0.45:
                direction = 'LONG'
                confidence = prob_long
            elif prob_short >= 0.45:
                direction = 'SHORT'
                confidence = prob_short
            
            if direction:
                hurst = row.get('hurst', 0.5)
                rsi = row.get('rsi_14', 50)
                rsi7 = row.get('rsi_7', 50)
                
                if direction == 'LONG' and rsi < 30 and hurst > 0.5:
                    continue
                
                if direction == 'SHORT' and rsi7 < 25:
                    continue
                
                # Compounding
                position_size = 0.5 * (balance / INITIAL_BALANCE)
                
                position_counter += 1
                new_pos = OpenPosition(
                    id=position_counter,
                    timestamp=timestamp,
                    direction=direction,
                    entry_price=row['close'],
                    confidence=confidence,
                    size_btc=position_size
                )
                open_positions.append(new_pos)
    
    # Final stats
    print("\n" + "=" * 80)
    print("📊 DECEMBER 2025 BACKTEST RESULTS (Yahoo Finance Data)")
    print("=" * 80)
    
    wins = [t for t in closed_trades if t.exit_reason == "TP"]
    losses = [t for t in closed_trades if t.exit_reason == "SL"]
    expired = [t for t in closed_trades if t.exit_reason == "EXPIRED"]
    
    print(f"Total Trades: {len(closed_trades)}")
    print(f"Wins: {len(wins)} | Losses: {len(losses)} | Expired: {len(expired)}")
    
    if wins or losses:
        wr = len(wins) / (len(wins) + len(losses)) * 100
        print(f"Win Rate: {wr:.1f}%")
    
    total_pnl = sum(t.pnl for t in closed_trades)
    roi = ((balance - INITIAL_BALANCE) / INITIAL_BALANCE) * 100
    
    print(f"\nTotal P&L: ${total_pnl:+,.2f}")
    print(f"Final Balance: ${balance:,.2f}")
    print(f"ROI: {roi:+.2f}%")
    
    print(f"\n🎯 Comparison:")
    print(f"December 2025: {roi:+.2f}% (31 days)")
    print(f"January 2-17: +52.00% (16 days)")
    print(f"Jan monthly projection: +97.5%")
    
    print("=" * 80)
    
    # Save
    if closed_trades:
        trades_data = []
        for pos in closed_trades:
            trades_data.append({
                'id': pos.id,
                'entry_time': pos.entry_time,
                'exit_time': pos.exit_time,
                'direction': pos.direction,
                'entry_price': pos.entry_price,
                'exit_price': pos.exit_price,
                'exit_reason': pos.exit_reason,
                'pnl': pos.pnl,
                'size_btc': pos.size_btc
            })
        
        trades_df = pd.DataFrame(trades_data)
        trades_df.to_csv('dec2025_full_backtest_results.csv', index=False)
        print(f"\n💾 Results saved to: dec2025_full_backtest_results.csv")

if __name__ == "__main__":
    run_dec_backtest_yfinance()
