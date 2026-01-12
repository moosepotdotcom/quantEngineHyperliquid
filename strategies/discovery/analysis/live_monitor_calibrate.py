#!/usr/bin/env python3
"""
Live Feed Monitor with Threshold Calibration
Monitors real-time data and suggests thresholds for ~5 trades/day
"""
import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
import requests
import json
import sys
import os
import time
from datetime import datetime, timedelta
from collections import deque

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))
from feature_engineer import add_all_indicators

class LiveMonitor:
    def __init__(self):
        print("="*70)
        print("🔴 LIVE FEED MONITOR - THRESHOLD CALIBRATION")
        print("="*70)
        
        # Load models
        print("\n📦 Loading Trio Ensemble Models...")
        prefix = 'models/mtf_scalper_5m_trio_'
        
        self.xgb_model = xgb.XGBClassifier()
        self.xgb_model.load_model(f'{prefix}xgb.json')
        
        self.lgb_model = lgb.Booster(model_file=f'{prefix}lgb.json')
        
        self.cat_model = CatBoostClassifier()
        self.cat_model.load_model(f'{prefix}cat.json')
        
        with open(f'{prefix}metadata.json', 'r') as f:
            self.metadata = json.load(f)
        
        self.current_thresh_long = self.metadata['target_precision_threshold_long']
        self.current_thresh_short = self.metadata['target_precision_threshold_short']
        
        print(f"   ✅ Models loaded")
        print(f"   📊 Current thresholds: Long={self.current_thresh_long:.4f}, Short={self.current_thresh_short:.4f}")
        
        # Tracking
        self.confidence_history = deque(maxlen=1000)
        self.long_confidences = []
        self.short_confidences = []
        
    def fetch_live_data(self, interval='5m', limit=500):
        """Fetch live data from Hyperliquid"""
        url = 'https://api.hyperliquid.xyz/info'
        
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(minutes=interval_to_minutes(interval) * limit)).timestamp() * 1000)
        
        payload = {
            'type': 'candleSnapshot',
            'req': {
                'coin': 'BTC',
                'interval': interval,
                'startTime': start_time,
                'endTime': end_time
            }
        }
        
        try:
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code != 200:
                return None
            
            data = resp.json()
            if not isinstance(data, list) or len(data) == 0:
                return None
            
            df_data = []
            for candle in data:
                df_data.append([
                    candle['t'],
                    float(candle['o']),
                    float(candle['h']),
                    float(candle['l']),
                    float(candle['c']),
                    float(candle['v'])
                ])
            
            df = pd.DataFrame(df_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            return df
        except Exception as e:
            print(f"   ❌ Fetch error: {e}")
            return None
    
    def get_trio_proba(self, X):
        """Get consensus probability"""
        p1 = self.xgb_model.predict_proba(X)
        p2 = self.lgb_model.predict(X, num_iteration=self.lgb_model.best_iteration)
        p3 = self.cat_model.predict_proba(X)
        
        ensemble_proba = (p1 + p2 + p3) / 3.0
        std_dev = np.std([p1, p2, p3], axis=0)
        
        return ensemble_proba, np.max(std_dev)
    
    def monitor(self, duration_minutes=30, check_interval=60):
        """Monitor live feed and track confidence levels"""
        print(f"\n🔄 Starting {duration_minutes}-minute monitoring session")
        print(f"   Check interval: {check_interval} seconds")
        print(f"   Target: ~5 trades/day calibration\n")
        
        start_time = datetime.now()
        iterations = 0
        
        while (datetime.now() - start_time).seconds < duration_minutes * 60:
            iterations += 1
            current_time = datetime.now().strftime("%H:%M:%S")
            
            print(f"\n{'='*70}")
            print(f"⏰ {current_time} | Check #{iterations}")
            print(f"{'='*70}")
            
            # Fetch data
            print("📊 Fetching live data...")
            df_5m = self.fetch_live_data('5m', 500)
            df_15m = self.fetch_live_data('15m', 500)
            df_1h = self.fetch_live_data('1h', 500)
            
            if df_5m is None or df_15m is None or df_1h is None:
                print("   ❌ Failed to fetch data, retrying in 60s...")
                time.sleep(check_interval)
                continue
            
            # Generate features
            df_5m = add_all_indicators(df_5m)
            df_15m = add_all_indicators(df_15m)
            df_1h = add_all_indicators(df_1h)
            
            # Merge MTF
            df_5m.set_index('timestamp', inplace=True)
            df_15m.set_index('timestamp', inplace=True)
            df_1h.set_index('timestamp', inplace=True)
            
            exclude = ['open', 'high', 'low', 'close', 'volume']
            
            ctx_cols_15m = [c for c in df_15m.columns if c not in exclude]
            df_15m_ctx = df_15m[ctx_cols_15m].copy()
            df_15m_ctx.columns = [f"{c}_15m" for c in ctx_cols_15m]
            df_15m_resampled = df_15m_ctx.reindex(df_5m.index, method='ffill')
            
            ctx_cols_1h = [c for c in df_1h.columns if c not in exclude]
            df_1h_ctx = df_1h[ctx_cols_1h].copy()
            df_1h_ctx.columns = [f"{c}_1h" for c in ctx_cols_1h]
            df_1h_resampled = df_1h_ctx.reindex(df_5m.index, method='ffill')
            
            df_mtf = pd.concat([df_5m, df_15m_resampled, df_1h_resampled], axis=1)
            df_mtf.dropna(inplace=True)
            
            # Get latest prediction
            feature_cols = [c for c in df_mtf.columns if c not in exclude]
            latest = df_mtf.iloc[-1]
            X = latest[feature_cols].values.reshape(1, -1)
            X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
            
            probas, disagreement = self.get_trio_proba(X)
            
            prob_long = float(probas[0][1])
            prob_short = float(probas[0][2])
            
            # Track
            self.long_confidences.append(prob_long)
            self.short_confidences.append(prob_short)
            self.confidence_history.append({
                'timestamp': datetime.now(),
                'long': prob_long,
                'short': prob_short,
                'disagreement': disagreement,
                'price': float(latest['close'])
            })
            
            # Display
            print(f"\n📊 Current Market State:")
            print(f"   Price: ${latest['close']:,.2f}")
            print(f"   Long Confidence: {prob_long:.2%}")
            print(f"   Short Confidence: {prob_short:.2%}")
            print(f"   Disagreement: {disagreement:.4f}")
            
            # Check signals at current thresholds
            signal_current = None
            if prob_long >= self.current_thresh_long:
                signal_current = f"LONG @ {prob_long:.2%}"
            elif prob_short >= self.current_thresh_short:
                signal_current = f"SHORT @ {prob_short:.2%}"
            
            if signal_current:
                print(f"\n   🎯 SIGNAL (Current Thresholds): {signal_current}")
            else:
                print(f"\n   ⏸️  No signal at current thresholds")
            
            # Calculate suggested thresholds
            if len(self.long_confidences) >= 10:
                self.calculate_suggested_thresholds()
            
            print(f"\n   ⏳ Next check in {check_interval}s...")
            time.sleep(check_interval)
        
        # Final report
        self.generate_calibration_report()
    
    def calculate_suggested_thresholds(self):
        """Calculate thresholds for ~5 trades/day"""
        # Target: 5 trades/day = 5/288 candles = 1.74% signal rate
        target_signal_rate = 0.0174
        
        # Calculate percentiles
        long_sorted = sorted(self.long_confidences, reverse=True)
        short_sorted = sorted(self.short_confidences, reverse=True)
        
        # Find threshold that gives ~1.74% signal rate
        target_idx = int(len(long_sorted) * target_signal_rate)
        
        suggested_long = long_sorted[min(target_idx, len(long_sorted)-1)] if len(long_sorted) > 0 else 0.5
        suggested_short = short_sorted[min(target_idx, len(short_sorted)-1)] if len(short_sorted) > 0 else 0.5
        
        print(f"\n💡 Suggested Thresholds (for ~5 trades/day):")
        print(f"   Long: {suggested_long:.4f} ({suggested_long*100:.2f}%)")
        print(f"   Short: {suggested_short:.4f} ({suggested_short*100:.2f}%)")
        print(f"   Current Long: {self.current_thresh_long:.4f}")
        print(f"   Current Short: {self.current_thresh_short:.4f}")
        
        # Estimate trades with suggested thresholds
        signals_long = sum(1 for c in self.long_confidences if c >= suggested_long)
        signals_short = sum(1 for c in self.short_confidences if c >= suggested_short)
        total_signals = signals_long + signals_short
        
        # Extrapolate to daily
        samples_per_day = 288  # 5M candles
        daily_estimate = (total_signals / len(self.long_confidences)) * samples_per_day
        
        print(f"\n📊 Estimated Daily Signals: {daily_estimate:.1f}")
        print(f"   (Based on {len(self.long_confidences)} samples)")
    
    def generate_calibration_report(self):
        """Generate final calibration report"""
        print("\n" + "="*70)
        print("📊 CALIBRATION REPORT")
        print("="*70)
        
        print(f"\n📈 Confidence Statistics:")
        print(f"   Samples collected: {len(self.long_confidences)}")
        print(f"   Long - Min: {min(self.long_confidences):.2%}, Max: {max(self.long_confidences):.2%}, Avg: {np.mean(self.long_confidences):.2%}")
        print(f"   Short - Min: {min(self.short_confidences):.2%}, Max: {max(self.short_confidences):.2%}, Avg: {np.mean(self.short_confidences):.2%}")
        
        # Calculate various threshold scenarios
        print(f"\n🎯 Threshold Scenarios:")
        
        scenarios = [
            (0.45, "Aggressive (10-15 trades/day)"),
            (0.40, "Moderate (5-10 trades/day)"),
            (0.35, "Active (3-7 trades/day)"),
        ]
        
        for thresh, desc in scenarios:
            long_signals = sum(1 for c in self.long_confidences if c >= thresh)
            short_signals = sum(1 for c in self.short_confidences if c >= thresh)
            total = long_signals + short_signals
            
            daily_est = (total / len(self.long_confidences)) * 288
            
            print(f"\n   Threshold: {thresh:.2f} ({thresh*100:.0f}%) - {desc}")
            print(f"      Estimated daily signals: {daily_est:.1f}")
            print(f"      Long: {long_signals}, Short: {short_signals}")
        
        # Recommendation
        print(f"\n💡 RECOMMENDATION:")
        print(f"   For ~5 trades/day, use threshold: 0.40-0.45")
        print(f"   This balances frequency with quality")
        print(f"   Note: Lower thresholds = more trades but lower win rate")
        
        print("\n" + "="*70)

def interval_to_minutes(interval):
    """Convert interval string to minutes"""
    mapping = {'1m': 1, '5m': 5, '15m': 15, '1h': 60}
    return mapping.get(interval, 5)

def main():
    monitor = LiveMonitor()
    monitor.monitor(duration_minutes=30, check_interval=60)

if __name__ == '__main__':
    main()
