#!/usr/bin/env python3
"""
🔴 LIVE SANDBOX - Real-Time Model Testing
Streams live data from Binance and tests both models in real-time.
"""

import os
import sys
import pandas as pd
import numpy as np
import xgboost as xgb
import requests
import time
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Add parent to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')

class LiveDataStream:
    """Fetches live OHLCV data from Binance"""
    
    def __init__(self, symbol='BTCUSDT', interval='5m'):
        self.symbol = symbol
        self.interval = interval
        self.url = 'https://api.binance.com/api/v3/klines'
        
    def fetch_latest(self, limit=100):
        """Fetch latest candles"""
        params = {
            'symbol': self.symbol,
            'interval': self.interval,
            'limit': limit
        }
        
        try:
            resp = requests.get(self.url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            df = df.astype({
                'open': float, 'high': float, 'low': float,
                'close': float, 'volume': float
            })
            
            return df
        except Exception as e:
            print(f"❌ Fetch Error: {e}")
            return None

class LiveModelTester:
    """Tests models with live data"""
    
    def __init__(self, model_name, threshold=0.95):
        self.model_name = model_name
        self.threshold = threshold
        self.model = xgb.XGBClassifier()
        
        model_path = os.path.join(MODEL_DIR, f'{model_name}.json')
        if os.path.exists(model_path):
            self.model.load_model(model_path)
            print(f"✅ Loaded: {model_name}")
        else:
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        self.signals = []
        self.last_signal_time = None
        
    def add_features(self, df):
        """Add ALL technical indicators to match training"""
        # Import feature engineering from utils
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'utils'))
        from feature_engineer import add_all_indicators
        
        try:
            df = add_all_indicators(df)
            return df
        except Exception as e:
            print(f"⚠️ Feature Engineering Error: {e}")
            return df
    
    def predict(self, df):
        """Generate prediction on latest bar"""
        df = self.add_features(df)
        
        if len(df) == 0:
            return None, 0.0
        
        # Get latest row
        latest = df.iloc[-1]
        
        # Extract features (match training)
        exclude = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        feature_cols = [c for c in df.columns if c not in exclude]
        
        try:
            X = latest[feature_cols].values.reshape(1, -1)
            prob = self.model.predict_proba(X)[0][1]
            signal = 1 if prob >= self.threshold else 0
            
            return signal, prob
        except Exception as e:
            print(f"⚠️ Prediction Error: {e}")
            return None, 0.0
    
    def log_signal(self, timestamp, price, signal, prob):
        """Log trading signal"""
        self.signals.append({
            'timestamp': timestamp,
            'price': price,
            'signal': signal,
            'confidence': prob
        })
        self.last_signal_time = timestamp

def run_sandbox(duration_minutes=30):
    """Run live sandbox test"""
    
    print("="*60)
    print("🔴 LIVE SANDBOX MODE - REAL-TIME TESTING")
    print("="*60)
    
    # Initialize models
    print("\n📦 Loading Models...")
    scalper = LiveModelTester('mtf_scalper_5m', threshold=0.95)
    winner = LiveModelTester('winner_hunter_1h', threshold=0.95)
    
    # Initialize data streams
    stream_5m = LiveDataStream('BTCUSDT', '5m')
    stream_1h = LiveDataStream('BTCUSDT', '1h')
    
    print(f"\n⏱️ Running for {duration_minutes} minutes...")
    print("🔴 LIVE | Press Ctrl+C to stop\n")
    
    start_time = datetime.now()
    iteration = 0
    
    try:
        while (datetime.now() - start_time).seconds < duration_minutes * 60:
            iteration += 1
            current_time = datetime.now().strftime("%H:%M:%S")
            
            print(f"\n{'='*60}")
            print(f"⏰ {current_time} | Iteration {iteration}")
            print(f"{'='*60}")
            
            # Test 5m Scalper
            print("\n⚡ MTF Scalper (5m):")
            df_5m = stream_5m.fetch_latest(limit=100)
            if df_5m is not None:
                signal, prob = scalper.predict(df_5m)
                latest_price = df_5m['close'].iloc[-1]
                
                if signal == 1:
                    print(f"   🚨 SIGNAL! Price: ${latest_price:,.2f} | Confidence: {prob:.2%}")
                    scalper.log_signal(datetime.now(), latest_price, signal, prob)
                else:
                    print(f"   ⚪ No Signal | Price: ${latest_price:,.2f} | Confidence: {prob:.2%}")
            
            # Test 1H Winner Hunter
            print("\n🏆 Winner Hunter (1h):")
            df_1h = stream_1h.fetch_latest(limit=100)
            if df_1h is not None:
                signal, prob = winner.predict(df_1h)
                latest_price = df_1h['close'].iloc[-1]
                
                if signal == 1:
                    print(f"   🚨 SIGNAL! Price: ${latest_price:,.2f} | Confidence: {prob:.2%}")
                    winner.log_signal(datetime.now(), latest_price, signal, prob)
                else:
                    print(f"   ⚪ No Signal | Price: ${latest_price:,.2f} | Confidence: {prob:.2%}")
            
            # Summary
            print(f"\n📊 Session Stats:")
            print(f"   Scalper Signals: {len(scalper.signals)}")
            print(f"   Winner Signals: {len(winner.signals)}")
            print(f"   Runtime: {(datetime.now() - start_time).seconds}s")
            
            # Wait before next iteration (5 minutes for 5m candles)
            print(f"\n⏳ Waiting 5 minutes for next candle...")
            time.sleep(300)  # 5 minutes
            
    except KeyboardInterrupt:
        print("\n\n🛑 Sandbox stopped by user")
    
    # Final Report
    print("\n" + "="*60)
    print("📋 SANDBOX REPORT")
    print("="*60)
    
    print(f"\n⚡ MTF Scalper (5m):")
    print(f"   Total Signals: {len(scalper.signals)}")
    if scalper.signals:
        signals_df = pd.DataFrame(scalper.signals)
        print(f"   Avg Confidence: {signals_df['confidence'].mean():.2%}")
        print(f"   Latest Signal: {signals_df.iloc[-1]['timestamp']}")
    
    print(f"\n🏆 Winner Hunter (1h):")
    print(f"   Total Signals: {len(winner.signals)}")
    if winner.signals:
        signals_df = pd.DataFrame(winner.signals)
        print(f"   Avg Confidence: {signals_df['confidence'].mean():.2%}")
        print(f"   Latest Signal: {signals_df.iloc[-1]['timestamp']}")
    
    print("\n✅ Sandbox test complete!")

if __name__ == '__main__':
    # Quick test (5 minutes for demo)
    run_sandbox(duration_minutes=5)
