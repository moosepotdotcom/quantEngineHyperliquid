#!/usr/bin/env python3
"""
81.9% WR ENGINE - LIVE TRADING SIMULATION
Proper position tracking, real-time P&L, no lookahead
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
        # Clean old losses
        self.losses = [t for t in self.losses if (timestamp - t).total_seconds() < self.window_minutes * 60]
        self.losses.append(timestamp)
        
        if len(self.losses) >= self.max_losses:
            self.cooldown_until = timestamp + pd.Timedelta(hours=self.cooldown_hours)
            print(f"   🛑 CIRCUIT BREAKER ACTIVATED until {self.cooldown_until}")
    
    def reset(self):
        """Reset after a win"""
        self.losses = []

# Configuration
LEVERAGE = 400
POSITION_SIZE_BTC = 0.5
INITIAL_BALANCE = 100000.0
TP_PCT = 0.015  # 1.5%
SL_PCT = 0.008  # 0.8%
THRESHOLD = 0.45  # 45% confidence
MAX_CONCURRENT = 6  # Maximum concurrent positions
MAX_POSITION_DURATION_HOURS = 16  # Expire after 16 hours

# Filters (81.9% WR configuration)
USE_HURST_FILTER = True
USE_ATR_PENALTY = False  # CRITICAL: Must be OFF
USE_AI_SMART_FILTER = True

START_DATE = "2026-01-02"
END_DATE = "2026-01-17"

class Position:
    """Represents an open trading position"""
    def __init__(self, id, timestamp, direction, entry_price, confidence, leverage, size_btc):
        self.id = id
        self.entry_time = timestamp
        self.direction = direction
        self.entry_price = entry_price
        self.confidence = confidence
        self.leverage = leverage
        self.size_btc = size_btc
        
        # Calculate TP/SL
        if direction == "LONG":
            self.tp_price = entry_price * (1 + TP_PCT)
            self.sl_price = entry_price * (1 - SL_PCT)
        else:  # SHORT
            self.tp_price = entry_price * (1 - TP_PCT)
            self.sl_price = entry_price * (1 + SL_PCT)
        
        # Calculate margin
        self.margin = (size_btc * entry_price) / leverage
        
        # Status
        self.status = "OPEN"
        self.exit_time = None
        self.exit_price = None
        self.exit_reason = None
        self.pnl = 0.0
        self.roe = 0.0
        
    def check_exit(self, high, low, close, timestamp):
        """Check if position should be closed"""
        # Check TP/SL
        if self.direction == "LONG":
            if high >= self.tp_price:
                self.close(self.tp_price, "TP", timestamp)
                return True
            elif low <= self.sl_price:
                self.close(self.sl_price, "SL", timestamp)
                return True
        else:  # SHORT
            if low <= self.tp_price:
                self.close(self.tp_price, "TP", timestamp)
                return True
            elif high >= self.sl_price:
                self.close(self.sl_price, "SL", timestamp)
                return True
        
        # Check expiration (16 hours)
        duration = (timestamp - self.entry_time).total_seconds() / 3600
        if duration >= MAX_POSITION_DURATION_HOURS:
            self.close(close, "EXPIRED", timestamp)
            return True
        
        return False
    
    def close(self, exit_price, reason, timestamp):
        """Close the position"""
        self.status = "CLOSED"
        self.exit_price = exit_price
        self.exit_reason = reason
        self.exit_time = timestamp
        
        # Calculate P&L
        if self.direction == "LONG":
            price_change = exit_price - self.entry_price
        else:  # SHORT
            price_change = self.entry_price - exit_price
        
        self.pnl = price_change * self.size_btc
        self.roe = (self.pnl / self.margin) * 100
    
    def get_unrealized_pnl(self, current_price):
        """Calculate unrealized P&L"""
        if self.status == "CLOSED":
            return self.pnl
        
        if self.direction == "LONG":
            price_change = current_price - self.entry_price
        else:
            price_change = self.entry_price - current_price
        
        return price_change * self.size_btc

class LiveTradingEngine:
    """Live trading simulation with proper position management"""
    def __init__(self, initial_balance, max_concurrent):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.max_concurrent = max_concurrent
        
        self.open_positions = []
        self.closed_positions = []
        self.position_counter = 0
        
        self.breaker = CustomCircuitBreaker(max_losses=2, window_minutes=60, cooldown_hours=4)
        
    def can_open_position(self):
        """Check if we can open a new position"""
        return len(self.open_positions) < self.max_concurrent
    
    def get_available_balance(self):
        """Get balance available for new positions"""
        used_margin = sum(pos.margin for pos in self.open_positions)
        return self.balance - used_margin
    
    def open_position(self, timestamp, direction, entry_price, confidence):
        """Open a new position"""
        if not self.can_open_position():
            return None
        
        # Check if we have enough balance
        required_margin = (POSITION_SIZE_BTC * entry_price) / LEVERAGE
        if self.get_available_balance() < required_margin:
            return None
        
        # Create position
        self.position_counter += 1
        position = Position(
            id=self.position_counter,
            timestamp=timestamp,
            direction=direction,
            entry_price=entry_price,
            confidence=confidence,
            leverage=LEVERAGE,
            size_btc=POSITION_SIZE_BTC
        )
        
        self.open_positions.append(position)
        return position
    
    def check_exits(self, high, low, close, timestamp):
        """Check all open positions for exits"""
        closed_this_tick = []
        remaining_positions = []
        
        for pos in self.open_positions:
            if pos.check_exit(high, low, close, timestamp):
                # Position closed
                self.balance += pos.margin + pos.pnl
                self.closed_positions.append(pos)
                closed_this_tick.append(pos)
                
                # Update circuit breaker
                if pos.exit_reason == "SL":
                    self.breaker.record_loss(timestamp)
            else:
                remaining_positions.append(pos)
        
        self.open_positions = remaining_positions
        return closed_this_tick
    
    def get_total_pnl(self, current_price):
        """Get total P&L (realized + unrealized)"""
        realized = sum(pos.pnl for pos in self.closed_positions)
        unrealized = sum(pos.get_unrealized_pnl(current_price) for pos in self.open_positions)
        return realized + unrealized
    
    def get_stats(self):
        """Get trading statistics"""
        if not self.closed_positions:
            return None
        
        wins = [p for p in self.closed_positions if p.exit_reason == "TP"]
        losses = [p for p in self.closed_positions if p.exit_reason == "SL"]
        expired = [p for p in self.closed_positions if p.exit_reason == "EXPIRED"]
        
        total = len(self.closed_positions)
        win_rate = (len(wins) / (len(wins) + len(losses)) * 100) if (len(wins) + len(losses)) > 0 else 0
        
        total_pnl = sum(p.pnl for p in self.closed_positions)
        roi = ((self.balance - self.initial_balance) / self.initial_balance) * 100
        
        return {
            'total_trades': total,
            'wins': len(wins),
            'losses': len(losses),
            'expired': len(expired),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'balance': self.balance,
            'roi': roi,
            'avg_win': sum(p.pnl for p in wins) / len(wins) if wins else 0,
            'avg_loss': sum(p.pnl for p in losses) / len(losses) if losses else 0,
        }

def run_live_simulation():
    print("=" * 80)
    print("🎯 81.9% WR ENGINE - LIVE TRADING SIMULATION")
    print("=" * 80)
    print(f"Period: {START_DATE} to {END_DATE}")
    print(f"Config: {LEVERAGE}x Leverage | {POSITION_SIZE_BTC} BTC")
    print(f"TP: {TP_PCT*100}% | SL: {SL_PCT*100}%")
    print(f"Threshold: {THRESHOLD*100}%")
    print(f"Max Concurrent: {MAX_CONCURRENT} positions")
    print(f"Max Duration: {MAX_POSITION_DURATION_HOURS} hours")
    print(f"Filters: Hurst={USE_HURST_FILTER}, ATR Penalty={USE_ATR_PENALTY}, AI Smart={USE_AI_SMART_FILTER}")
    print("=" * 80)
    
    engine = TradingEngine()
    trader = LiveTradingEngine(INITIAL_BALANCE, MAX_CONCURRENT)
    
    print("\n📊 Fetching data from Hyperliquid...")
    
    start = pd.to_datetime(START_DATE)
    end = pd.to_datetime(END_DATE)
    days = (end - start).days + 1
    limit = days * 288 + 500
    
    df5 = engine.fetch_data('5m', limit=limit)
    df15 = engine.fetch_data('15m', limit=limit)
    df1h = engine.fetch_data('1h', limit=limit)
    
    if df5 is None or len(df5) == 0:
        print("❌ Failed to fetch data")
        return
    
    print(f"✅ Fetched {len(df5)} 5m candles")
    
    df5['timestamp'] = pd.to_datetime(df5['timestamp'])
    df15['timestamp'] = pd.to_datetime(df15['timestamp'])
    df1h['timestamp'] = pd.to_datetime(df1h['timestamp'])
    
    df5 = df5[(df5['timestamp'] >= START_DATE) & (df5['timestamp'] <= END_DATE)]
    df15 = df15[(df15['timestamp'] >= START_DATE) & (df15['timestamp'] <= END_DATE)]
    df1h = df1h[(df1h['timestamp'] >= START_DATE) & (df1h['timestamp'] <= END_DATE)]
    
    print(f"📅 Filtered to {len(df5)} candles in date range")
    
    print("🔧 Adding indicators...")
    df5 = add_all_indicators(df5)
    df15 = add_all_indicators(df15)
    df1h = add_all_indicators(df1h)
    
    df5.set_index('timestamp', inplace=True)
    df15.set_index('timestamp', inplace=True)
    df1h.set_index('timestamp', inplace=True)
    
    exclude = ['open', 'high', 'low', 'close', 'volume']
    ctx15 = [c for c in df15.columns if c not in exclude]
    df15_renamed = df15[ctx15].copy().rename(columns={c: f"{c}_15m" for c in ctx15})
    df_merged = pd.concat([df5, df15_renamed.reindex(df5.index, method='ffill')], axis=1)
    
    ctx1h = [c for c in df1h.columns if c not in exclude]
    df1h_renamed = df1h[ctx1h].copy().rename(columns={c: f"{c}_1h" for c in ctx1h})
    df_merged = pd.concat([df_merged, df1h_renamed.reindex(df5.index, method='ffill')], axis=1)
    
    df_merged.dropna(inplace=True)
    
    print(f"✅ Prepared {len(df_merged)} candles for simulation\n")
    print("🚀 Running live simulation...\n")
    
    for idx, row in df_merged.iterrows():
        timestamp = idx
        current_price = row['close']
        
        # 1. Check exits for all open positions
        closed_positions = trader.check_exits(row['high'], row['low'], row['close'], timestamp)
        
        for pos in closed_positions:
            emoji = "✅" if pos.exit_reason == "TP" else "❌" if pos.exit_reason == "SL" else "⏱️"
            print(f"{emoji} Position #{pos.id}: {pos.direction} | "
                  f"Entry: ${pos.entry_price:,.0f} → Exit: ${pos.exit_price:,.0f} | "
                  f"{pos.exit_reason} | PnL: ${pos.pnl:+,.2f} | "
                  f"Balance: ${trader.balance:,.2f} | Open: {len(trader.open_positions)}")
        
        # 2. Check for new signals (if we can open more positions)
        if trader.can_open_position():
            # Skip if circuit breaker active
            if trader.breaker.cooldown_until and timestamp < trader.breaker.cooldown_until:
                continue
            
            # Prepare features
            X_dict = {c: row.get(c, 0.0) for c in MTF_FEATURE_LIST}
            X = np.array([X_dict[c] for c in MTF_FEATURE_LIST]).reshape(1, -1)
            X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
            
            probas = engine.get_ensemble_proba('MTF', X)[0]
            prob_long, prob_short = float(probas[1]), float(probas[2])
            
            direction = None
            confidence = 0.0
            
            if prob_long >= THRESHOLD:
                direction = 'LONG'
                confidence = prob_long
            elif prob_short >= THRESHOLD:
                direction = 'SHORT'
                confidence = prob_short
            
            if direction:
                # Apply filters
                hurst = row.get('hurst', 0.5)
                rsi = row.get('rsi_14', 50)
                rsi7 = row.get('rsi_7', 50)
                
                # Hurst Filter
                if USE_HURST_FILTER and direction == 'LONG' and rsi < 30 and hurst > 0.5:
                    continue
                
                # AI Smart Filter
                if USE_AI_SMART_FILTER and direction == 'SHORT' and rsi7 < 25:
                    continue
                
                # Open position
                position = trader.open_position(timestamp, direction, current_price, confidence)
                if position:
                    print(f"📍 Position #{position.id}: OPEN {direction} @ ${current_price:,.0f} | "
                          f"Confidence: {confidence*100:.1f}% | "
                          f"TP: ${position.tp_price:,.0f} | SL: ${position.sl_price:,.0f} | "
                          f"Open: {len(trader.open_positions)}/{MAX_CONCURRENT}")
    
    # Close any remaining open positions at end
    print(f"\n⏱️  Closing {len(trader.open_positions)} remaining positions at market close...")
    for pos in trader.open_positions:
        pos.close(df_merged.iloc[-1]['close'], "MARKET_CLOSE", df_merged.index[-1])
        trader.balance += pos.margin + pos.pnl
        trader.closed_positions.append(pos)
    trader.open_positions = []
    
    # Final stats
    print("\n" + "=" * 80)
    print("📊 LIVE TRADING SIMULATION RESULTS")
    print("=" * 80)
    
    stats = trader.get_stats()
    if stats:
        print(f"Total Trades: {stats['total_trades']}")
        print(f"Wins: {stats['wins']} | Losses: {stats['losses']} | Expired: {stats['expired']}")
        print(f"Win Rate: {stats['win_rate']:.1f}%")
        print(f"Total P&L: ${stats['total_pnl']:+,.2f}")
        print(f"Final Balance: ${stats['balance']:,.2f}")
        print(f"ROI: {stats['roi']:+.2f}%")
        print(f"Avg Win: ${stats['avg_win']:,.2f}")
        print(f"Avg Loss: ${stats['avg_loss']:,.2f}")
        
        print(f"\n🎯 Comparison:")
        print(f"Signal-Based Backtest: 81.9% WR (316 signals)")
        print(f"Live Simulation: {stats['win_rate']:.1f}% WR ({stats['total_trades']} trades)")
    else:
        print("No trades executed")
    
    print("=" * 80)
    
    # Save results
    if trader.closed_positions:
        trades_data = []
        for pos in trader.closed_positions:
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
                'pnl': pos.pnl,
                'roe': pos.roe,
                'confidence': pos.confidence,
                'duration_hours': (pos.exit_time - pos.entry_time).total_seconds() / 3600
            })
        
        trades_df = pd.DataFrame(trades_data)
        trades_df.to_csv('live_simulation_results.csv', index=False)
        print(f"\n💾 Results saved to: live_simulation_results.csv")

if __name__ == "__main__":
    run_live_simulation()
