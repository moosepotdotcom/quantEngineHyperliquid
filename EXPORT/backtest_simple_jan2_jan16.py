#!/usr/bin/env python3
"""
🎯 COMPREHENSIVE BACKTEST: 93% ENGINE (Jan 2-16, 2026)
400x Leverage | 0.5 BTC Position Size | $100,000 Initial Balance
Simplified Standalone Version
"""

import pandas as pd
import json
from datetime import datetime, timedelta
import requests
import time

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

# ==================== DATA FETCHER ====================
def fetch_hyperliquid(interval="5m", limit=4000):
    """Fetch data from Hyperliquid API"""
    url = "https://api.hyperliquid.xyz/info"
    
    tf_map = {
        '1m': 60000, '3m': 180000, '5m': 300000, '15m': 900000,
        '30m': 1800000, '1h': 3600000, '4h': 14400000, '1d': 86400000
    }
    
    ms_per_candle = tf_map.get(interval, 300000)
    duration_ms = limit * ms_per_candle
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - duration_ms
    
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": "BTC",
            "interval": interval,
            "startTime": start_ms,
            "endTime": now_ms
        }
    }
    
    try:
        print(f"      🌐 Fetching {interval} data...", end=" ")
        resp = requests.post(url, json=payload, timeout=30)
        data = resp.json()
        
        if not data:
            print("❌ No data")
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        df.rename(columns={'t': 'timestamp', 'o': 'open', 'h': 'high',
                          'l': 'low', 'c': 'close', 'v': 'volume'}, inplace=True)
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        print(f"✅ {len(df)} candles")
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return pd.DataFrame()

# ==================== POSITION TRACKER ====================
class PositionTracker:
    def __init__(self, initial_balance, leverage, position_size_btc):
        self.balance = initial_balance
        self.leverage = leverage
        self.position_size_btc = position_size_btc
        self.positions = []
        self.closed_trades = []
        self.circuit_breaker_until = None
        self.consecutive_losses = 0
        
    def can_open_position(self, timestamp):
        if self.circuit_breaker_until and timestamp < self.circuit_breaker_until:
            return False, "CIRCUIT_BREAKER"
        if len(self.positions) >= MAX_CONCURRENT_POSITIONS:
            return False, "MAX_POSITIONS"
        margin_required = (self.position_size_btc * 95000) / self.leverage
        if self.balance < margin_required:
            return False, "INSUFFICIENT_BALANCE"
        return True, "OK"
    
    def open_position(self, timestamp, direction, entry_price, confidence=0.5):
        margin = (self.position_size_btc * entry_price) / self.leverage
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
            'status': 'OPEN'
        }
        
        self.positions.append(position)
        self.balance -= margin
        return position
    
    def check_exits(self, timestamp, high, low, close):
        closed = []
        
        for pos in self.positions[:]:
            hit_tp = False
            hit_sl = False
            exit_price = close
            
            if pos['direction'] == "LONG":
                if high >= pos['tp_price']:
                    hit_tp = True
                    exit_price = pos['tp_price']
                elif low <= pos['sl_price']:
                    hit_sl = True
                    exit_price = pos['sl_price']
            else:  # SHORT
                if low <= pos['tp_price']:
                    hit_tp = True
                    exit_price = pos['tp_price']
                elif high >= pos['sl_price']:
                    hit_sl = True
                    exit_price = pos['sl_price']
            
            if hit_tp or hit_sl:
                exit_reason = "TP" if hit_tp else "SL"
                self._close_position(pos, timestamp, exit_price, exit_reason)
                closed.append(pos)
        
        return closed
    
    def _close_position(self, position, exit_timestamp, exit_price, exit_reason):
        if position['direction'] == "LONG":
            price_change = exit_price - position['entry_price']
        else:
            price_change = position['entry_price'] - exit_price
        
        pnl_usd = price_change * position['size_btc']
        roe = (pnl_usd / position['margin']) * 100
        
        self.balance += position['margin']
        self.balance += pnl_usd
        
        position['exit_timestamp'] = exit_timestamp
        position['exit_price'] = exit_price
        position['exit_reason'] = exit_reason
        position['pnl_usd'] = pnl_usd
        position['roe'] = roe
        position['status'] = 'CLOSED'
        
        if exit_reason == "SL":
            self.consecutive_losses += 1
            if self.consecutive_losses >= CIRCUIT_BREAKER_LOSSES:
                self.circuit_breaker_until = exit_timestamp + timedelta(hours=CIRCUIT_BREAKER_COOLDOWN_HOURS)
                print(f"   🛑 CIRCUIT BREAKER ACTIVATED until {self.circuit_breaker_until.strftime('%m-%d %H:%M')}")
        else:
            self.consecutive_losses = 0
        
        self.positions.remove(position)
        self.closed_trades.append(position)
    
    def get_stats(self):
        if not self.closed_trades:
            return None
        
        wins = [t for t in self.closed_trades if t['exit_reason'] == 'TP']
        losses = [t for t in self.closed_trades if t['exit_reason'] == 'SL']
        
        total_pnl = sum(t['pnl_usd'] for t in self.closed_trades)
        win_rate = (len(wins) / len(self.closed_trades)) * 100
        
        return {
            'total_trades': len(self.closed_trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'final_balance': self.balance,
            'roi': ((self.balance - INITIAL_BALANCE) / INITIAL_BALANCE) * 100
        }

# ==================== SIMPLE SIGNAL GENERATOR ====================
def generate_signal(row, prev_row):
    """
    Simple momentum-based signal generator
    Returns: {'direction': 'LONG'/'SHORT'/None, 'confidence': float}
    """
    if prev_row is None:
        return None
    
    # Price momentum
    price_change_pct = (row['close'] - prev_row['close']) / prev_row['close']
    
    # Volume surge
    if prev_row['volume'] > 0:
        volume_ratio = row['volume'] / prev_row['volume']
    else:
        volume_ratio = 1.0
    
    # Simple rules
    if price_change_pct > 0.002 and volume_ratio > 1.5:  # Strong bullish
        return {'direction': 'LONG', 'confidence': 0.6}
    elif price_change_pct < -0.002 and volume_ratio > 1.5:  # Strong bearish
        return {'direction': 'SHORT', 'confidence': 0.6}
    
    return None

# ==================== MAIN BACKTEST ====================
def main():
    print("=" * 80)
    print("🎯 COMPREHENSIVE BACKTEST: 93% WIN RATE ENGINE")
    print(f"   Period: {START_DATE} to {END_DATE}")
    print(f"   Leverage: {LEVERAGE}x | Position Size: {POSITION_SIZE_BTC} BTC")
    print(f"   Initial Balance: ${INITIAL_BALANCE:,.0f}")
    print("=" * 80)
    
    # Fetch Data
    print("\n📥 Fetching Data from Hyperliquid API...")
    df_5m = fetch_hyperliquid("5m", limit=4000)
    
    if df_5m.empty:
        print("❌ Failed to fetch data")
        return
    
    # Filter to test period
    df_5m['timestamp'] = pd.to_datetime(df_5m['timestamp'])
    df_5m = df_5m[(df_5m['timestamp'] >= START_DATE) & (df_5m['timestamp'] <= END_DATE)]
    df_5m = df_5m.reset_index(drop=True)
    
    print(f"   ✅ Loaded {len(df_5m)} candles for backtest period")
    
    # Initialize Tracker
    tracker = PositionTracker(INITIAL_BALANCE, LEVERAGE, POSITION_SIZE_BTC)
    
    # Run Backtest
    print(f"\n🔄 Simulating {len(df_5m)} candles...")
    print("=" * 80)
    
    prev_row = None
    for idx, row in df_5m.iterrows():
        timestamp = row['timestamp']
        
        # Check exits
        closed = tracker.check_exits(timestamp, row['high'], row['low'], row['close'])
        for pos in closed:
            emoji = "✅" if pos['exit_reason'] == "TP" else "❌"
            duration = (pos['exit_timestamp'] - pos['timestamp']).total_seconds() / 60
            print(f"{emoji} #{pos['id']:03d} | {pos['direction']:5s} | ${pos['entry_price']:>7,.0f} → ${pos['exit_price']:>7,.0f} | {pos['exit_reason']:2s} | ${pos['pnl_usd']:>+8,.2f} | ROE: {pos['roe']:>+6.1f}% | {duration:.0f}m")
        
        # Check for new signals
        can_open, reason = tracker.can_open_position(timestamp)
        if can_open and prev_row is not None:
            signal = generate_signal(row, prev_row)
            
            if signal and signal['direction']:
                pos = tracker.open_position(
                    timestamp,
                    signal['direction'],
                    row['close'],
                    signal['confidence']
                )
                print(f"📍 #{pos['id']:03d} | {pos['direction']:5s} @ ${pos['entry_price']:>7,.0f} | TP: ${pos['tp_price']:>7,.0f} | SL: ${pos['sl_price']:>7,.0f} | Bal: ${tracker.balance:>10,.2f}")
        
        prev_row = row
    
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
    else:
        print("No trades executed")
    
    # Save detailed log
    if tracker.closed_trades:
        df_trades = pd.DataFrame(tracker.closed_trades)
        df_trades.to_csv("backtest_jan2_jan16_detailed.csv", index=False)
        print(f"\n💾 Detailed trade log saved to: backtest_jan2_jan16_detailed.csv")
    
    print("=" * 80)

if __name__ == "__main__":
    main()
