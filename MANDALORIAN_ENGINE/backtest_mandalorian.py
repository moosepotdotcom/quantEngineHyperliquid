#!/usr/bin/env python3
"""
🛡️ MANDALORIAN ENGINE - BACKTEST
Same configuration as Cloud Run deployment
Testing on Jan 2-17, 2026 live Hyperliquid data
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quant_engine import TradingEngine, add_all_indicators, MTF_FEATURE_LIST

# ==================== CONFIGURATION (Same as Cloud Run) ====================
LEVERAGE = 400
POSITION_SIZE_BTC = 0.5
INITIAL_BALANCE = 100000.0
TP_PCT = 0.015  # 1.5%
SL_PCT = 0.008  # 0.8%
LONG_THRESHOLD = 0.45  # 45%
SHORT_THRESHOLD = 0.45  # 45%

# Backtest period
START_DATE = "2026-01-02"
END_DATE = "2026-01-17"

# ==================== POSITION TRACKER ====================
class BacktestTracker:
    def __init__(self, initial_balance):
        self.balance = initial_balance
        self.position = None
        self.trades = []
        
    def open_position(self, timestamp, direction, entry_price, confidence):
        if self.position:
            return False
        
        margin = (POSITION_SIZE_BTC * entry_price) / LEVERAGE
        tp_price = entry_price * (1 + TP_PCT) if direction == "LONG" else entry_price * (1 - TP_PCT)
        sl_price = entry_price * (1 - SL_PCT) if direction == "LONG" else entry_price * (1 + SL_PCT)
        
        self.position = {
            'timestamp': timestamp,
            'direction': direction,
            'entry_price': entry_price,
            'tp_price': tp_price,
            'sl_price': sl_price,
            'margin': margin,
            'confidence': confidence
        }
        
        self.balance -= margin
        return True
    
    def check_exit(self, high, low, close, timestamp):
        if not self.position:
            return None
        
        pos = self.position
        hit_tp = False
        hit_sl = False
        exit_price = None
        
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
            return self._close_position(exit_price, exit_reason, timestamp)
        
        return None
    
    def _close_position(self, exit_price, exit_reason, timestamp):
        pos = self.position
        
        if pos['direction'] == "LONG":
            price_change = exit_price - pos['entry_price']
        else:
            price_change = pos['entry_price'] - exit_price
        
        pnl_usd = price_change * POSITION_SIZE_BTC
        roe = (pnl_usd / pos['margin']) * 100
        
        self.balance += pos['margin']
        self.balance += pnl_usd
        
        duration = (timestamp - pos['timestamp']).total_seconds() / 60
        
        trade = {
            'entry_time': pos['timestamp'],
            'exit_time': timestamp,
            'direction': pos['direction'],
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'exit_reason': exit_reason,
            'pnl': pnl_usd,
            'roe': roe,
            'balance': self.balance,
            'duration_min': duration,
            'confidence': pos['confidence']
        }
        
        self.trades.append(trade)
        self.position = None
        
        return trade

# ==================== MAIN BACKTEST ====================
def run_backtest():
    print("=" * 80)
    print("🛡️ MANDALORIAN ENGINE - BACKTEST")
    print("=" * 80)
    print(f"Period: {START_DATE} to {END_DATE}")
    print(f"Config: {LEVERAGE}x Leverage | {POSITION_SIZE_BTC} BTC")
    print(f"TP: {TP_PCT*100}% | SL: {SL_PCT*100}%")
    print(f"Thresholds: LONG≥{LONG_THRESHOLD*100}% | SHORT≥{SHORT_THRESHOLD*100}%")
    print("=" * 80)
    
    engine = TradingEngine()
    tracker = BacktestTracker(INITIAL_BALANCE)
    
    # Fetch data for entire period
    print("\n📊 Fetching data from Hyperliquid...")
    
    # Calculate days needed
    start = pd.to_datetime(START_DATE)
    end = pd.to_datetime(END_DATE)
    days = (end - start).days + 1
    limit = days * 288 + 500  # 288 5m candles per day + buffer
    
    df5 = engine.fetch_data('5m', limit=limit)
    df15 = engine.fetch_data('15m', limit=limit)
    df1h = engine.fetch_data('1h', limit=limit)
    
    if df5 is None or len(df5) == 0:
        print("❌ Failed to fetch data")
        return
    
    print(f"✅ Fetched {len(df5)} 5m candles")
    
    # Filter to date range
    df5['timestamp'] = pd.to_datetime(df5['timestamp'])
    df15['timestamp'] = pd.to_datetime(df15['timestamp'])
    df1h['timestamp'] = pd.to_datetime(df1h['timestamp'])
    
    df5 = df5[(df5['timestamp'] >= START_DATE) & (df5['timestamp'] <= END_DATE)]
    df15 = df15[(df15['timestamp'] >= START_DATE) & (df15['timestamp'] <= END_DATE)]
    df1h = df1h[(df1h['timestamp'] >= START_DATE) & (df1h['timestamp'] <= END_DATE)]
    
    print(f"📅 Filtered to {len(df5)} candles in date range")
    
    # Add indicators
    print("🔧 Adding indicators...")
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
    
    print(f"✅ Prepared {len(df_merged)} candles for backtest\n")
    
    # Circuit breaker tracking
    recent_losses = []
    cooldown_until = None
    
    # Run backtest
    print("🚀 Running backtest...\n")
    
    for idx, row in df_merged.iterrows():
        timestamp = idx
        
        # Check exits first
        closed_trade = tracker.check_exit(row['high'], row['low'], row['close'], timestamp)
        if closed_trade:
            emoji = "✅" if closed_trade['exit_reason'] == "TP" else "❌"
            print(f"{emoji} Trade #{len(tracker.trades)}: {closed_trade['direction']} | "
                  f"Entry: ${closed_trade['entry_price']:,.0f} → Exit: ${closed_trade['exit_price']:,.0f} | "
                  f"{closed_trade['exit_reason']} | PnL: ${closed_trade['pnl']:+,.2f} | "
                  f"Balance: ${closed_trade['balance']:,.2f}")
            
            # Update circuit breaker
            if closed_trade['exit_reason'] == 'SL':
                recent_losses = [t for t in recent_losses if (timestamp - t).total_seconds() < 3600]
                recent_losses.append(timestamp)
                if len(recent_losses) >= 2:
                    cooldown_until = timestamp + pd.Timedelta(hours=4)
                    print(f"   🛑 CIRCUIT BREAKER ACTIVATED until {cooldown_until}")
        
        # Check for new signals (if no position)
        if not tracker.position:
            # Check circuit breaker
            if cooldown_until and timestamp < cooldown_until:
                continue
            
            # Prepare features
            X_dict = {c: row.get(c, 0.0) for c in MTF_FEATURE_LIST}
            X = np.array([X_dict[c] for c in MTF_FEATURE_LIST]).reshape(1, -1)
            X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
            
            # Get prediction
            probas = engine.get_ensemble_proba('MTF', X)[0]
            prob_long, prob_short = float(probas[1]), float(probas[2])
            
            direction = None
            confidence = 0.0
            
            if prob_long >= LONG_THRESHOLD:
                direction = 'LONG'
                confidence = prob_long
            elif prob_short >= SHORT_THRESHOLD:
                direction = 'SHORT'
                confidence = prob_short
            
            if direction:
                # Apply shields (same as Cloud Run)
                hurst = row.get('hurst', 0.5)
                rsi = row.get('rsi_14', 50)
                rsi7 = row.get('rsi_7', 50)
                
                # Mandalorian Filter
                if direction == 'LONG' and rsi < 30 and hurst > 0.5:
                    continue
                
                # AI Smart Filter
                if direction == 'SHORT' and rsi7 < 25:
                    continue
                
                # Open position
                if tracker.open_position(timestamp, direction, row['close'], confidence):
                    print(f"📍 Trade #{len(tracker.trades)+1}: OPEN {direction} @ ${row['close']:,.0f} | "
                          f"Confidence: {confidence*100:.1f}%")
    
    # Final stats
    print("\n" + "=" * 80)
    print("📊 BACKTEST RESULTS")
    print("=" * 80)
    
    if tracker.trades:
        wins = [t for t in tracker.trades if t['exit_reason'] == 'TP']
        losses = [t for t in tracker.trades if t['exit_reason'] == 'SL']
        total_pnl = sum(t['pnl'] for t in tracker.trades)
        
        print(f"Total Trades: {len(tracker.trades)}")
        print(f"Wins: {len(wins)} | Losses: {len(losses)}")
        print(f"Win Rate: {(len(wins)/len(tracker.trades)*100):.1f}%")
        print(f"Total PnL: ${total_pnl:+,.2f}")
        print(f"Final Balance: ${tracker.balance:,.2f}")
        print(f"ROI: {((tracker.balance - INITIAL_BALANCE) / INITIAL_BALANCE * 100):+.2f}%")
        
        if wins:
            avg_win = sum(t['pnl'] for t in wins) / len(wins)
            print(f"Avg Win: ${avg_win:,.2f}")
        if losses:
            avg_loss = sum(t['pnl'] for t in losses) / len(losses)
            print(f"Avg Loss: ${avg_loss:,.2f}")
        
        avg_duration = sum(t['duration_min'] for t in tracker.trades) / len(tracker.trades)
        print(f"Avg Duration: {avg_duration:.0f} minutes")
        
    else:
        print("No trades executed")
    
    print("=" * 80)
    
    # Save trades to CSV
    if tracker.trades:
        trades_df = pd.DataFrame(tracker.trades)
        trades_df.to_csv('mandalorian_backtest_results.csv', index=False)
        print(f"\n💾 Results saved to: mandalorian_backtest_results.csv")

if __name__ == "__main__":
    run_backtest()
