#!/usr/bin/env python3
"""
Backtest Optimized Engine Configuration
Tests new thresholds (50%/65%) + trend filter on historical data
"""
import json
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from utils.trend_filter import get_market_regime, should_trade, get_regime_info

# Configuration
NEW_THRESHOLDS = {
    'Winner Hunter (1H)': {'LONG': 0.5000, 'SHORT': 0.4789},
    'MTF Scalper (5M)': {'LONG': 0.6500, 'SHORT': 0.6891}
}

OLD_THRESHOLDS = {
    'Winner Hunter (1H)': {'LONG': 0.3412, 'SHORT': 0.4789},
    'MTF Scalper (5M)': {'LONG': 0.4500, 'SHORT': 0.6891}
}

# TP/SL parameters
TP_PCT = 0.015  # 1.5%
SL_PCT = 0.008  # 0.8%

def get_historical_candles(start_time, end_time):
    """Get 1-minute BTC candles for outcome simulation"""
    url = "https://api.hyperliquid.xyz/info"
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": "BTC",
            "interval": "1m",
            "startTime": int(start_time.timestamp() * 1000),
            "endTime": int(end_time.timestamp() * 1000)
        }
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        if data:
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
            df['close'] = df['c'].astype(float)
            df['high'] = df['h'].astype(float)
            df['low'] = df['l'].astype(float)
            return df
        return None
    except:
        return None

def simulate_outcome(entry_price, direction, entry_time):
    """Simulate if TP or SL would have been hit"""
    end_time = entry_time + timedelta(hours=48)
    candles = get_historical_candles(entry_time, end_time)
    
    if candles is None or len(candles) == 0:
        return "UNCONFIRMED", 0.0, None
    
    if direction == "LONG":
        tp_target = entry_price * (1 + TP_PCT)
        sl_target = entry_price * (1 - SL_PCT)
    else:
        tp_target = entry_price * (1 - TP_PCT)
        sl_target = entry_price * (1 + SL_PCT)
    
    for _, candle in candles.iterrows():
        high = candle['high']
        low = candle['low']
        
        if direction == "LONG":
            if high >= tp_target:
                return "WIN", TP_PCT * 100, candle['timestamp']
            if low <= sl_target:
                return "LOSS", -SL_PCT * 100, candle['timestamp']
        else:
            if low <= tp_target:
                return "WIN", TP_PCT * 100, candle['timestamp']
            if high >= sl_target:
                return "LOSS", -SL_PCT * 100, candle['timestamp']
    
    # Still open
    current_price = candles.iloc[-1]['close']
    if direction == "LONG":
        pnl = (current_price - entry_price) / entry_price * 100
    else:
        pnl = (entry_price - current_price) / entry_price * 100
    
    return "OPEN", pnl, None

def load_predictions(date_str):
    """Load predictions for a given date"""
    try:
        with open(f'logs/trades/predictions_{date_str}.jsonl', 'r') as f:
            return [json.loads(line) for line in f]
    except:
        return []

def backtest_configuration(predictions, thresholds, use_trend_filter=False):
    """Backtest a specific configuration"""
    trades = []
    
    for pred in predictions:
        model = pred.get('model', '')
        conf = pred.get('confidence', 0)
        price = pred.get('market_data', {}).get('close', 0)
        timestamp = pred.get('timestamp', '')
        
        if not price or price == 0 or model not in thresholds:
            continue
        
        # Determine direction
        if conf >= thresholds[model]['SHORT']:
            direction = 'SHORT'
            threshold = thresholds[model]['SHORT']
        elif conf >= thresholds[model]['LONG']:
            direction = 'LONG'
            threshold = thresholds[model]['LONG']
        else:
            continue  # Below threshold
        
        # Apply trend filter if enabled
        if use_trend_filter:
            # Get 1h data for regime detection
            entry_time = datetime.fromisoformat(timestamp)
            regime_start = entry_time - timedelta(hours=100)
            df_1h = get_historical_candles(regime_start, entry_time)
            
            if df_1h is not None and len(df_1h) >= 50:
                # Resample to 1h
                df_1h_resampled = df_1h.set_index('timestamp').resample('1H').agg({
                    'close': 'last',
                    'high': 'max',
                    'low': 'min'
                }).dropna()
                
                if len(df_1h_resampled) >= 50:
                    regime = get_market_regime(df_1h_resampled)
                    can_trade, reason = should_trade(direction, regime)
                    
                    if not can_trade:
                        continue  # Blocked by trend filter
        
        # Simulate trade outcome
        entry_time = datetime.fromisoformat(timestamp)
        outcome, pnl, exit_time = simulate_outcome(price, direction, entry_time)
        
        trades.append({
            'model': model,
            'timestamp': timestamp,
            'direction': direction,
            'confidence': conf,
            'threshold': threshold,
            'entry_price': price,
            'outcome': outcome,
            'pnl': pnl,
            'exit_time': exit_time
        })
    
    return trades

def print_results(trades, config_name):
    """Print backtest results"""
    if not trades:
        print(f"\n❌ {config_name}: No trades")
        return
    
    wins = [t for t in trades if t['outcome'] == 'WIN']
    losses = [t for t in trades if t['outcome'] == 'LOSS']
    opens = [t for t in trades if t['outcome'] == 'OPEN']
    
    total_pnl = sum(t['pnl'] for t in trades)
    win_rate = len(wins) / (len(wins) + len(losses)) * 100 if (len(wins) + len(losses)) > 0 else 0
    
    print(f"\n{'='*70}")
    print(f"📊 {config_name}")
    print(f"{'='*70}")
    print(f"Total Trades: {len(trades)}")
    print(f"  Wins: {len(wins)} ✅")
    print(f"  Losses: {len(losses)} ❌")
    print(f"  Open: {len(opens)} 🟡")
    print(f"\nWin Rate: {win_rate:.1f}%")
    print(f"Total P&L: {total_pnl:+.2f}%")
    print(f"Avg P&L per trade: {total_pnl/len(trades):+.2f}%")
    
    # Show sample trades
    print(f"\n📋 Sample Trades (first 5):")
    for i, trade in enumerate(trades[:5], 1):
        emoji = "✅" if trade['outcome'] == 'WIN' else "❌" if trade['outcome'] == 'LOSS' else "🟡"
        print(f"{i}. {emoji} {trade['model']} {trade['direction']}")
        print(f"   {trade['timestamp'][:19]} | Conf: {trade['confidence']:.2%}")
        print(f"   Entry: ${trade['entry_price']:,.2f} | {trade['outcome']} ({trade['pnl']:+.2f}%)")

# Main execution
print("="*70)
print("🔬 BACKTEST: Optimized Engine Configuration")
print("="*70)
print("\nTesting Period: Last 7 days")
print("Configurations:")
print("  1. OLD: 34.12%/45% thresholds, NO trend filter")
print("  2. NEW (Phase 1): 50%/65% thresholds, NO trend filter")
print("  3. NEW (Phase 1+2): 50%/65% thresholds + TREND FILTER")

# Load predictions from last 7 days
all_predictions = []
for i in range(7):
    date = (datetime.now() - timedelta(days=i)).strftime('%Y%m%d')
    preds = load_predictions(date)
    all_predictions.extend(preds)
    print(f"  Loaded {len(preds)} predictions from {date}")

print(f"\nTotal predictions: {len(all_predictions)}")

# Run backtests
print("\n" + "="*70)
print("Running backtests...")
print("="*70)

print("\n⏳ Backtesting OLD configuration...")
old_trades = backtest_configuration(all_predictions, OLD_THRESHOLDS, use_trend_filter=False)
print_results(old_trades, "OLD CONFIG (34.12%/45%, No Filter)")

print("\n⏳ Backtesting NEW Phase 1...")
new_phase1_trades = backtest_configuration(all_predictions, NEW_THRESHOLDS, use_trend_filter=False)
print_results(new_phase1_trades, "NEW PHASE 1 (50%/65%, No Filter)")

print("\n⏳ Backtesting NEW Phase 1+2...")
new_phase2_trades = backtest_configuration(all_predictions, NEW_THRESHOLDS, use_trend_filter=True)
print_results(new_phase2_trades, "NEW PHASE 1+2 (50%/65% + Trend Filter)")

# Comparison
print(f"\n{'='*70}")
print("📈 COMPARISON SUMMARY")
print(f"{'='*70}")
print(f"{'Config':<30} {'Trades':<10} {'Win Rate':<12} {'Total P&L':<12}")
print(f"{'-'*70}")

for name, trades in [
    ("OLD (34.12%/45%)", old_trades),
    ("NEW Phase 1 (50%/65%)", new_phase1_trades),
    ("NEW Phase 1+2 (+ Filter)", new_phase2_trades)
]:
    if trades:
        wins = len([t for t in trades if t['outcome'] == 'WIN'])
        losses = len([t for t in trades if t['outcome'] == 'LOSS'])
        wr = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
        pnl = sum(t['pnl'] for t in trades)
        print(f"{name:<30} {len(trades):<10} {wr:>6.1f}%{'':<5} {pnl:>+8.2f}%")
    else:
        print(f"{name:<30} {'0':<10} {'N/A':<12} {'N/A':<12}")

print(f"\n{'='*70}")
print("✅ Backtest complete!")
print(f"{'='*70}")
