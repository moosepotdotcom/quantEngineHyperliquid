#!/usr/bin/env python3
"""
MTF Scalper: Last Week's Trade Log Generator
Fetches last 7-8 days of data and simulates "Gem" configuration.
"""
import os
import sys
import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
import requests
import json
import time
from datetime import datetime, timedelta

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))
from utils.feature_engineer import add_all_indicators

MODEL_DIR = 'training/models/'

class TradeReportGenerator:
    def __init__(self):
        print("📦 Loading Trio Ensemble Models...")
        self.mtf_prefix = os.path.join(MODEL_DIR, 'mtf_scalper_5m_trio_')
        
        self.xgb = xgb.XGBClassifier()
        self.xgb.load_model(f'{self.mtf_prefix}xgb.json')
        self.lgb = lgb.Booster(model_file=f'{self.mtf_prefix}lgb.json')
        self.cat = CatBoostClassifier()
        self.cat.load_model(f'{self.mtf_prefix}cat.json')
        
        self.threshold = 0.90
        self.tp_pct = 0.003
        self.sl_pct = 0.005

    def fetch_data(self, interval, days=8):
        """Fetch live data from Hyperliquid API in chunks"""
        url = 'https://api.hyperliquid.xyz/info'
        all_data = []
        
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
        current_end = end_time
        while current_end > start_time:
            print(f"   🌐 Fetching {interval} chunks... ({len(all_data)} rows so far)")
            payload = {
                'type': 'candleSnapshot',
                'req': {
                    'coin': 'BTC',
                    'interval': interval,
                    'startTime': start_time,
                    'endTime': current_end
                }
            }
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code != 200: break
            
            data = resp.json()
            if not data or not isinstance(data, list): break
            
            all_data.extend(data)
            current_end = data[0]['t'] - 1 # Move back in time
            if len(data) < 500: break # Last chunk
            
        # Deduplicate and sort
        df_data = []
        seen_t = set()
        for c in all_data:
            if c['t'] not in seen_t:
                df_data.append([c['t'], float(c['o']), float(c['h']), float(c['l']), float(c['c']), float(c['v'])])
                seen_t.add(c['t'])
        
        df = pd.DataFrame(df_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.sort_values('timestamp', inplace=True)
        return df

    def generate_report(self):
        print("\n" + "="*70)
        print("📊 GENERATING LAST WEEK'S 'GEM' TRADE LOG")
        print("="*70)
        
        # 1. Fetch Data
        print("\n📥 Fetching multi-timeframe data...")
        df_5m = self.fetch_data('5m')
        df_15m = self.fetch_data('15m')
        df_1h = self.fetch_data('1h')
        
        print(f"✅ Fetched: 5m ({len(df_5m)}), 15m ({len(df_15m)}), 1h ({len(df_1h)})")
        
        # 2. Add Indicators
        print("\n🔧 Generating features...")
        df_5m = add_all_indicators(df_5m)
        df_15m = add_all_indicators(df_15m)
        df_1h = add_all_indicators(df_1h)
        
        # 3. Merge MTF Context
        print("\n🔗 Aligning MTF context...")
        df_5m.set_index('timestamp', inplace=True)
        df_15m.set_index('timestamp', inplace=True)
        df_1h.set_index('timestamp', inplace=True)
        
        exclude = ['open', 'high', 'low', 'close', 'volume']
        
        # 15m context
        ctx_15m = [c for c in df_15m.columns if c not in exclude]
        df_15m_renamed = df_15m[ctx_15m].copy()
        df_15m_renamed.columns = [f"{c}_15m" for c in ctx_15m]
        df_15m_resampled = df_15m_renamed.reindex(df_5m.index, method='ffill')
        
        # 1h context
        ctx_1h = [c for c in df_1h.columns if c not in exclude]
        df_1h_renamed = df_1h[ctx_1h].copy()
        df_1h_renamed.columns = [f"{c}_1h" for c in ctx_1h]
        df_1h_resampled = df_1h_renamed.reindex(df_5m.index, method='ffill')
        
        df_final = pd.concat([df_5m, df_15m_resampled, df_1h_resampled], axis=1).dropna()
        print(f"✅ Final dataset: {len(df_final)} bars, {len(df_final.columns)} columns")
        
        # 4. Run Ensemble
        print("\n🤖 Running Trio Ensemble...")
        all_exclude = exclude + ['timestamp']
        features = [c for c in df_final.columns if c not in all_exclude]
        X = df_final[features].values
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        
        p1 = self.xgb.predict_proba(X)[:,1]
        p2 = self.lgb.predict(X)
        p3 = self.cat.predict_proba(X)[:,1]
        probs = (p1 + p2 + p3) / 3
        
        # 5. Extract Trades
        print("\n🎯 Filtering Gem signals (Threshold: 0.90)...")
        signals_idx = np.where(probs >= self.threshold)[0]
        
        trades = []
        last_exit_idx = -1
        
        for idx in signals_idx:
            if idx <= last_exit_idx: continue # Avoid overlapping trades
            
            entry_price = df_final.iloc[idx]['close']
            entry_time = df_final.index[idx]
            tp_price = entry_price * (1 + self.tp_pct)
            sl_price = entry_price * (1 - self.sl_pct)
            
            outcome = "OPEN"
            exit_time = None
            exit_price = None
            
            for j in range(idx + 1, len(df_final)):
                high = df_final.iloc[j]['high']
                low = df_final.iloc[j]['low']
                
                if high >= tp_price:
                    outcome = "WIN"
                    exit_price = tp_price
                    exit_time = df_final.index[j]
                    last_exit_idx = j
                    break
                if low <= sl_price:
                    outcome = "LOSS"
                    exit_price = sl_price
                    exit_time = df_final.index[j]
                    last_exit_idx = j
                    break
                    
            if outcome != "OPEN":
                trades.append({
                    'Entry Time': entry_time,
                    'Entry Price': entry_price,
                    'Exit Time': exit_time,
                    'Exit Price': exit_price,
                    'Outcome': outcome,
                    'PnL %': 0.3 if outcome == "WIN" else -0.5,
                    'PnL $': (0.3 if outcome == "WIN" else -0.5) * 1.27 * 95000 / 100, # Approx $1.2M pos
                    'Duration (m)': (exit_time - entry_time).total_seconds() / 60,
                    'Confidence': probs[idx]
                })

        # 6. Output Report
        if not trades:
            print("\n❌ No signals found for the last week.")
            return

        report_df = pd.DataFrame(trades)
        total_pnl = report_df['PnL $'].sum()
        win_rate = (report_df['Outcome'] == "WIN").mean() * 100
        
        print("\n" + "="*70)
        print("🏆 LAST WEEK'S PERFORMANCE REPORT")
        print("="*70)
        print(f"📅 Period: {df_final.index[0]} to {df_final.index[-1]}")
        print(f"📊 Total Trades: {len(report_df)}")
        print(f"✅ Wins: {sum(report_df['Outcome'] == 'WIN')}")
        print(f"❌ Losses: {sum(report_df['Outcome'] == 'LOSS')}")
        print(f"📈 Win Rate: {win_rate:.1f}%")
        print(f"💰 Total P&L: ${total_pnl:,.2f}")
        print("="*70)
        
        print("\n📝 DETAILED LOG:")
        print(report_df[['Entry Time', 'Entry Price', 'Exit Time', 'PnL %', 'Duration (m)', 'Confidence']].to_string(index=False))

if __name__ == '__main__':
    generator = TradeReportGenerator()
    generator.generate_report()
