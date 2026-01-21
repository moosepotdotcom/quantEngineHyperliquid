#!/usr/bin/env python3
"""
PHASE 2 ENGINE - DECEMBER 2025 BACKTEST
Testing on different time period to validate strategy
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

def run_dec_backtest():
    print("=" * 80)
    print("🎯 PHASE 2 ENGINE - DECEMBER 2025 BACKTEST")
    print("=" * 80)
    print("Testing Period: Dec 1-31, 2025")
    print("Config: 12 positions | 12h max | Compounding")
    print("=" * 80)
    
    engine = TradingEngine()
    breaker = CustomCircuitBreaker(max_losses=2, window_minutes=60, cooldown_hours=4)
    
    INITIAL_BALANCE = 100000.0
    MAX_CONCURRENT = 12
    MAX_DURATION_HOURS = 12
    
    balance = INITIAL_BALANCE
    
    print("\n📊 Fetching December 2025 data...")
    
    limit = 10000  # More data to cover full December
    df5 = engine.fetch_data('5m', limit)
    df15 = engine.fetch_data('15m', limit)
    df1h = engine.fetch_data('1h', limit)
    
    if df5 is None or len(df5) == 0:
        print("❌ Failed to fetch data")
        return
    
    print(f"✅ Fetched {len(df5)} candles")
    
    df5 = add_all_indicators(df5)
    df15 = add_all_indicators(df15)
    df1h = add_all_indicators(df1h)
    
    df5.set_index('timestamp', inplace=True)
    df15.set_index('timestamp', inplace=True)
    df1h.set_index('timestamp', inplace=True)
    
    # Merge
    exclude = ['open', 'high', 'low', 'close', 'volume']
    ctx15 = [c for c in df15.columns if c not in exclude]
    df15_renamed = df15[ctx15].copy().rename(columns={c: f"{c}_15m" for c in ctx15})
    df_merged = pd.concat([df5, df15_renamed.reindex(df5.index, method='ffill')], axis=1)
    
    ctx1h = [c for c in df1h.columns if c not in exclude]
    df1h_renamed = df1h[ctx1h].copy().rename(columns={c: f"{c}_1h" for c in ctx1h})
    df_merged = pd.concat([df_merged, df1h_renamed.reindex(df5.index, method='ffill')], axis=1)
    
    df_merged.dropna(inplace=True)
    
    # Filter to December 2025
    start_date = "2025-12-01 00:00:00"
    end_date = "2025-12-31 23:59:59"
    mask = (df_merged.index >= start_date) & (df_merged.index <= end_date)
    sim_data = df_merged[mask]
    
    print(f"📅 December 2025: {len(sim_data)} candles")
    print(f"🔄 Running backtest...\n")
    
    open_positions = []
    closed_trades = []
    position_counter = 0
    
    for i, (timestamp, row) in enumerate(sim_data.iterrows()):
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
                
                if len(closed_trades) % 20 == 0:  # Print every 20 trades
                    print(f"{emoji} #{pos.id}: {pos.exit_reason} | Balance: ${balance:,.0f} | WR: {wr:.1f}% | Trades: {len(closed_trades)}")
                
                if pos.exit_reason == "SL":
                    if breaker.record_loss(timestamp):
                        print(f"   🛑 BREAKER until {breaker.cooldown_until}")
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
    print("📊 DECEMBER 2025 BACKTEST RESULTS")
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
    
    monthly_roi = roi  # Full month
    print(f"\n🎯 December 2025 Performance: {roi:+.2f}%")
    print(f"Compare to Jan 2-17 (16 days): +52.00%")
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
        trades_df.to_csv('dec2025_backtest_results.csv', index=False)
        print(f"\n💾 Results saved to: dec2025_backtest_results.csv")

if __name__ == "__main__":
    run_dec_backtest()
