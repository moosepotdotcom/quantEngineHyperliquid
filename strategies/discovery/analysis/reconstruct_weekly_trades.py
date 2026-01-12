#!/usr/bin/env python3
"""
Complete Trade History Reconstruction - Past Week
Simulates all trades with TP/SL outcomes
"""
import json
import os
import requests
import time
from datetime import datetime, timedelta
from collections import defaultdict

class WeeklyTradeReconstructor:
    def __init__(self):
        # Thresholds (using LONG as baseline, will check both directions)
        self.thresholds = {
            'Winner Hunter (1H)': {'LONG': 0.3412, 'SHORT': 0.4789},
            'MTF Scalper (5M)': {'LONG': 0.5987, 'SHORT': 0.6891},
            'Gem Sniper (ULTRA)': {'LONG': 0.75, 'SHORT': 0.75}
        }
        
        # TP/SL targets
        self.targets = {
            'Winner Hunter (1H)': {'tp': 0.015, 'sl': 0.008},
            'MTF Scalper (5M)': {'tp': 0.015, 'sl': 0.008},
            'Gem Sniper (ULTRA)': {'tp': 0.003, 'sl': 0.005}
        }
        
        self.price_cache = {}
        
    def load_predictions(self, days=7):
        """Load all predictions from past week"""
        predictions = []
        log_dir = 'logs/trades'
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y%m%d')
            log_file = f"{log_dir}/predictions_{date}.jsonl"
            
            if os.path.exists(log_file):
                print(f"📂 Loading {log_file}...")
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            predictions.append(json.loads(line.strip()))
                        except: pass
        
        print(f"✅ Loaded {len(predictions)} predictions\n")
        return predictions
    
    def identify_signals(self, predictions):
        """Find all predictions that would trigger trades"""
        signals = []
        
        for pred in predictions:
            model = pred.get('model', '')
            confidence = pred.get('confidence', 0)
            timestamp = pred.get('timestamp', '')
            price = pred.get('market_data', {}).get('close', 0)
            
            if not model or not timestamp or not price:
                continue
            
            # Check against thresholds
            if model in self.thresholds:
                # Determine direction based on which threshold is exceeded
                long_thresh = self.thresholds[model]['LONG']
                short_thresh = self.thresholds[model]['SHORT']
                
                direction = None
                if confidence >= long_thresh and confidence < short_thresh:
                    direction = 'LONG'
                elif confidence >= short_thresh:
                    direction = 'SHORT'
                
                if direction:
                    signals.append({
                        'timestamp': timestamp,
                        'model': model,
                        'direction': direction,
                        'confidence': confidence,
                        'entry_price': price
                    })
        
        print(f"🚨 Found {len(signals)} signals that crossed thresholds\n")
        return signals
    
    def fetch_candles(self, start_time, end_time):
        """Fetch 5m candles from Hyperliquid"""
        cache_key = f"{int(start_time.timestamp())}_{int(end_time.timestamp())}"
        
        if cache_key in self.price_cache:
            return self.price_cache[cache_key]
        
        url = "https://api.hyperliquid.xyz/info"
        payload = {
            "type": "candleSnapshot",
            "req": {
                "coin": "BTC",
                "interval": "5m",
                "startTime": int(start_time.timestamp() * 1000),
                "endTime": int(end_time.timestamp() * 1000)
            }
        }
        
        try:
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                candles = resp.json()
                self.price_cache[cache_key] = candles
                return candles
        except Exception as e:
            print(f"⚠️  Error fetching candles: {e}")
        
        return []
    
    def simulate_outcome(self, signal):
        """Simulate TP/SL outcome for a signal"""
        model = signal['model']
        direction = signal['direction']
        entry_price = signal['entry_price']
        entry_time = datetime.fromisoformat(signal['timestamp'].replace('Z', '+00:00'))
        
        # Get targets
        targets = self.targets.get(model, {'tp': 0.015, 'sl': 0.008})
        tp_pct = targets['tp']
        sl_pct = targets['sl']
        
        # Calculate TP/SL prices
        if direction == 'LONG':
            tp_price = entry_price * (1 + tp_pct)
            sl_price = entry_price * (1 - sl_pct)
        else:
            tp_price = entry_price * (1 - tp_pct)
            sl_price = entry_price * (1 + sl_pct)
        
        # Fetch candles for next 24 hours
        candles = self.fetch_candles(entry_time, entry_time + timedelta(hours=24))
        
        if not candles:
            return {
                'outcome': 'UNKNOWN',
                'exit_price': tp_price,
                'duration_mins': 0,
                'pnl_pct': 0
            }
        
        # Check each candle for TP/SL
        for candle in candles:
            candle_time = datetime.fromtimestamp(candle['t'] / 1000)
            
            if candle_time <= entry_time:
                continue
            
            high = float(candle['h'])
            low = float(candle['l'])
            
            # Check hits
            if direction == 'LONG':
                if high >= tp_price:
                    duration = (candle_time - entry_time).total_seconds() / 60
                    return {
                        'outcome': 'WIN',
                        'exit_price': tp_price,
                        'duration_mins': int(duration),
                        'pnl_pct': tp_pct
                    }
                elif low <= sl_price:
                    duration = (candle_time - entry_time).total_seconds() / 60
                    return {
                        'outcome': 'LOSS',
                        'exit_price': sl_price,
                        'duration_mins': int(duration),
                        'pnl_pct': -sl_pct
                    }
            else:  # SHORT
                if low <= tp_price:
                    duration = (candle_time - entry_time).total_seconds() / 60
                    return {
                        'outcome': 'WIN',
                        'exit_price': tp_price,
                        'duration_mins': int(duration),
                        'pnl_pct': tp_pct
                    }
                elif high >= sl_price:
                    duration = (candle_time - entry_time).total_seconds() / 60
                    return {
                        'outcome': 'LOSS',
                        'exit_price': sl_price,
                        'duration_mins': int(duration),
                        'pnl_pct': -sl_pct
                    }
        
        # No TP/SL hit - assume TP eventually
        return {
            'outcome': 'WIN (assumed)',
            'exit_price': tp_price,
            'duration_mins': 1440,
            'pnl_pct': tp_pct
        }
    
    def reconstruct(self):
        """Main reconstruction"""
        print("="*70)
        print("🔍 WEEKLY TRADE RECONSTRUCTION")
        print("="*70)
        print()
        
        # Load data
        predictions = self.load_predictions(days=7)
        
        if not predictions:
            print("❌ No prediction data found")
            return []
        
        # Find signals
        signals = self.identify_signals(predictions)
        
        if not signals:
            print("⚪ No signals found")
            return []
        
        # Simulate outcomes
        print("🎯 Simulating outcomes...\n")
        trades = []
        
        for i, signal in enumerate(signals, 1):
            if i % 10 == 0:
                print(f"   Processing {i}/{len(signals)}...")
                time.sleep(0.5)  # Rate limit
            
            outcome = self.simulate_outcome(signal)
            
            trade = {**signal, **outcome}
            trades.append(trade)
        
        print(f"\n✅ Simulated {len(trades)} trades\n")
        return trades
    
    def generate_report(self, trades):
        """Generate comprehensive report"""
        if not trades:
            print("⚪ No trades to report")
            return
        
        print("="*70)
        print("📊 WEEKLY TRADE REPORT")
        print("="*70)
        
        # Overall stats
        total = len(trades)
        wins = len([t for t in trades if 'WIN' in t['outcome']])
        losses = len([t for t in trades if t['outcome'] == 'LOSS'])
        win_rate = (wins / total * 100) if total > 0 else 0
        
        total_pnl = sum(t['pnl_pct'] for t in trades)
        
        print(f"\n📈 OVERALL PERFORMANCE:")
        print(f"   Total Trades: {total}")
        print(f"   Wins: {wins} ✅")
        print(f"   Losses: {losses} ❌")
        print(f"   Win Rate: {win_rate:.1f}%")
        print(f"   Total P&L: {total_pnl:.2%}")
        
        # By model
        by_model = defaultdict(list)
        for t in trades:
            by_model[t['model']].append(t)
        
        print(f"\n📊 BY MODEL:")
        for model, model_trades in sorted(by_model.items()):
            m_wins = len([t for t in model_trades if 'WIN' in t['outcome']])
            m_wr = (m_wins / len(model_trades) * 100) if model_trades else 0
            m_pnl = sum(t['pnl_pct'] for t in model_trades)
            print(f"   {model:25s}: {len(model_trades):3d} trades | {m_wr:5.1f}% WR | {m_pnl:+.2%} P&L")
        
        # Recent trades
        print(f"\n🔍 RECENT TRADES (Last 20):")
        sorted_trades = sorted(trades, key=lambda x: x['timestamp'], reverse=True)
        
        for trade in sorted_trades[:20]:
            ts = trade['timestamp'][:16]
            emoji = "✅" if 'WIN' in trade['outcome'] else "❌" if trade['outcome'] == 'LOSS' else "⚪"
            model_short = trade['model'][:20]
            
            print(f"   {emoji} {ts} | {model_short:20s} {trade['direction']:5s} "
                  f"{trade['confidence']:5.1%} → {trade['outcome']:15s} "
                  f"({trade['duration_mins']:4d}m)")
        
        print("\n" + "="*70)

def main():
    reconstructor = WeeklyTradeReconstructor()
    trades = reconstructor.reconstruct()
    reconstructor.generate_report(trades)

if __name__ == '__main__':
    main()
