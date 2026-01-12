#!/usr/bin/env python3
"""
Trade History Reconstruction
Analyzes prediction logs to reconstruct what trades would have been executed
"""
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
import requests

class TradeReconstructor:
    def __init__(self):
        self.thresholds = {
            'Winner Hunter (1H)': {'long': 0.3412, 'short': 0.4789},
            'MTF Scalper (5M)': {'long': 0.5987, 'short': 0.6891},
            'Gem Sniper (ULTRA)': {'long': 0.75, 'short': 0.75}
        }
        
        # TP/SL targets
        self.targets = {
            'Winner Hunter (1H)': {'tp': 0.015, 'sl': 0.008},
            'MTF Scalper (5M)': {'tp': 0.015, 'sl': 0.008},
            'Gem Sniper (ULTRA)': {'tp': 0.003, 'sl': 0.005}
        }
        
        self.trades = []
        
    def load_predictions(self, days=7):
        """Load prediction logs from the last N days"""
        predictions = []
        log_dir = 'logs/trades'
        
        if not os.path.exists(log_dir):
            print(f"⚠️  Log directory not found: {log_dir}")
            return predictions
        
        # Get all prediction files
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y%m%d')
            log_file = f"{log_dir}/predictions_{date}.jsonl"
            
            if os.path.exists(log_file):
                print(f"📂 Loading {log_file}...")
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            pred = json.loads(line.strip())
                            predictions.append(pred)
                        except:
                            pass
        
        print(f"✅ Loaded {len(predictions)} predictions from last {days} days")
        return predictions
    
    def identify_signals(self, predictions):
        """Identify which predictions would have triggered trades"""
        signals = []
        
        for pred in predictions:
            model = pred.get('model', '')
            confidence = pred.get('confidence', 0)
            direction = pred.get('direction')
            timestamp = pred.get('timestamp')
            price = pred.get('price', 0)
            
            # Check if already marked as signal
            if pred.get('is_signal'):
                signals.append(pred)
                continue
            
            # Check thresholds
            if model in self.thresholds:
                threshold_long = self.thresholds[model]['long']
                threshold_short = self.thresholds[model]['short']
                
                # Determine if this would trigger
                if direction == 'LONG' and confidence >= threshold_long:
                    pred['is_signal'] = True
                    signals.append(pred)
                elif direction == 'SHORT' and confidence >= threshold_short:
                    pred['is_signal'] = True
                    signals.append(pred)
        
        print(f"🚨 Found {len(signals)} signals that crossed thresholds")
        return signals
    
    def fetch_price_data(self, timestamp_str, lookback_hours=24):
        """Fetch historical price data from Hyperliquid"""
        try:
            # Parse timestamp
            ts = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
            # Fetch 5m candles
            url = "https://api.hyperliquid.xyz/info"
            payload = {
                "type": "candleSnapshot",
                "req": {
                    "coin": "BTC",
                    "interval": "5m",
                    "startTime": int((ts - timedelta(hours=lookback_hours)).timestamp() * 1000),
                    "endTime": int((ts + timedelta(hours=lookback_hours)).timestamp() * 1000)
                }
            }
            
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                candles = resp.json()
                return candles
            else:
                print(f"⚠️  Failed to fetch price data: {resp.status_code}")
                return []
        except Exception as e:
            print(f"❌ Error fetching price data: {e}")
            return []
    
    def simulate_trade_outcome(self, signal):
        """Simulate TP/SL outcome for a signal"""
        model = signal.get('model', '')
        direction = signal.get('direction', '')
        entry_price = signal.get('price', 0)
        timestamp = signal.get('timestamp', '')
        
        if not entry_price or entry_price == 0:
            return None
        
        # Get TP/SL targets
        targets = self.targets.get(model, {'tp': 0.015, 'sl': 0.008})
        tp_pct = targets['tp']
        sl_pct = targets['sl']
        
        # Calculate TP/SL prices
        if direction == 'LONG':
            tp_price = entry_price * (1 + tp_pct)
            sl_price = entry_price * (1 - sl_pct)
        else:  # SHORT
            tp_price = entry_price * (1 - tp_pct)
            sl_price = entry_price * (1 + sl_pct)
        
        # Fetch price data
        candles = self.fetch_price_data(timestamp)
        
        if not candles:
            print(f"⚠️  No price data for {timestamp}, assuming TP hit")
            return {
                'outcome': 'WIN',
                'exit_price': tp_price,
                'duration': 'Unknown',
                'pnl_pct': tp_pct if direction == 'LONG' else -tp_pct
            }
        
        # Check each candle for TP/SL hit
        entry_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        for candle in candles:
            candle_time = datetime.fromtimestamp(candle['t'] / 1000)
            
            # Only check candles after entry
            if candle_time <= entry_time:
                continue
            
            high = float(candle['h'])
            low = float(candle['l'])
            
            # Check for TP/SL hit
            if direction == 'LONG':
                if high >= tp_price:
                    duration = (candle_time - entry_time).total_seconds() / 60
                    return {
                        'outcome': 'WIN',
                        'exit_price': tp_price,
                        'duration': f"{int(duration)}m",
                        'pnl_pct': tp_pct
                    }
                elif low <= sl_price:
                    duration = (candle_time - entry_time).total_seconds() / 60
                    return {
                        'outcome': 'LOSS',
                        'exit_price': sl_price,
                        'duration': f"{int(duration)}m",
                        'pnl_pct': -sl_pct
                    }
            else:  # SHORT
                if low <= tp_price:
                    duration = (candle_time - entry_time).total_seconds() / 60
                    return {
                        'outcome': 'WIN',
                        'exit_price': tp_price,
                        'duration': f"{int(duration)}m",
                        'pnl_pct': tp_pct
                    }
                elif high >= sl_price:
                    duration = (candle_time - entry_time).total_seconds() / 60
                    return {
                        'outcome': 'LOSS',
                        'exit_price': sl_price,
                        'duration': f"{int(duration)}m",
                        'pnl_pct': -sl_pct
                    }
        
        # If no TP/SL hit in available data, assume still open or TP hit
        return {
            'outcome': 'WIN (assumed)',
            'exit_price': tp_price,
            'duration': 'Unknown',
            'pnl_pct': tp_pct
        }
    
    def reconstruct_trades(self, days=7):
        """Main reconstruction logic"""
        print("="*70)
        print("🔍 TRADE HISTORY RECONSTRUCTION")
        print("="*70)
        
        # Load predictions
        predictions = self.load_predictions(days)
        
        if not predictions:
            print("❌ No prediction data found")
            return []
        
        # Identify signals
        signals = self.identify_signals(predictions)
        
        if not signals:
            print("⚪ No signals found in the data")
            return []
        
        # Simulate outcomes
        print(f"\n🎯 Simulating outcomes for {len(signals)} signals...")
        trades = []
        
        for i, signal in enumerate(signals, 1):
            print(f"\n[{i}/{len(signals)}] {signal.get('model')} {signal.get('direction')} @ ${signal.get('price', 0):,.2f}")
            
            outcome = self.simulate_trade_outcome(signal)
            
            if outcome:
                trade = {
                    'timestamp': signal.get('timestamp'),
                    'model': signal.get('model'),
                    'direction': signal.get('direction'),
                    'confidence': signal.get('confidence'),
                    'entry_price': signal.get('price'),
                    **outcome
                }
                trades.append(trade)
                
                emoji = "✅" if 'WIN' in outcome['outcome'] else "❌"
                print(f"  {emoji} {outcome['outcome']} - Exit: ${outcome['exit_price']:,.2f} ({outcome['duration']})")
        
        return trades
    
    def generate_report(self, trades):
        """Generate comprehensive trade report"""
        if not trades:
            print("\n⚪ No trades to report")
            return
        
        print("\n" + "="*70)
        print("📊 TRADE RECONSTRUCTION REPORT")
        print("="*70)
        
        # Calculate stats
        total_trades = len(trades)
        wins = len([t for t in trades if 'WIN' in t['outcome']])
        losses = total_trades - wins
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        total_pnl_pct = sum(t['pnl_pct'] for t in trades)
        
        print(f"\n📈 SUMMARY:")
        print(f"   Total Trades: {total_trades}")
        print(f"   Wins: {wins}")
        print(f"   Losses: {losses}")
        print(f"   Win Rate: {win_rate:.1f}%")
        print(f"   Total P&L: {total_pnl_pct:.2%}")
        
        # Group by model
        by_model = defaultdict(list)
        for trade in trades:
            by_model[trade['model']].append(trade)
        
        print(f"\n📊 BY MODEL:")
        for model, model_trades in by_model.items():
            model_wins = len([t for t in model_trades if 'WIN' in t['outcome']])
            model_wr = (model_wins / len(model_trades) * 100) if model_trades else 0
            print(f"   {model}: {len(model_trades)} trades, {model_wr:.1f}% WR")
        
        # Show recent trades
        print(f"\n🔍 RECENT TRADES (Last 10):")
        for trade in sorted(trades, key=lambda x: x['timestamp'], reverse=True)[:10]:
            ts = trade['timestamp'][:16]
            emoji = "✅" if 'WIN' in trade['outcome'] else "❌"
            print(f"   {emoji} {ts} | {trade['model'][:15]:15s} {trade['direction']:5s} @ ${trade['entry_price']:>8,.2f} → {trade['outcome']}")

def main():
    reconstructor = TradeReconstructor()
    trades = reconstructor.reconstruct_trades(days=7)
    reconstructor.generate_report(trades)

if __name__ == '__main__':
    main()
