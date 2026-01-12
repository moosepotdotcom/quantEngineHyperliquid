#!/usr/bin/env python3
"""
📝 Trade Logger & Position Monitor
Comprehensive logging and monitoring of all trades.
"""

import os
import json
from datetime import datetime

class TradeLogger:
    """Logs all trade activity with full details"""
    
    def __init__(self, log_dir='logs'):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.log_file = os.path.join(log_dir, f'trades_{datetime.now().strftime("%Y%m%d")}.json')
        self.trades = []
        
    def log_entry(self, signal):
        """Log trade entry"""
        
        # Calculate targets
        tp_pct = 0.015  # 1.5%
        sl_pct = 0.008  # 0.8%
        
        entry_price = signal['price']
        tp_price = entry_price * (1 + tp_pct)
        sl_price = entry_price * (1 - sl_pct)
        
        trade = {
            'trade_id': f"T{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'model': signal['model'],
            'status': 'OPEN',
            'entry': {
                'timestamp': signal['timestamp'].isoformat(),
                'price': entry_price,
                'confidence': signal['confidence'],
                'rsi': signal['rsi'],
                'macd': signal['macd'],
                'atr_pct': signal['atr_pct']
            },
            'targets': {
                'take_profit': tp_price,
                'stop_loss': sl_price,
                'tp_pct': tp_pct,
                'sl_pct': sl_pct,
                'risk_reward': tp_pct / sl_pct
            },
            'exit': None,
            'pnl': None
        }
        
        self.trades.append(trade)
        self._save()
        
        # Print detailed log
        print("\n" + "="*70)
        print("📝 TRADE LOGGED - ENTRY")
        print("="*70)
        print(f"   🆔 Trade ID: {trade['trade_id']}")
        print(f"   🤖 Model: {trade['model']}")
        print(f"   ⏰ Entry Time: {signal['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   💰 Entry Price: ${entry_price:,.2f}")
        print(f"   📊 Confidence: {signal['confidence']:.2%}")
        print(f"\n   🎯 TARGETS:")
        print(f"      ✅ Take Profit: ${tp_price:,.2f} (+{tp_pct*100:.1f}%)")
        print(f"      ❌ Stop Loss: ${sl_price:,.2f} (-{sl_pct*100:.1f}%)")
        print(f"      💵 Risk/Reward: 1:{tp_pct/sl_pct:.2f}")
        print(f"\n   📊 INDICATORS:")
        print(f"      RSI(14): {signal['rsi']:.1f}")
        print(f"      MACD Hist: {signal['macd']:.2f}")
        print(f"      ATR%: {signal['atr_pct']:.3f}%")
        print("="*70)
        
        return trade
    
    def log_exit(self, trade_id, exit_price, exit_reason):
        """Log trade exit"""
        
        for trade in self.trades:
            if trade['trade_id'] == trade_id and trade['status'] == 'OPEN':
                entry_price = trade['entry']['price']
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                pnl_dollars = exit_price - entry_price
                
                trade['status'] = 'CLOSED'
                trade['exit'] = {
                    'timestamp': datetime.now().isoformat(),
                    'price': exit_price,
                    'reason': exit_reason
                }
                trade['pnl'] = {
                    'dollars': pnl_dollars,
                    'percent': pnl_pct,
                    'result': 'WIN' if pnl_dollars > 0 else 'LOSS'
                }
                
                self._save()
                
                # Print exit log
                result_emoji = "✅" if pnl_dollars > 0 else "❌"
                print("\n" + "="*70)
                print(f"📝 TRADE LOGGED - EXIT {result_emoji}")
                print("="*70)
                print(f"   🆔 Trade ID: {trade_id}")
                print(f"   ⏰ Exit Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   💰 Exit Price: ${exit_price:,.2f}")
                print(f"   📊 Exit Reason: {exit_reason}")
                print(f"\n   💵 PROFIT/LOSS:")
                print(f"      {result_emoji} Result: {trade['pnl']['result']}")
                print(f"      💰 PnL: ${pnl_dollars:,.2f} ({pnl_pct:+.2f}%)")
                print(f"      📈 Entry: ${entry_price:,.2f}")
                print(f"      📉 Exit: ${exit_price:,.2f}")
                print("="*70)
                
                return trade
        
        return None
    
    def _save(self):
        """Save trades to file"""
        with open(self.log_file, 'w') as f:
            json.dump(self.trades, f, indent=2)
    
    def get_open_trades(self):
        """Get all open trades"""
        return [t for t in self.trades if t['status'] == 'OPEN']
    
    def get_summary(self):
        """Get trading summary"""
        closed = [t for t in self.trades if t['status'] == 'CLOSED']
        
        if not closed:
            return None
        
        wins = [t for t in closed if t['pnl']['result'] == 'WIN']
        losses = [t for t in closed if t['pnl']['result'] == 'LOSS']
        
        total_pnl = sum([t['pnl']['dollars'] for t in closed])
        win_rate = len(wins) / len(closed) if closed else 0
        
        return {
            'total_trades': len(closed),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_win': np.mean([t['pnl']['dollars'] for t in wins]) if wins else 0,
            'avg_loss': np.mean([t['pnl']['dollars'] for t in losses]) if losses else 0
        }

class PositionMonitor:
    """Monitors open positions and checks for exits"""
    
    def __init__(self, logger):
        self.logger = logger
        
    def check_exits(self, current_price):
        """Check if any open positions should exit"""
        
        open_trades = self.logger.get_open_trades()
        
        for trade in open_trades:
            tp = trade['targets']['take_profit']
            sl = trade['targets']['stop_loss']
            
            # Check TP
            if current_price >= tp:
                print(f"\n🎯 Take Profit Hit! Trade {trade['trade_id']}")
                self.logger.log_exit(trade['trade_id'], tp, 'TAKE_PROFIT')
                return True
            
            # Check SL
            if current_price <= sl:
                print(f"\n❌ Stop Loss Hit! Trade {trade['trade_id']}")
                self.logger.log_exit(trade['trade_id'], sl, 'STOP_LOSS')
                return True
        
        return False
    
    def show_status(self, current_price):
        """Show status of open positions"""
        
        open_trades = self.logger.get_open_trades()
        
        if not open_trades:
            return
        
        print(f"\n📊 OPEN POSITIONS ({len(open_trades)}):")
        print("-" * 70)
        
        for trade in open_trades:
            entry = trade['entry']['price']
            tp = trade['targets']['take_profit']
            sl = trade['targets']['stop_loss']
            
            unrealized_pnl = current_price - entry
            unrealized_pct = (unrealized_pnl / entry) * 100
            
            # Distance to targets
            dist_to_tp = ((tp - current_price) / current_price) * 100
            dist_to_sl = ((current_price - sl) / current_price) * 100
            
            pnl_emoji = "🟢" if unrealized_pnl > 0 else "🔴"
            
            print(f"\n   🆔 {trade['trade_id']}")
            print(f"   💰 Entry: ${entry:,.2f} | Current: ${current_price:,.2f}")
            print(f"   {pnl_emoji} Unrealized PnL: ${unrealized_pnl:,.2f} ({unrealized_pct:+.2f}%)")
            print(f"   🎯 TP: ${tp:,.2f} ({dist_to_tp:+.2f}% away)")
            print(f"   ❌ SL: ${sl:,.2f} ({dist_to_sl:+.2f}% away)")

if __name__ == '__main__':
    # Test logging
    import numpy as np
    
    logger = TradeLogger()
    
    # Simulate entry
    signal = {
        'model': 'Winner Hunter (1H)',
        'timestamp': datetime.now(),
        'price': 87650.00,
        'confidence': 0.96,
        'rsi': 55.2,
        'macd': 35.5,
        'atr_pct': 0.45
    }
    
    trade = logger.log_entry(signal)
    
    # Simulate monitoring
    monitor = PositionMonitor(logger)
    monitor.show_status(87750.00)  # Price moved up
    
    # Simulate TP hit
    monitor.check_exits(88965.00)  # TP hit
    
    print("\n✅ Trade logging test complete!")
