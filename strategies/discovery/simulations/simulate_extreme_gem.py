#!/usr/bin/env python3
"""
💎 EXTREME GEM SIMULATOR - 27x Leverage Audit
Simulates $60 capital with 0.02 BTC positions (~31.6x actual leverage at $95k).
Using Gem Targets: 0.3% TP / 0.5% SL
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
from datetime import datetime, timedelta

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))
from utils.feature_engineer import add_all_indicators

MODEL_DIR = 'training/models/'

class ExtremeSimulator:
    def __init__(self, capital=60, target_size=0.02):
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
        self.capital = capital
        self.target_size = target_size # 0.02 BTC

    def fetch_data(self, interval, days=8):
        url = 'https://api.hyperliquid.xyz/info'
        all_data = []
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
        current_end = end_time
        while current_end > start_time:
            payload = {'type': 'candleSnapshot', 'req': {'coin': 'BTC', 'interval': interval, 'startTime': start_time, 'endTime': current_end}}
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code != 200: break
            data = resp.json()
            if not data or not isinstance(data, list): break
            all_data.extend(data)
            current_end = data[0]['t'] - 1
            if len(data) < 500: break
        
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

    def run_simulation(self):
        print("\n" + "🔥"*20)
        print("💎 EXTREME GEM SIMULATION ($60 @ 0.02 BTC)")
        print("🔥"*20)
        
        # 1. Fetch & Process
        df_5m = self.fetch_data('5m')
        df_15m = self.fetch_data('15m')
        df_1h = self.fetch_data('1h')
        
        df_5m = add_all_indicators(df_5m)
        df_15m = add_all_indicators(df_15m)
        df_1h = add_all_indicators(df_1h)
        
        df_5m.set_index('timestamp', inplace=True)
        df_15m.set_index('timestamp', inplace=True)
        df_1h.set_index('timestamp', inplace=True)
        
        exclude = ['open', 'high', 'low', 'close', 'volume']
        ctx_15m = [f"{c}_15m" for c in df_15m.columns if c not in exclude]
        df_15m_c = df_15m[[c.replace('_15m','') for c in ctx_15m]].copy()
        df_15m_c.columns = ctx_15m
        
        ctx_1h = [f"{c}_1h" for c in df_1h.columns if c not in exclude]
        df_1h_c = df_1h[[c.replace('_1h','') for c in ctx_1h]].copy()
        df_1h_c.columns = ctx_1h
        
        df_final = pd.concat([df_5m, df_15m_c.reindex(df_5m.index, method='ffill'), df_1h_c.reindex(df_5m.index, method='ffill')], axis=1).dropna()
        
        # 2. Predict
        features = [c for c in df_final.columns if c not in exclude + ['timestamp']]
        X = np.nan_to_num(df_final[features].values, nan=0.0)
        probs = (self.xgb.predict_proba(X)[:,1] + self.lgb.predict(X) + self.cat.predict_proba(X)[:,1]) / 3
        
        # 3. Simulate
        signals_idx = np.where(probs >= self.threshold)[0]
        balance = self.capital
        trades = []
        last_exit_idx = -1
        
        for idx in signals_idx:
            if idx <= last_exit_idx: continue
            
            entry_price = df_final.iloc[idx]['close']
            tp_price = entry_price * (1 + self.tp_pct)
            sl_price = entry_price * (1 - self.sl_pct)
            
            outcome = "OPEN"
            for j in range(idx + 1, len(df_final)):
                h, l = df_final.iloc[j]['high'], df_final.iloc[j]['low']
                if h >= tp_price:
                    outcome = "WIN"; break
                if l <= sl_price:
                    outcome = "LOSS"; break
                if j > idx + 288: # 24h limit
                    break
            
            if outcome != "OPEN":
                # Real P&L calculation for 0.02 BTC size
                # P&L = (Exit - Entry) * Size
                profit_factor = 1 if outcome == "WIN" else -1
                actual_move = entry_price * (self.tp_pct if outcome == "WIN" else self.sl_pct) * profit_factor
                pnl_dollars = actual_move * self.target_size
                
                # Update compounding balance
                balance += pnl_dollars
                last_exit_idx = j
                
                trades.append({
                    'Time': df_final.index[idx],
                    'Price': entry_price,
                    'Outcome': outcome,
                    'Gain/Loss $': pnl_dollars,
                    'New Balance': balance,
                    'Leverage (Eff)': (self.target_size * entry_price) / (balance - pnl_dollars)
                })

        # 4. Report
        if not trades:
            print("No signals found.")
            return

        res = pd.DataFrame(trades)
        print("\n" + "="*60)
        print(f"📈 EXTREME STRATEGY REPORT (Starting Capital: ${self.capital})")
        print("="*60)
        print(f"💰 Total Profit: ${res['Gain/Loss $'].sum():.2f}")
        print(f"🏆 Final Balance: ${balance:.2f} (+{(balance/self.capital-1)*100:.1f}%)")
        print(f"📊 Win Rate: {(res['Outcome']=='WIN').mean()*100:.1f}%")
        print(f"⚠️  Max Effective Leverage: {res['Leverage (Eff)'].max():.1f}x")
        print(f"🛡️  Max Loss in single trade: ${res['Gain/Loss $'].min():.2f}")
        print("="*60)
        print("\nDETAILED LOG:")
        print(res[['Time', 'Outcome', 'Gain/Loss $', 'New Balance', 'Leverage (Eff)']].to_string(index=False))

if __name__ == "__main__":
    ExtremeSimulator().run_simulation()
