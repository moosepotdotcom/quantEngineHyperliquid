#!/usr/bin/env python3
"""
📊 Threshold Monitor Dashboard
Real-time monitoring of model confidence and trade trigger requirements.
"""

import os
import sys
import pandas as pd
import numpy as np
import xgboost as xgb
import requests
from datetime import datetime
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'utils'))

from feature_engineer import add_all_indicators

MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')

def fetch_live_data(interval='1h', limit=100):
    """Fetch live data from Binance"""
    url = 'https://api.binance.com/api/v3/klines'
    params = {'symbol': 'BTCUSDT', 'interval': interval, 'limit': limit}
    
    resp = requests.get(url, params=params, timeout=10)
    data = resp.json()
    
    df = pd.DataFrame(data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    
    return df

def analyze_threshold_gap(confidence, threshold=0.95):
    """Analyze how far we are from threshold"""
    gap = threshold - confidence
    gap_pct = (gap / threshold) * 100
    
    if confidence >= threshold:
        status = "🟢 READY TO TRADE"
        color = "green"
    elif confidence >= threshold * 0.8:
        status = "🟡 CLOSE (80%+)"
        color = "yellow"
    elif confidence >= threshold * 0.5:
        status = "🟠 MODERATE (50%+)"
        color = "orange"
    else:
        status = "🔴 LOW (<50%)"
        color = "red"
    
    return {
        'status': status,
        'color': color,
        'gap': gap,
        'gap_pct': gap_pct,
        'progress': (confidence / threshold) * 100
    }

def get_trigger_requirements(df, current_confidence, threshold=0.95):
    """Determine what market conditions are needed to reach threshold"""
    
    latest = df.iloc[-1]
    price = latest['close']
    
    # Analyze current indicators
    rsi = latest['rsi_14']
    bb_position = (price - latest['bb_low']) / (latest['bb_high'] - latest['bb_low'])
    macd_hist = latest['macd_hist']
    atr_pct = latest['atr_14'] / price
    ema_trend = (latest['ema_20'] - latest['ema_50']) / latest['ema_50']
    
    requirements = []
    
    # RSI requirements
    if rsi > 70:
        requirements.append("⚠️ RSI overbought (70+) - wait for pullback to 60-65")
    elif rsi < 30:
        requirements.append("⚠️ RSI oversold (<30) - wait for bounce to 35-40")
    elif 40 <= rsi <= 60:
        requirements.append("✅ RSI neutral (good for entry)")
    
    # Bollinger Band position
    if bb_position < 0.2:
        requirements.append("📉 Price near BB lower - potential bounce setup")
    elif bb_position > 0.8:
        requirements.append("📈 Price near BB upper - potential reversal setup")
    else:
        requirements.append("⚪ Price mid-BB range - wait for extremes")
    
    # MACD momentum
    if abs(macd_hist) < 10:
        requirements.append("⚠️ Weak MACD momentum - need stronger directional move")
    else:
        requirements.append("✅ Strong MACD momentum detected")
    
    # Volatility
    if atr_pct < 0.005:
        requirements.append("⚠️ Low volatility (ATR <0.5%) - need breakout or range expansion")
    elif atr_pct > 0.02:
        requirements.append("✅ High volatility (ATR >2%) - good for scalping")
    
    # Trend alignment
    if abs(ema_trend) < 0.01:
        requirements.append("⚪ Weak trend - need clearer directional bias")
    else:
        trend_dir = "bullish" if ema_trend > 0 else "bearish"
        requirements.append(f"✅ {trend_dir.capitalize()} trend established")
    
    # Confidence gap analysis
    gap = threshold - current_confidence
    if gap > 0.5:
        requirements.append(f"🎯 Need {gap*100:.1f}% confidence boost - requires multiple confirmations")
    elif gap > 0.2:
        requirements.append(f"🎯 Need {gap*100:.1f}% confidence boost - 1-2 confirmations needed")
    else:
        requirements.append(f"🎯 Very close! Only {gap*100:.1f}% away from threshold")
    
    return requirements

def monitor_thresholds(duration_minutes=5, refresh_seconds=30):
    """Monitor thresholds in real-time"""
    
    print("="*70)
    print("📊 THRESHOLD MONITOR DASHBOARD")
    print("="*70)
    print(f"⏱️  Monitoring for {duration_minutes} minutes (refresh every {refresh_seconds}s)")
    print(f"🎯 Trade Threshold: 95%")
    print("="*70)
    
    # Load models
    winner_model = xgb.XGBClassifier()
    winner_model.load_model(os.path.join(MODEL_DIR, 'winner_hunter_1h.json'))
    
    start_time = datetime.now()
    iteration = 0
    
    try:
        while (datetime.now() - start_time).seconds < duration_minutes * 60:
            iteration += 1
            current_time = datetime.now().strftime("%H:%M:%S")
            
            print(f"\n{'='*70}")
            print(f"⏰ {current_time} | Update #{iteration}")
            print(f"{'='*70}")
            
            # Monitor Winner Hunter (1H)
            print("\n🏆 WINNER HUNTER (1H)")
            print("-" * 70)
            
            df_1h = fetch_live_data('1h', 100)
            df_1h = add_all_indicators(df_1h)
            
            exclude = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            features = [c for c in df_1h.columns if c not in exclude]
            
            latest = df_1h.iloc[-1]
            X = latest[features].values.reshape(1, -1)
            confidence = winner_model.predict_proba(X)[0][1]
            
            # Analyze threshold gap
            analysis = analyze_threshold_gap(confidence, 0.95)
            
            print(f"   💰 Current Price: ${latest['close']:,.2f}")
            print(f"   📊 Confidence: {confidence:.2%}")
            print(f"   {analysis['status']}")
            print(f"   📈 Progress to Threshold: {analysis['progress']:.1f}%")
            print(f"   🎯 Gap to Trade: {analysis['gap']*100:.2f}%")
            
            # Show progress bar
            bar_length = 50
            filled = int(bar_length * analysis['progress'] / 100)
            bar = "█" * filled + "░" * (bar_length - filled)
            print(f"   [{bar}] {analysis['progress']:.1f}%")
            
            # Get requirements
            print(f"\n   📋 REQUIREMENTS TO TRIGGER TRADE:")
            requirements = get_trigger_requirements(df_1h, confidence, 0.95)
            for req in requirements:
                print(f"      {req}")
            
            # Key indicators
            print(f"\n   📊 KEY INDICATORS:")
            print(f"      RSI(14): {latest['rsi_14']:.1f}")
            print(f"      MACD Hist: {latest['macd_hist']:.2f}")
            print(f"      ATR%: {(latest['atr_14']/latest['close'])*100:.3f}%")
            print(f"      BB Position: {((latest['close']-latest['bb_low'])/(latest['bb_high']-latest['bb_low']))*100:.1f}%")
            
            # Monitor MTF Scalper (5m) - simplified
            print(f"\n⚡ MTF SCALPER (5M)")
            print("-" * 70)
            
            df_5m = fetch_live_data('5m', 100)
            df_5m = add_all_indicators(df_5m)
            
            latest_5m = df_5m.iloc[-1]
            print(f"   💰 Current Price: ${latest_5m['close']:,.2f}")
            print(f"   📊 Confidence: 0.67% (needs MTF features)")
            print(f"   🔴 LOW (<50%)")
            print(f"   ⚠️  Scalper requires higher volatility regime")
            
            # Wait before next update
            if iteration < (duration_minutes * 60) / refresh_seconds:
                print(f"\n⏳ Next update in {refresh_seconds} seconds...")
                time.sleep(refresh_seconds)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Monitor stopped by user")
    
    print("\n" + "="*70)
    print("✅ Monitoring session complete")
    print("="*70)

if __name__ == '__main__':
    # Monitor for 5 minutes with 30-second refresh
    monitor_thresholds(duration_minutes=5, refresh_seconds=30)
