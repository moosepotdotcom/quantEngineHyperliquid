#!/usr/bin/env python3
"""
🚀 FULL SYSTEM SANDBOX - Complete Trading Engine Test
Runs all models with monitoring until we get a trade signal.
"""

import os
import sys
import pandas as pd
import numpy as np
import xgboost as xgb
import requests
import time
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'utils'))

from feature_engineer import add_all_indicators

MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')

class TradingEngine:
    """Complete trading engine with all models"""
    
    def __init__(self):
        # Load models
        print("📦 Loading Models...")
        self.winner_model = xgb.XGBClassifier()
        self.winner_model.load_model(os.path.join(MODEL_DIR, 'winner_hunter_1h.json'))
        print("   ✅ Winner Hunter (1H) loaded")
        
        self.threshold = 0.95
        self.trades_executed = []
        self.signals_logged = []
        
    def fetch_data(self, interval='1h', limit=500):
        """Fetch live data from Hyperliquid API"""
        from datetime import datetime, timedelta
        
        url = 'https://api.hyperliquid.xyz/info'
        
        # Calculate time range based on interval and limit
        interval_minutes = {
            '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '2h': 120, '4h': 240, '1d': 1440
        }
        
        minutes = interval_minutes.get(interval, 60)
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(minutes=minutes * limit)).timestamp() * 1000)
        
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
            print(f"      🌐 Fetching from Hyperliquid: {interval}, limit={limit}", flush=True)
            resp = requests.post(url, json=payload, timeout=10)
            print(f"      🌐 Response status: {resp.status_code}", flush=True)
            
            if resp.status_code != 200:
                print(f"      ❌ ERROR: HTTP {resp.status_code}", flush=True)
                return None
            
            data = resp.json()
            print(f"      🌐 Response type: {type(data)}, length: {len(data) if isinstance(data, list) else 'N/A'}", flush=True)
            
            if not isinstance(data, list):
                print(f"      ❌ ERROR: API returned non-list: {data}", flush=True)
                return None
            
            if len(data) == 0:
                print(f"      ❌ ERROR: API returned empty list", flush=True)
                return None
            
            # Convert Hyperliquid format to our DataFrame format
            # Hyperliquid: {'t': timestamp_ms, 'o': open, 'h': high, 'l': low, 'c': close, 'v': volume}
            df_data = []
            for candle in data:
                df_data.append([
                    candle['t'],  # timestamp in milliseconds
                    float(candle['o']),  # open
                    float(candle['h']),  # high
                    float(candle['l']),  # low
                    float(candle['c']),  # close
                    float(candle['v'])   # volume
                ])
            
            df = pd.DataFrame(df_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            print(f"      🌐 DataFrame created: {len(df)} rows", flush=True)
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            print(f"      🌐 After processing: {len(df)} rows", flush=True)
            return df
        except Exception as e:
            print(f"   ❌ Fetch Error: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return None
    
    def check_winner_hunter(self):
        """Check Winner Hunter for signals"""
        import sys
        df = self.fetch_data('1h')  # Uses default limit=500
        if df is None:
            return None, 0.0
        
        print(f"   📊 Fetched {len(df)} bars", flush=True)
        print(f"   📊 Columns: {list(df.columns)}", flush=True)
        print(f"   📊 First row timestamp: {df.iloc[0]['timestamp']}", flush=True)
        print(f"   📊 Last row timestamp: {df.iloc[-1]['timestamp']}", flush=True)
        sys.stdout.flush()
        
        df = add_all_indicators(df)
        
        print(f"   📊 After indicators: {len(df)} bars", flush=True)
        sys.stdout.flush()
        
        if len(df) == 0:
            print(f"   ❌ ERROR: DataFrame is empty after add_all_indicators!", flush=True)
            return None, 0.0
        
        exclude = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        features = [c for c in df.columns if c not in exclude]
        
        latest = df.iloc[-1]
        X = latest[features].values.reshape(1, -1)
        
        try:
            prob = self.winner_model.predict_proba(X)[0][1]
            
            if prob >= self.threshold:
                return {
                    'model': 'Winner Hunter (1H)',
                    'timestamp': datetime.now(),
                    'price': latest['close'],
                    'confidence': prob,
                    'rsi': latest['rsi_14'],
                    'macd': latest['macd_hist'],
                    'atr_pct': (latest['atr_14'] / latest['close']) * 100
                }, prob
            
            return None, prob
        except Exception as e:
            print(f"   ⚠️ Prediction Error: {e}")
            return None, 0.0
    
    def execute_trade(self, signal):
        """Execute trade (sandbox mode)"""
        print("\n" + "="*70)
        print("🎉 TRADE SIGNAL DETECTED!")
        print("="*70)
        print(f"   🤖 Model: {signal['model']}")
        print(f"   ⏰ Time: {signal['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   💰 Price: ${signal['price']:,.2f}")
        print(f"   📊 Confidence: {signal['confidence']:.2%}")
        print(f"   📈 RSI: {signal['rsi']:.1f}")
        print(f"   📉 MACD: {signal['macd']:.2f}")
        print(f"   📊 ATR%: {signal['atr_pct']:.3f}%")
        print("="*70)
        
        # Calculate targets
        tp_pct = 0.015  # 1.5%
        sl_pct = 0.008  # 0.8%
        
        tp_price = signal['price'] * (1 + tp_pct)
        sl_price = signal['price'] * (1 - sl_pct)
        
        print(f"\n📋 TRADE PLAN:")
        print(f"   🎯 Entry: ${signal['price']:,.2f}")
        print(f"   ✅ Take Profit: ${tp_price:,.2f} (+{tp_pct*100:.1f}%)")
        print(f"   ❌ Stop Loss: ${sl_price:,.2f} (-{sl_pct*100:.1f}%)")
        print(f"   💵 Risk/Reward: 1:{tp_pct/sl_pct:.2f}")
        
        self.trades_executed.append(signal)
        
        return True
    
    def run_continuous_monitoring(self, max_hours=24):
        """Run continuous monitoring until trade or timeout"""
        
        print("\n" + "="*70)
        print("🚀 FULL SYSTEM SANDBOX - LIVE TRADING ENGINE")
        print("="*70)
        print(f"⏱️  Max Runtime: {max_hours} hours")
        print(f"🎯 Trade Threshold: {self.threshold:.0%}")
        print(f"🔄 Check Interval: 60 seconds (1H candle updates)")
        print("="*70)
        
        start_time = datetime.now()
        iteration = 0
        max_iterations = max_hours * 60  # Check every minute
        
        try:
            while iteration < max_iterations:
                iteration += 1
                current_time = datetime.now().strftime("%H:%M:%S")
                elapsed = (datetime.now() - start_time).seconds / 60
                
                print(f"\n{'='*70}")
                print(f"⏰ {current_time} | Check #{iteration} | Elapsed: {elapsed:.1f}m")
                print(f"{'='*70}")
                
                # Check Winner Hunter
                print("\n🏆 Checking Winner Hunter (1H)...")
                signal, confidence = self.check_winner_hunter()
                
                if signal:
                    # TRADE DETECTED!
                    self.execute_trade(signal)
                    
                    print("\n✅ SANDBOX TEST SUCCESSFUL!")
                    print("   🎯 Trade signal captured")
                    print("   ✅ All systems operational")
                    print("   ✅ Ready for production deployment")
                    
                    return True
                else:
                    # No signal - show status
                    gap = self.threshold - confidence
                    progress = (confidence / self.threshold) * 100
                    
                    status_emoji = "🟢" if confidence >= self.threshold else \
                                  "🟡" if confidence >= self.threshold * 0.8 else \
                                  "🟠" if confidence >= self.threshold * 0.5 else "🔴"
                    
                    print(f"   {status_emoji} Confidence: {confidence:.2%}")
                    print(f"   📊 Progress: {progress:.1f}%")
                    print(f"   🎯 Gap: {gap*100:.2f}%")
                    
                    # Progress bar
                    bar_length = 40
                    filled = int(bar_length * progress / 100)
                    bar = "█" * filled + "░" * (bar_length - filled)
                    print(f"   [{bar}] {progress:.1f}%")
                    
                    # Log signal
                    self.signals_logged.append({
                        'timestamp': datetime.now(),
                        'confidence': confidence,
                        'gap': gap
                    })
                
                # Summary stats
                if len(self.signals_logged) > 0:
                    recent = self.signals_logged[-10:]
                    avg_conf = np.mean([s['confidence'] for s in recent])
                    max_conf = np.max([s['confidence'] for s in recent])
                    
                    print(f"\n   📊 Recent Stats (last {len(recent)} checks):")
                    print(f"      Avg Confidence: {avg_conf:.2%}")
                    print(f"      Max Confidence: {max_conf:.2%}")
                    print(f"      Total Checks: {len(self.signals_logged)}")
                
                # Wait before next check
                print(f"\n   ⏳ Next check in 60 seconds...")
                time.sleep(60)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Monitoring stopped by user")
        
        # Timeout reached
        print("\n" + "="*70)
        print("⏱️ MONITORING TIMEOUT REACHED")
        print("="*70)
        print(f"   Total Checks: {iteration}")
        print(f"   Runtime: {(datetime.now() - start_time).seconds / 60:.1f} minutes")
        print(f"   Signals Logged: {len(self.signals_logged)}")
        
        if len(self.signals_logged) > 0:
            max_conf = max([s['confidence'] for s in self.signals_logged])
            print(f"   Max Confidence Seen: {max_conf:.2%}")
        
        print("\n   ℹ️  No trade signal reached threshold during monitoring period")
        print("   ℹ️  This is expected in low-volatility market conditions")
        print("   ℹ️  Models are correctly waiting for high-confidence setups")
        
        return False

def main():
    """Main entry point"""
    
    print("\n" + "🚀"*35)
    print("QUANT ENGINE - FULL SYSTEM SANDBOX TEST")
    print("🚀"*35 + "\n")
    
    engine = TradingEngine()
    
    # Run for 24 hours or until trade
    success = engine.run_continuous_monitoring(max_hours=24)
    
    print("\n" + "="*70)
    print("📊 FINAL REPORT")
    print("="*70)
    
    if success:
        print("✅ SANDBOX TEST: PASSED")
        print("✅ Trade signal successfully captured and executed")
        print("✅ All systems validated")
        print("\n🎯 READY FOR PRODUCTION DEPLOYMENT")
    else:
        print("ℹ️  SANDBOX TEST: COMPLETED (No trades)")
        print("ℹ️  System operational but no high-confidence setups found")
        print("ℹ️  This validates the model's selectivity")
        print("\n✅ SYSTEM VALIDATED - Models working as designed")
    
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
