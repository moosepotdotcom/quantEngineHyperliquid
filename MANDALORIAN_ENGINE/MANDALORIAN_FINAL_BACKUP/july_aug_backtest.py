#!/usr/bin/env python3
"""
JULY/AUGUST 2025 BACKTEST - FIXED MTF MERGE
Based on validated methodology.
Data source: Binance (July 1 - Sept 1, 2025)
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

def run_backtest(month_name, csv_path):
    print("=" * 80)
    print(f"🎯 {month_name} BACKTEST (Binance Data)")
    print("=" * 80)
    
    engine = TradingEngine()
    breaker = CustomCircuitBreaker(max_losses=2, window_minutes=60, cooldown_hours=4)
    
    INITIAL_BALANCE = 100000.0
    MAX_CONCURRENT = 12
    MAX_DURATION_HOURS = 12
    
    balance = INITIAL_BALANCE
    
    print(f"\n📊 Loading {month_name} data...")
    
    # Load 5m data
    df5_raw = pd.read_csv(csv_path)
    df5_raw['timestamp'] = pd.to_datetime(df5_raw['timestamp'])
    df5_raw.set_index('timestamp', inplace=True)
    
    print(f"✅ Loaded {len(df5_raw)} 5-minute candles")
    
    # Resample to 15m and 1h
    print("🔧 Resampling to 15m and 1h...")
    df15_raw = df5_raw.resample('15T').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
    
    df1h_raw = df5_raw.resample('1H').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
    
    # Add indicators
    print("🔧 Adding indicators to each timeframe...")
    df5_raw.reset_index(inplace=True)
    df15_raw.reset_index(inplace=True)
    df1h_raw.reset_index(inplace=True)
    
    df5 = add_all_indicators(df5_raw)
    df15 = add_all_indicators(df15_raw)
    df1h = add_all_indicators(df1h_raw)
    
    df5.set_index('timestamp', inplace=True)
    df15.set_index('timestamp', inplace=True)
    df1h.set_index('timestamp', inplace=True)
    
    # Merge MTF
    print("🔧 Merging MTF features...")
    exclude = ['open', 'high', 'low', 'close', 'volume']
    
    ctx15 = [c for c in df15.columns if c not in exclude]
    df15_renamed = df15[ctx15].copy().rename(columns={c: f"{c}_15m" for c in ctx15})
    df_merged = pd.concat([df5, df15_renamed.reindex(df5.index, method='ffill')], axis=1)
    
    ctx1h = [c for c in df1h.columns if c not in exclude]
    df1h_renamed = df1h[ctx1h].copy().rename(columns={c: f"{c}_1h" for c in ctx1h})
    df_merged = pd.concat([df_merged, df1h_renamed.reindex(df5.index, method='ffill')], axis=1)
    
    df_merged.dropna(inplace=True)
    
    print(f"✅ Final dataset: {len(df_merged)} candles")
    print(f"🔄 Running backtest...\n")
    
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
                
                if pos.exit_reason == "SL":
                    breaker.record_loss(timestamp)
                else:
                    breaker.reset()
            else:
                still_open.append(pos)
        open_positions = still_open
        
        # Check new signals
        if len(open_positions) < MAX_CONCURRENT:
            if breaker.cooldown_until and timestamp < breaker.cooldown_until:
                continue
            
            X_dict = {c: row.get(c, 0.0) for c in MTF_FEATURE_LIST}
            X = np.array([X_dict[c] for c in MTF_FEATURE_LIST]).reshape(1, -1)
            X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
            
            probas = engine.get_ensemble_proba('MTF', X)[0]
            prob_long, prob_short = float(probas[1]), float(probas[2])
            
            direction = None
            conf = 0.0
            
            if prob_long >= 0.45:
                direction = 'LONG'
                conf = prob_long
            elif prob_short >= 0.45:
                direction = 'SHORT'
                conf = prob_short
            
            if direction:
                hurst = row.get('hurst', 0.5)
                rsi = row.get('rsi_14', 50)
                rsi7 = row.get('rsi_7', 50)
                
                if direction == 'LONG' and rsi < 30 and hurst > 0.5:
                    continue
                if direction == 'SHORT' and rsi7 < 25:
                    continue
                
                # Compounding
                size = 0.5 * (balance / INITIAL_BALANCE)
                
                position_counter += 1
                new_pos = OpenPosition(position_counter, timestamp, direction, row['close'], conf, size)
                open_positions.append(new_pos)
    
    # Stats
    wins = [t for t in closed_trades if t.exit_reason == "TP"]
    losses = [t for t in closed_trades if t.exit_reason == "SL"]
    
    if closed_trades:
        wr = len(wins) / len(closed_trades) * 100
        roi = ((balance - INITIAL_BALANCE) / INITIAL_BALANCE) * 100
        
        print("\n" + "=" * 50)
        print(f"📊 {month_name} RESULTS")
        print(f"Trades: {len(closed_trades)} | WR: {wr:.1f}%")
        print(f"ROI: {roi:+.2f}% | Final Bal: ${balance:,.0f}")
        print("=" * 50 + "\n")
        return {"roi": roi, "wr": wr, "trades": len(closed_trades)}
    else:
        print("❌ No trades executed")
        return None

if __name__ == "__main__":
    results_july = run_backtest("JULY 2025", '/Users/alifiyaa/Downloads/quantEngineHyperliquid/MANDALORIAN_ENGINE/july2025_binance_data.csv')
    results_aug = run_backtest("AUGUST 2025", '/Users/alifiyaa/Downloads/quantEngineHyperliquid/MANDALORIAN_ENGINE/aug2025_binance_data.csv')
