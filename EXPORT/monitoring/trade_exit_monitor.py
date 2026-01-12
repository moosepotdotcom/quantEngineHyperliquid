#!/usr/bin/env python3
"""
Trade Exit Monitor - Monitors open trades for TP/SL hits
"""
import os
import json
from datetime import datetime
from typing import List, Dict, Optional
import requests
import time

class TradeExitMonitor:
    """
    Monitors open trades and detects TP/SL hits
    """
    
    def __init__(self, logger):
        self.logger = logger
        self.open_trades = []
        self.closed_trades = []
        self.load_open_trades()
    
    def load_open_trades(self):
        """Load open trades from logger"""
        # For now, we'll track trades in memory
        # In production, this would load from persistent storage
        pass
    
    def add_trade(self, trade_signal: Dict, tp_price: float, sl_price: float):
        """
        Add a new trade to monitor
        
        Args:
            trade_signal: Trade signal dictionary with entry details
            tp_price: Take profit price
            sl_price: Stop loss price
        """
        # Validate trade signal has valid price
        entry_price = trade_signal.get('price', 0)
        
        if not entry_price or entry_price <= 0:
            print(f"\n⚠️  INVALID TRADE REJECTED!")
            print(f"   Reason: Entry price is {entry_price} (must be > 0)")
            print(f"   Model: {trade_signal.get('model', 'Unknown')}")
            return
        
        if not tp_price or tp_price <= 0:
            print(f"\n⚠️  INVALID TRADE REJECTED!")
            print(f"   Reason: TP price is {tp_price} (must be > 0)")
            return
        
        if not sl_price or sl_price <= 0:
            print(f"\n⚠️  INVALID TRADE REJECTED!")
            print(f"   Reason: SL price is {sl_price} (must be > 0)")
            return
        
        trade = {
            'trade_id': f"{trade_signal['model']}_{trade_signal['timestamp'].strftime('%Y%m%d_%H%M%S')}",
            'model': trade_signal['model'],
            'entry_time': trade_signal['timestamp'],
            'entry_price': entry_price,
            'tp_price': tp_price,
            'sl_price': sl_price,
            'confidence': trade_signal['confidence'],
            'status': 'OPEN'
        }
        
        self.open_trades.append(trade)
        
        # Log trade entry
        self.logger.log_trade_entry(
            prediction_id=trade['trade_id'],
            entry_price=trade['entry_price'],
            entry_time=trade['entry_time'],
            position_size=1000,  # $1000 position
            tp_price=tp_price,
            sl_price=sl_price
        )
        
        print(f"\n📝 Trade Added to Monitor:")
        print(f"   ID: {trade['trade_id']}")
        print(f"   Entry: ${trade['entry_price']:,.2f}")
        print(f"   TP: ${tp_price:,.2f}")
        print(f"   SL: ${sl_price:,.2f}")
    
    def get_current_price(self) -> Optional[float]:
        """Get current BTC price from Hyperliquid"""
        try:
            url = "https://api.hyperliquid.xyz/info"
            payload = {
                "type": "candleSnapshot",
                "req": {
                    "coin": "BTC",
                    "interval": "1m",
                    "startTime": 0,
                    "endTime": 9999999999999
                }
            }
            
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return float(data[-1]['c'])  # Close price of latest candle
            
            return None
        except Exception as e:
            print(f"⚠️ Error fetching price: {e}")
            return None
    
    def check_exits(self) -> List[Dict]:
        """
        Check all open trades for TP/SL hits (including historical)
        
        Returns:
            List of closed trades
        """
        if not self.open_trades:
            return []
        
        current_price = self.get_current_price()
        if current_price is None:
            return []
        
        closed_now = []
        
        for trade in self.open_trades[:]:  # Copy list to allow removal
            # Check historical prices since entry to catch missed TP/SL
            tp_hit, sl_hit, exit_price, exit_time = self._check_historical_prices(trade)
            
            if tp_hit:
                outcome = 'WIN'
                reason = 'Take Profit Hit'
            elif sl_hit:
                outcome = 'LOSS'
                reason = 'Stop Loss Hit'
            else:
                # Check current price
                if current_price >= trade['tp_price']:
                    outcome = 'WIN'
                    exit_price = trade['tp_price']
                    exit_time = datetime.now()
                    reason = 'Take Profit Hit'
                elif current_price <= trade['sl_price']:
                    outcome = 'LOSS'
                    exit_price = trade['sl_price']
                    exit_time = datetime.now()
                    reason = 'Stop Loss Hit'
                else:
                    # Trade still open
                    continue
            
            # Trade closed!
            trade['status'] = 'CLOSED'
            trade['exit_time'] = exit_time
            trade['exit_price'] = exit_price
            trade['outcome'] = outcome
            trade['reason'] = reason
            
            # Calculate P&L
            pnl_pct = ((exit_price - trade['entry_price']) / trade['entry_price']) * 100
            pnl_usd = (exit_price - trade['entry_price']) / trade['entry_price'] * 1000  # $1000 position
            
            trade['pnl_pct'] = pnl_pct
            trade['pnl_usd'] = pnl_usd
            
            # Log trade exit
            self.logger.log_trade_exit(
                trade_id=trade['trade_id'],
                exit_price=exit_price,
                exit_time=exit_time,
                outcome=outcome
            )
            
            # Print trade closure
            print(f"\n{'='*70}")
            print(f"🎯 TRADE CLOSED!")
            print(f"{'='*70}")
            print(f"   Model: {trade['model']}")
            print(f"   Entry: ${trade['entry_price']:,.2f}")
            print(f"   Exit: ${exit_price:,.2f}")
            print(f"   Reason: {reason}")
            print(f"   Outcome: {'✅ WIN' if outcome == 'WIN' else '❌ LOSS'}")
            print(f"   P&L: {'+' if pnl_usd > 0 else ''}{pnl_usd:.2f} USD ({'+' if pnl_pct > 0 else ''}{pnl_pct:.2f}%)")
            print(f"   Duration: {(exit_time - trade['entry_time']).total_seconds() / 3600:.1f} hours")
            print(f"{'='*70}")
            
            # Move to closed trades
            self.open_trades.remove(trade)
            self.closed_trades.append(trade)
            closed_now.append(trade)
        
        return closed_now
    
    def _check_historical_prices(self, trade: Dict) -> tuple:
        """
        Check historical prices since entry for TP/SL hits
        
        Args:
            trade: Trade dictionary
            
        Returns:
            (tp_hit, sl_hit, exit_price, exit_time)
        """
        try:
            # Fetch historical candles since entry
            url = "https://api.hyperliquid.xyz/info"
            
            # Get entry timestamp in milliseconds
            entry_ts = int(trade['entry_time'].timestamp() * 1000)
            now_ts = int(datetime.now().timestamp() * 1000)
            
            payload = {
                "type": "candleSnapshot",
                "req": {
                    "coin": "BTC",
                    "interval": "5m",  # 5-minute candles for precision
                    "startTime": entry_ts,
                    "endTime": now_ts
                }
            }
            
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                candles = response.json()
                
                if candles and len(candles) > 0:
                    # Check each candle for TP/SL hit
                    for candle in candles:
                        candle_time = datetime.fromtimestamp(int(candle['t']) / 1000)
                        high = float(candle['h'])
                        low = float(candle['l'])
                        
                        # Check TP hit (high touched TP)
                        if high >= trade['tp_price']:
                            return True, False, trade['tp_price'], candle_time
                        
                        # Check SL hit (low touched SL)
                        if low <= trade['sl_price']:
                            return False, True, trade['sl_price'], candle_time
            
            return False, False, None, None
            
        except Exception as e:
            print(f"⚠️ Error checking historical prices: {e}")
            return False, False, None, None
    
    def get_status_summary(self) -> Dict:
        """Get summary of all trades"""
        total_trades = len(self.open_trades) + len(self.closed_trades)
        wins = sum(1 for t in self.closed_trades if t['outcome'] == 'WIN')
        losses = sum(1 for t in self.closed_trades if t['outcome'] == 'LOSS')
        total_pnl = sum(t.get('pnl_usd', 0) for t in self.closed_trades)
        
        return {
            'total_trades': total_trades,
            'open_trades': len(self.open_trades),
            'closed_trades': len(self.closed_trades),
            'wins': wins,
            'losses': losses,
            'win_rate': wins / len(self.closed_trades) if self.closed_trades else 0,
            'total_pnl': total_pnl
        }
    
    def display_status(self):
        """Display current trade status"""
        summary = self.get_status_summary()
        
        print(f"\n📊 TRADE MONITOR STATUS:")
        print(f"   Total Trades: {summary['total_trades']}")
        print(f"   Open: {summary['open_trades']}")
        print(f"   Closed: {summary['closed_trades']}")
        
        if summary['closed_trades'] > 0:
            print(f"   Wins: {summary['wins']}")
            print(f"   Losses: {summary['losses']}")
            print(f"   Win Rate: {summary['win_rate']:.1%}")
            print(f"   Total P&L: ${summary['total_pnl']:.2f}")
        
        if self.open_trades:
            print(f"\n   📋 Open Trades:")
            for trade in self.open_trades:
                print(f"      • {trade['model']}: Entry ${trade['entry_price']:,.2f}, TP ${trade['tp_price']:,.2f}, SL ${trade['sl_price']:,.2f}")

# Singleton instance
_monitor = None

def get_monitor(logger):
    """Get the global trade exit monitor"""
    global _monitor
    if _monitor is None:
        _monitor = TradeExitMonitor(logger)
    return _monitor
