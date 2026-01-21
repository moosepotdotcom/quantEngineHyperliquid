#!/usr/bin/env python3
"""
🎯 ML ENGINE - LIVE PAPER TRADING
82.6% Win Rate | 400x Leverage | 0.5 BTC Position Size
Mandalorian + AI Smart Filters | Circuit Breaker Protection
"""

import sys
import os
import time
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quant_engine import TradingEngine, add_all_indicators, MTF_FEATURE_LIST, CircuitBreaker

# ==================== CONFIGURATION ====================
LEVERAGE = 400
POSITION_SIZE_BTC = 0.5
INITIAL_BALANCE = 100000.0
TP_PCT = 0.015  # 1.5%
SL_PCT = 0.008  # 0.8%

# Paper Trading Mode
PAPER_MODE = True

# ==================== POSITION TRACKER ====================
class LivePositionTracker:
    def __init__(self, initial_balance):
        self.balance = initial_balance
        self.position = None
        self.trades = []
        
    def open_position(self, timestamp, direction, entry_price, confidence):
        if self.position:
            print(f"⚠️  Position already open, skipping")
            return
        
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
        print(f"📍 POSITION OPENED: {direction} @ ${entry_price:,.0f}")
        print(f"   TP: ${tp_price:,.0f} | SL: ${sl_price:,.0f}")
        print(f"   Margin: ${margin:,.2f} | Balance: ${self.balance:,.2f}")
    
    def check_exit(self, current_price, timestamp):
        if not self.position:
            return False
        
        pos = self.position
        hit_tp = False
        hit_sl = False
        
        if pos['direction'] == "LONG":
            if current_price >= pos['tp_price']:
                hit_tp = True
            elif current_price <= pos['sl_price']:
                hit_sl = True
        else:
            if current_price <= pos['tp_price']:
                hit_tp = True
            elif current_price >= pos['sl_price']:
                hit_sl = True
        
        if hit_tp or hit_sl:
            exit_reason = "TP" if hit_tp else "SL"
            self._close_position(current_price, exit_reason, timestamp)
            return True
        
        return False
    
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
        
        emoji = "✅" if exit_reason == "TP" else "❌"
        print(f"\n{emoji} POSITION CLOSED: {exit_reason}")
        print(f"   Entry: ${pos['entry_price']:,.0f} → Exit: ${exit_price:,.0f}")
        print(f"   PnL: ${pnl_usd:+,.2f} | ROE: {roe:+.1f}%")
        print(f"   Duration: {duration:.0f}m | Balance: ${self.balance:,.2f}\n")
        
        self.trades.append({
            'timestamp': pos['timestamp'],
            'exit_timestamp': timestamp,
            'direction': pos['direction'],
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'exit_reason': exit_reason,
            'pnl_usd': pnl_usd,
            'roe': roe,
            'balance': self.balance
        })
        
        self.position = None

# ==================== MAIN LOOP ====================
def main():
    print("=" * 80)
    print("🎯 ML ENGINE - LIVE PAPER TRADING")
    print(f"   Leverage: {LEVERAGE}x | Position Size: {POSITION_SIZE_BTC} BTC")
    print(f"   Initial Balance: ${INITIAL_BALANCE:,.0f}")
    print("=" * 80)
    
    engine = TradingEngine()
    tracker = LivePositionTracker(INITIAL_BALANCE)
    breaker = CircuitBreaker(max_losses=2, window_minutes=60, cooldown_hours=4)
    
    print("\n🚀 Starting live trading loop...")
    print("   Press Ctrl+C to stop\n")
    
    while True:
        try:
            # Fetch latest data
            df5 = engine.fetch_data('5m', limit=500)
            df15 = engine.fetch_data('15m', limit=500)
            df1h = engine.fetch_data('1h', limit=500)
            
            if df5 is None or len(df5) == 0:
                print("⚠️  Data fetch failed, retrying in 30s...")
                time.sleep(30)
                continue
            
            # Add indicators
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
            
            # Get latest row
            latest = df_merged.iloc[-1]
            timestamp = df_merged.index[-1]
            current_price = latest['close']
            
            # Check exits first
            if tracker.check_exit(current_price, timestamp):
                # Update breaker
                last_trade = tracker.trades[-1]
                if last_trade['exit_reason'] == 'TP':
                    breaker.cooldown_until = None
                else:
                    if not hasattr(breaker, 'sim_losses'): breaker.sim_losses = []
                    breaker.sim_losses = [t for t in breaker.sim_losses if (timestamp - t).total_seconds() < 3600]
                    breaker.sim_losses.append(timestamp)
                    if len(breaker.sim_losses) >= 2:
                        breaker.cooldown_until = timestamp + pd.Timedelta(hours=4)
                        print(f"🛑 CIRCUIT BREAKER ACTIVATED until {breaker.cooldown_until}")
            
            # Check for new signals (if no position)
            if not tracker.position:
                # Check circuit breaker
                if breaker.cooldown_until and timestamp < breaker.cooldown_until:
                    print(f"⏸️  Circuit breaker active until {breaker.cooldown_until}")
                    time.sleep(60)
                    continue
                
                # Prepare features
                X_dict = {c: latest.get(c, 0.0) for c in MTF_FEATURE_LIST}
                X = np.array([X_dict[c] for c in MTF_FEATURE_LIST]).reshape(1, -1)
                X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
                
                # Get prediction
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
                    # Apply shields
                    hurst = latest.get('hurst', 0.5)
                    rsi = latest.get('rsi_14', 50)
                    rsi7 = latest.get('rsi_7', 50)
                    
                    # Mandalorian Filter
                    if direction == 'LONG' and rsi < 30 and hurst > 0.5:
                        print(f"🛡️  Mandalorian Shield: Blocked falling knife")
                        direction = None
                    
                    # AI Smart Filter
                    if direction == 'SHORT' and rsi7 < 25:
                        print(f"🛡️  AI Smart Filter: Blocked oversold short")
                        direction = None
                    
                    if direction:
                        tracker.open_position(timestamp, direction, current_price, confidence)
            
            # Sleep before next iteration
            print(f"💤 Sleeping 60s... (Price: ${current_price:,.0f})")
            time.sleep(60)
            
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(30)
    
    # Final stats
    if tracker.trades:
        wins = len([t for t in tracker.trades if t['exit_reason'] == 'TP'])
        losses = len([t for t in tracker.trades if t['exit_reason'] == 'SL'])
        total_pnl = sum(t['pnl_usd'] for t in tracker.trades)
        
        print("\n" + "=" * 80)
        print("📊 SESSION SUMMARY")
        print("=" * 80)
        print(f"Total Trades: {len(tracker.trades)}")
        print(f"Wins: {wins} | Losses: {losses}")
        print(f"Win Rate: {(wins/(wins+losses)*100):.1f}%")
        print(f"Total PnL: ${total_pnl:+,.2f}")
        print(f"Final Balance: ${tracker.balance:,.2f}")
        print("=" * 80)

if __name__ == "__main__":
    main()
