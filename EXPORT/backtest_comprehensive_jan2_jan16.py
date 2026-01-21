#!/usr/bin/env python3
"""
🎯 COMPREHENSIVE BACKTEST: 93% ENGINE (Jan 2-16, 2026)
400x Leverage | 0.5 BTC Position Size | $100,000 Initial Balance
With Circuit Breaker & Multi-Position Tracking
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import json
from datetime import datetime, timedelta
from utils.fetch_data import fetch_live_data
from quant_engine import QuantEngine

# ==================== CONFIGURATION ====================
LEVERAGE = 400
POSITION_SIZE_BTC = 0.5
INITIAL_BALANCE = 100000.0
TP_PCT = 0.015  # 1.5%
SL_PCT = 0.008  # 0.8%

# Circuit Breaker
MAX_CONCURRENT_POSITIONS = 6
CIRCUIT_BREAKER_LOSSES = 2
CIRCUIT_BREAKER_COOLDOWN_HOURS = 4

# Test Period
START_DATE = "2026-01-02"
END_DATE = "2026-01-16"

# ==================== POSITION TRACKER ====================
class PositionTracker:
    def __init__(self, initial_balance, leverage, position_size_btc):
        self.balance = initial_balance
        self.leverage = leverage
        self.position_size_btc = position_size_btc
        self.positions = []  # Active positions
        self.closed_trades = []  # Trade history
        self.circuit_breaker_until = None
        self.consecutive_losses = 0
        
    def can_open_position(self, timestamp):
        # Check circuit breaker
        if self.circuit_breaker_until and timestamp < self.circuit_breaker_until:
            return False, "CIRCUIT_BREAKER"
        
        # Check max concurrent positions
        if len(self.positions) >= MAX_CONCURRENT_POSITIONS:
            return False, "MAX_POSITIONS"
        
        # Check balance
        margin_required = self.calculate_margin(self.position_size_btc, 95000)  # Approx price
        if self.balance < margin_required:
            return False, "INSUFFICIENT_BALANCE"
        
        return True, "OK"
    
    def calculate_margin(self, size_btc, price):
        """Calculate margin required for position"""
        notional = size_btc * price
        return notional / self.leverage
    
    def open_position(self, timestamp, direction, entry_price, confidence, strategy):
        """Open a new position"""
        margin = self.calculate_margin(self.position_size_btc, entry_price)
        tp_price = entry_price * (1 + TP_PCT) if direction == "LONG" else entry_price * (1 - TP_PCT)
        sl_price = entry_price * (1 - SL_PCT) if direction == "LONG" else entry_price * (1 + SL_PCT)
        
        position = {
            'id': len(self.closed_trades) + len(self.positions) + 1,
            'timestamp': timestamp,
            'direction': direction,
            'entry_price': entry_price,
            'size_btc': self.position_size_btc,
            'margin': margin,
            'tp_price': tp_price,
            'sl_price': sl_price,
            'confidence': confidence,
            'strategy': strategy,
            'status': 'OPEN'
        }
        
        self.positions.append(position)
        self.balance -= margin  # Lock margin
        return position
    
    def check_exits(self, timestamp, current_price):
        """Check if any positions hit TP/SL"""
        closed = []
        
        for pos in self.positions[:]:  # Copy to avoid modification during iteration
            if pos['direction'] == "LONG":
                if current_price >= pos['tp_price']:
                    self._close_position(pos, timestamp, current_price, "TP")
                    closed.append(pos)
                elif current_price <= pos['sl_price']:
                    self._close_position(pos, timestamp, current_price, "SL")
                    closed.append(pos)
            else:  # SHORT
                if current_price <= pos['tp_price']:
                    self._close_position(pos, timestamp, current_price, "TP")
                    closed.append(pos)
                elif current_price >= pos['sl_price']:
                    self._close_position(pos, timestamp, current_price, "SL")
                    closed.append(pos)
        
        return closed
    
    def _close_position(self, position, exit_timestamp, exit_price, exit_reason):
        """Close a position and update balance"""
        # Calculate PnL
        if position['direction'] == "LONG":
            price_change = exit_price - position['entry_price']
        else:
            price_change = position['entry_price'] - exit_price
        
        pnl_usd = price_change * position['size_btc']
        roe = (pnl_usd / position['margin']) * 100
        
        # Update balance
        self.balance += position['margin']  # Return margin
        self.balance += pnl_usd  # Add/subtract PnL
        
        # Update position
        position['exit_timestamp'] = exit_timestamp
        position['exit_price'] = exit_price
        position['exit_reason'] = exit_reason
        position['pnl_usd'] = pnl_usd
        position['roe'] = roe
        position['status'] = 'CLOSED'
        
        # Track consecutive losses for circuit breaker
        if exit_reason == "SL":
            self.consecutive_losses += 1
            if self.consecutive_losses >= CIRCUIT_BREAKER_LOSSES:
                self.circuit_breaker_until = exit_timestamp + timedelta(hours=CIRCUIT_BREAKER_COOLDOWN_HOURS)
                print(f"   🛑 CIRCUIT BREAKER ACTIVATED until {self.circuit_breaker_until}")
        else:
            self.consecutive_losses = 0  # Reset on TP
        
        # Move to closed trades
        self.positions.remove(position)
        self.closed_trades.append(position)
    
    def get_stats(self):
        """Calculate performance statistics"""
        if not self.closed_trades:
            return None
        
        wins = [t for t in self.closed_trades if t['exit_reason'] == 'TP']
        losses = [t for t in self.closed_trades if t['exit_reason'] == 'SL']
        
        total_pnl = sum(t['pnl_usd'] for t in self.closed_trades)
        win_rate = (len(wins) / len(self.closed_trades)) * 100 if self.closed_trades else 0
        
        return {
            'total_trades': len(self.closed_trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'final_balance': self.balance,
            'roi': ((self.balance - INITIAL_BALANCE) / INITIAL_BALANCE) * 100
        }

# ==================== MAIN BACKTEST ====================
def main():
    print("=" * 80)
    print("🎯 COMPREHENSIVE BACKTEST: 93% WIN RATE ENGINE")
    print(f"   Period: {START_DATE} to {END_DATE}")
    print(f"   Leverage: {LEVERAGE}x | Position Size: {POSITION_SIZE_BTC} BTC")
    print(f"   Initial Balance: ${INITIAL_BALANCE:,.0f}")
    print("=" * 80)
    
    # Initialize Engine
    print("\n📦 Loading Quant Engine...")
    engine = QuantEngine(
        model_dir="models",
        config_path="golden_config.json"
    )
    
    # Fetch Data
    print(f"\n📥 Fetching Data from Hyperliquid API...")
    df_5m = fetch_live_data("BTC", "5m", limit=4000)
    df_15m = fetch_live_data("BTC", "15m", limit=4000)
    df_1h = fetch_live_data("BTC", "1h", limit=4000)
    
    # Filter to test period
    df_5m = df_5m[(df_5m['timestamp'] >= START_DATE) & (df_5m['timestamp'] <= END_DATE)]
    print(f"   Loaded {len(df_5m)} candles for backtest period")
    
    # Initialize Position Tracker
    tracker = PositionTracker(INITIAL_BALANCE, LEVERAGE, POSITION_SIZE_BTC)
    
    # Run Backtest
    print(f"\n🔄 Simulating {len(df_5m)} candles...")
    print("=" * 80)
    
    for idx, row in df_5m.iterrows():
        timestamp = row['timestamp']
        current_price = row['close']
        
        # Check exits first
        closed = tracker.check_exits(timestamp, current_price)
        for pos in closed:
            emoji = "✅" if pos['exit_reason'] == "TP" else "❌"
            print(f"{emoji} #{pos['id']:03d} | {pos['direction']:5s} | Entry: ${pos['entry_price']:,.0f} → Exit: ${pos['exit_price']:,.0f} | {pos['exit_reason']:2s} | PnL: ${pos['pnl_usd']:+,.2f} | ROE: {pos['roe']:+.1f}%")
        
        # Check for new signals
        can_open, reason = tracker.can_open_position(timestamp)
        if not can_open:
            continue
        
        # Get signal from engine
        signal = engine.get_signal(timestamp, df_5m, df_15m, df_1h)
        
        if signal and signal['direction'] in ['LONG', 'SHORT']:
            pos = tracker.open_position(
                timestamp,
                signal['direction'],
                current_price,
                signal['confidence'],
                signal['strategy']
            )
            print(f"📍 #{pos['id']:03d} | {pos['direction']:5s} OPENED @ ${pos['entry_price']:,.0f} | TP: ${pos['tp_price']:,.0f} | SL: ${pos['sl_price']:,.0f} | Conf: {pos['confidence']:.3f}")
    
    # Final Stats
    print("\n" + "=" * 80)
    print("📊 BACKTEST RESULTS")
    print("=" * 80)
    
    stats = tracker.get_stats()
    if stats:
        print(f"Total Trades:     {stats['total_trades']}")
        print(f"Wins:             {stats['wins']} ✅")
        print(f"Losses:           {stats['losses']} ❌")
        print(f"Win Rate:         {stats['win_rate']:.1f}%")
        print(f"Total PnL:        ${stats['total_pnl']:+,.2f}")
        print(f"Final Balance:    ${stats['final_balance']:,.2f}")
        print(f"ROI:              {stats['roi']:+.2f}%")
    
    # Save detailed log
    if tracker.closed_trades:
        df_trades = pd.DataFrame(tracker.closed_trades)
        df_trades.to_csv("EXPORT/backtest_jan2_jan16_detailed.csv", index=False)
        print(f"\n💾 Detailed trade log saved to: backtest_jan2_jan16_detailed.csv")
    
    print("=" * 80)

if __name__ == "__main__":
    main()
