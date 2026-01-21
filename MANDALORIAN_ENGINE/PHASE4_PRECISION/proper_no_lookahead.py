#!/usr/bin/env python3
"""
PROPER NO-LOOKAHEAD ENGINE
Track positions candle-by-candle until TP/SL hit
Should achieve ~81% WR like lookahead version
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
    """Circuit breaker for historical backtesting"""
    def __init__(self, max_losses=2, window_minutes=60, cooldown_hours=4):
        self.max_losses = max_losses
        self.window_minutes = window_minutes
        self.cooldown_hours = cooldown_hours
        self.losses = []
        self.cooldown_until = None
    
    def record_loss(self, timestamp):
        """Record a loss at given timestamp"""
        self.losses = [t for t in self.losses if (timestamp - t).total_seconds() < self.window_minutes * 60]
        self.losses.append(timestamp)
        
        if len(self.losses) >= self.max_losses:
            self.cooldown_until = timestamp + pd.Timedelta(hours=self.cooldown_hours)
            return True
        return False
    
    def reset(self):
        """Reset after a win"""
        self.losses = []

class OpenPosition:
    """Represents an open position"""
    def __init__(self, id, timestamp, direction, entry_price, confidence):
        self.id = id
        self.entry_time = timestamp
        self.direction = direction
        self.entry_price = entry_price
        self.confidence = confidence
        
        # Calculate TP/SL
        if direction == "LONG":
            self.tp_price = entry_price * 1.015  # +1.5%
            self.sl_price = entry_price * 0.992  # -0.8%
        else:  # SHORT
            self.tp_price = entry_price * 0.985  # -1.5%
            self.sl_price = entry_price * 1.008  # +0.8%
        
        self.exit_price = None
        self.exit_time = None
        self.exit_reason = None
    
    def check_exit(self, high, low, timestamp):
        """Check if TP or SL was hit on this candle"""
        if self.direction == "LONG":
            # Check TP first (price went up)
            if high >= self.tp_price:
                self.exit_price = self.tp_price
                self.exit_time = timestamp
                self.exit_reason = "TP"
                return True
            # Then check SL (price went down)
            elif low <= self.sl_price:
                self.exit_price = self.sl_price
                self.exit_time = timestamp
                self.exit_reason = "SL"
                return True
        else:  # SHORT
            # Check TP first (price went down)
            if low <= self.tp_price:
                self.exit_price = self.tp_price
                self.exit_time = timestamp
                self.exit_reason = "TP"
                return True
            # Then check SL (price went up)
            elif high >= self.sl_price:
                self.exit_price = self.sl_price
                self.exit_time = timestamp
                self.exit_reason = "SL"
                return True
        
        return False

def run_proper_no_lookahead():
    print("=" * 80)
    print("🎯 PROPER NO-LOOKAHEAD ENGINE")
    print("=" * 80)
    print("Track positions candle-by-candle until TP/SL hit")
    print("Should match ~81% WR from lookahead version")
    print("=" * 80)
    
    engine = TradingEngine()
    breaker = CustomCircuitBreaker(max_losses=2, window_minutes=60, cooldown_hours=4)
    
    print("\n📊 Fetching data...")
    
    limit = 4000
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
    
    # Filter to Jan 2-17
    start_date = "2026-01-02 00:00:00"
    end_date = "2026-01-17 23:59:59"
    mask = (df_merged.index >= start_date) & (df_merged.index <= end_date)
    sim_data = df_merged[mask]
    
    print(f"🔄 Simulating {len(sim_data)} candles...\n")
    
    # Tracking
    open_positions = []
    closed_trades = []
    position_counter = 0
    max_concurrent = 6  # Limit to 6 positions
    
    for i, (timestamp, row) in enumerate(sim_data.iterrows()):
        # 1. Check exits for all open positions FIRST
        still_open = []
        for pos in open_positions:
            if pos.check_exit(row['high'], row['low'], timestamp):
                # Position closed
                closed_trades.append(pos)
                
                emoji = "✅" if pos.exit_reason == "TP" else "❌"
                wins = len([t for t in closed_trades if t.exit_reason == "TP"])
                losses = len([t for t in closed_trades if t.exit_reason == "SL"])
                total = wins + losses
                wr = (wins / total * 100) if total > 0 else 0
                
                print(f"{emoji} Trade #{pos.id}: {pos.direction} @ ${pos.entry_price:,.0f} → ${pos.exit_price:,.0f} | "
                      f"{pos.exit_reason} | WR: {wr:.1f}% ({wins}W/{losses}L) | Open: {len(still_open)}/{max_concurrent}")
                
                # Update circuit breaker
                if pos.exit_reason == "SL":
                    if breaker.record_loss(timestamp):
                        print(f"   🛑 CIRCUIT BREAKER until {breaker.cooldown_until}")
                else:
                    breaker.reset()
            else:
                still_open.append(pos)
        
        open_positions = still_open
        
        # 2. Check for new signals (if room available)
        if len(open_positions) < max_concurrent:
            # Skip if circuit breaker active
            if breaker.cooldown_until and timestamp < breaker.cooldown_until:
                continue
            
            # Prepare features
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
                # Apply filters
                hurst = row.get('hurst', 0.5)
                rsi = row.get('rsi_14', 50)
                rsi7 = row.get('rsi_7', 50)
                
                # Hurst Filter
                if direction == 'LONG' and rsi < 30 and hurst > 0.5:
                    continue
                
                # AI Smart Filter
                if direction == 'SHORT' and rsi7 < 25:
                    continue
                
                # Open new position
                position_counter += 1
                new_pos = OpenPosition(
                    id=position_counter,
                    timestamp=timestamp,
                    direction=direction,
                    entry_price=row['close'],
                    confidence=confidence
                )
                open_positions.append(new_pos)
                
                print(f"📍 Trade #{new_pos.id}: OPEN {direction} @ ${row['close']:,.0f} | "
                      f"Conf: {confidence*100:.1f}% | TP: ${new_pos.tp_price:,.0f} | SL: ${new_pos.sl_price:,.0f} | "
                      f"Open: {len(open_positions)}/{max_concurrent}")
    
    # Final stats
    print("\n" + "=" * 80)
    print("📊 PROPER NO-LOOKAHEAD RESULTS")
    print("=" * 80)
    
    wins = [t for t in closed_trades if t.exit_reason == "TP"]
    losses = [t for t in closed_trades if t.exit_reason == "SL"]
    
    print(f"Total Closed Trades: {len(closed_trades)}")
    print(f"Still Open: {len(open_positions)}")
    print(f"Wins: {len(wins)} | Losses: {len(losses)}")
    
    if wins or losses:
        wr = len(wins) / (len(wins) + len(losses)) * 100
        print(f"Win Rate: {wr:.1f}%")
        
        print(f"\n🎯 Comparison:")
        print(f"Lookahead: 81.4% WR (231 trades)")
        print(f"This: {wr:.1f}% WR ({len(closed_trades)} trades)")
        
        if wr >= 75:
            print("✅ SUCCESS! Matches lookahead performance!")
        elif wr >= 60:
            print("⚠️  Close, but slightly lower")
        else:
            print("❌ Still has issues")
    
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
                'tp_price': pos.tp_price,
                'sl_price': pos.sl_price,
                'exit_reason': pos.exit_reason,
                'confidence': pos.confidence,
                'duration_min': (pos.exit_time - pos.entry_time).total_seconds() / 60
            })
        
        trades_df = pd.DataFrame(trades_data)
        trades_df.to_csv('proper_no_lookahead_results.csv', index=False)
        print(f"\n💾 Results saved to: proper_no_lookahead_results.csv")

if __name__ == "__main__":
    run_proper_no_lookahead()
