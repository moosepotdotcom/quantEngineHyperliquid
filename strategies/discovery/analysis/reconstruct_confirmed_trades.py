#!/usr/bin/env python3
"""
CONFIRMED Trade Reconstruction - Only Resolved Trades
Only counts trades where TP or SL was definitively hit in historical data
"""
import json
import os
import requests
import time
from datetime import datetime, timedelta
from collections import defaultdict

class ConfirmedTradeReconstructor:
    def __init__(self):
        self.thresholds = {
            'Winner Hunter (1H)': {'LONG': 0.3412, 'SHORT': 0.4789},
            'MTF Scalper (5M)': {'LONG': 0.5987, 'SHORT': 0.6891},
            'Gem Sniper (ULTRA)': {'LONG': 0.75, 'SHORT': 0.75}
        }
        
        self.targets = {
            'Winner Hunter (1H)': {'tp': 0.015, 'sl': 0.008},
            'MTF Scalper (5M)': {'tp': 0.015, 'sl': 0.008},
            'Gem Sniper (ULTRA)': {'tp': 0.003, 'sl': 0.005}
        }
        
        self.price_cache = {}
        
    def load_predictions(self, days=7):
        """Load predictions from past week"""
        predictions = []
        log_dir = 'logs/trades'
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y%m%d')
            log_file = f"{log_dir}/predictions_{date}.jsonl"
            
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            predictions.append(json.loads(line.strip()))
                        except: pass
        
        return predictions
    
    def identify_signals(self, predictions):
        """Find signals that crossed thresholds"""
        signals = []
        
        for pred in predictions:
            model = pred.get('model', '')
            confidence = pred.get('confidence', 0)
            timestamp = pred.get('timestamp', '')
            price = pred.get('market_data', {}).get('close', 0)
            
            if not model or not timestamp or not price:
                continue
            
            if model in self.thresholds:
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
        
        return signals
    
    def fetch_candles(self, start_time, end_time):
        """Fetch 5m candles"""
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
        except: pass
        
        return []
    
    def simulate_outcome(self, signal):
        """Simulate outcome - ONLY return if TP/SL definitively hit"""
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
        
        # Fetch candles - look ahead 48 hours
        candles = self.fetch_candles(entry_time, entry_time + timedelta(hours=48))
        
        if not candles:
            return None  # No data = unconfirmed
        
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
                        'pnl_pct': tp_pct,
                        'confirmed': True
                    }
                elif low <= sl_price:
                    duration = (candle_time - entry_time).total_seconds() / 60
                    return {
                        'outcome': 'LOSS',
                        'exit_price': sl_price,
                        'duration_mins': int(duration),
                        'pnl_pct': -sl_pct,
                        'confirmed': True
                    }
            else:  # SHORT
                if low <= tp_price:
                    duration = (candle_time - entry_time).total_seconds() / 60
                    return {
                        'outcome': 'WIN',
                        'exit_price': tp_price,
                        'duration_mins': int(duration),
                        'pnl_pct': tp_pct,
                        'confirmed': True
                    }
                elif high >= sl_price:
                    duration = (candle_time - entry_time).total_seconds() / 60
                    return {
                        'outcome': 'LOSS',
                        'exit_price': sl_price,
                        'duration_mins': int(duration),
                        'pnl_pct': -sl_pct,
                        'confirmed': True
                    }
        
        # No TP/SL hit = unconfirmed
        return None
    
    def reconstruct(self):
        """Main reconstruction - only confirmed trades"""
        print("="*70)
        print("🔍 CONFIRMED TRADE RECONSTRUCTION")
        print("="*70)
        print()
        
        predictions = self.load_predictions(days=7)
        print(f"📂 Loaded {len(predictions)} predictions\n")
        
        if not predictions:
            return []
        
        signals = self.identify_signals(predictions)
        print(f"🚨 Found {len(signals)} signals that crossed thresholds\n")
        
        if not signals:
            return []
        
        print("🎯 Simulating outcomes (CONFIRMED ONLY)...\n")
        confirmed_trades = []
        unconfirmed_count = 0
        
        for i, signal in enumerate(signals, 1):
            if i % 10 == 0:
                print(f"   Processing {i}/{len(signals)}...")
                time.sleep(0.5)
            
            outcome = self.simulate_outcome(signal)
            
            if outcome and outcome.get('confirmed'):
                trade = {**signal, **outcome}
                confirmed_trades.append(trade)
            else:
                unconfirmed_count += 1
        
        print(f"\n✅ Confirmed: {len(confirmed_trades)} trades")
        print(f"⚪ Unconfirmed: {unconfirmed_count} trades (no TP/SL hit yet)\n")
        
        return confirmed_trades
    
    def generate_report(self, trades):
        """Generate report for confirmed trades only"""
        if not trades:
            print("⚪ No confirmed trades found")
            print("   (All signals are still open or data unavailable)")
            return
        
        print("="*70)
        print("📊 CONFIRMED TRADE REPORT (TP/SL Hit Only)")
        print("="*70)
        
        # Stats
        total = len(trades)
        wins = len([t for t in trades if t['outcome'] == 'WIN'])
        losses = len([t for t in trades if t['outcome'] == 'LOSS'])
        win_rate = (wins / total * 100) if total > 0 else 0
        
        total_pnl = sum(t['pnl_pct'] for t in trades)
        avg_duration = sum(t['duration_mins'] for t in trades) / total if total > 0 else 0
        
        print(f"\n📈 OVERALL PERFORMANCE:")
        print(f"   Confirmed Trades: {total}")
        print(f"   Wins: {wins} ✅")
        print(f"   Losses: {losses} ❌")
        print(f"   Win Rate: {win_rate:.1f}%")
        print(f"   Total P&L: {total_pnl:.2%}")
        print(f"   Avg Duration: {avg_duration:.0f} minutes ({avg_duration/60:.1f} hours)")
        
        # By model
        by_model = defaultdict(list)
        for t in trades:
            by_model[t['model']].append(t)
        
        print(f"\n📊 BY MODEL:")
        for model, model_trades in sorted(by_model.items()):
            m_wins = len([t for t in model_trades if t['outcome'] == 'WIN'])
            m_wr = (m_wins / len(model_trades) * 100) if model_trades else 0
            m_pnl = sum(t['pnl_pct'] for t in model_trades)
            m_avg_dur = sum(t['duration_mins'] for t in model_trades) / len(model_trades)
            print(f"   {model:25s}: {len(model_trades):3d} trades | {m_wr:5.1f}% WR | {m_pnl:+.2%} P&L | {m_avg_dur:.0f}m avg")
        
        # By direction
        by_direction = defaultdict(list)
        for t in trades:
            by_direction[t['direction']].append(t)
        
        print(f"\n📊 BY DIRECTION:")
        for direction, dir_trades in sorted(by_direction.items()):
            d_wins = len([t for t in dir_trades if t['outcome'] == 'WIN'])
            d_wr = (d_wins / len(dir_trades) * 100) if dir_trades else 0
            d_pnl = sum(t['pnl_pct'] for t in dir_trades)
            print(f"   {direction:5s}: {len(dir_trades):3d} trades | {d_wr:5.1f}% WR | {d_pnl:+.2%} P&L")
        
        # Recent confirmed trades
        print(f"\n🔍 RECENT CONFIRMED TRADES (Last 20):")
        sorted_trades = sorted(trades, key=lambda x: x['timestamp'], reverse=True)
        
        for trade in sorted_trades[:20]:
            ts = trade['timestamp'][:16]
            emoji = "✅" if trade['outcome'] == 'WIN' else "❌"
            model_short = trade['model'][:20]
            dur_h = trade['duration_mins'] / 60
            
            print(f"   {emoji} {ts} | {model_short:20s} {trade['direction']:5s} "
                  f"{trade['confidence']:5.1%} → {trade['outcome']:4s} "
                  f"({trade['duration_mins']:4d}m / {dur_h:.1f}h)")
        
        print("\n" + "="*70)

def main():
    reconstructor = ConfirmedTradeReconstructor()
    trades = reconstructor.reconstruct()
    reconstructor.generate_report(trades)

if __name__ == '__main__':
    main()
