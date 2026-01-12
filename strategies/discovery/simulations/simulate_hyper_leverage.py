#!/usr/bin/env python3
"""
☣️ HYPER-LEVERAGE SIMULATOR - 400x Audit
Simulates $60 capital with 400x Effective Leverage.
Liquidation Sensitivity: 0.25% (Account blown before 0.5% SL hits)
"""
import os
import sys
import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
import requests
from datetime import datetime, timedelta

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))
from utils.feature_engineer import add_all_indicators

MODEL_DIR = 'training/models/'

class HyperLeverageSimulator:
    def __init__(self, leverage=400, capital=60):
        print("📦 Loading Trio Ensemble Models...")
        self.mtf_prefix = os.path.join(MODEL_DIR, 'mtf_scalper_5m_trio_')
        self.xgb = xgb.XGBClassifier()
        self.xgb.load_model(f'{self.mtf_prefix}xgb.json')
        self.lgb = lgb.Booster(model_file=f'{self.mtf_prefix}lgb.json')
        self.cat = CatBoostClassifier()
        self.cat.load_model(f'{self.mtf_prefix}cat.json')
        
        self.threshold = 0.90
        self.tp_pct = 0.003
        self.liq_pct = (1.0 / leverage) # 0.25% for 400x
        self.capital = capital
        self.leverage = leverage

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
        print("\n" + "💀"*20)
        print(f"☣️  HYPER-LEVERAGE SIMULATION ($60 @ {self.leverage}x)")
        print(f"   LIQUIDATION TOLERANCE: {self.liq_pct*100:.3f}%")
        print("💀"*20)
        
        df_5m = self.fetch_data('5m')
        df_15m = self.fetch_data('15m')
        df_1h = self.fetch_data('1h')
        
        # Add indicators before setting index
        df_5m = add_all_indicators(df_5m)
        df_15m = add_all_indicators(df_15m)
        df_1h = add_all_indicators(df_1h)
        
        df_5m.set_index('timestamp', inplace=True)
        df_15m.set_index('timestamp', inplace=True)
        df_1h.set_index('timestamp', inplace=True)
        
        exclude = ['open', 'high', 'low', 'close', 'volume']
        df_15m_c = df_15m[[c for c in df_15m.columns if c not in exclude]].copy()
        df_15m_c.columns = [f"{c}_15m" for c in df_15m_c.columns]
        df_1h_c = df_1h[[c for c in df_1h.columns if c not in exclude]].copy()
        df_1h_c.columns = [f"{c}_1h" for c in df_1h_c.columns]
        
        # Ensure indices are compatible
        df_5m.index = pd.to_datetime(df_5m.index)
        df_15m_c.index = pd.to_datetime(df_15m_c.index)
        df_1h_c.index = pd.to_datetime(df_1h_c.index)
        
        df_final = pd.concat([df_5m, df_15m_c.reindex(df_5m.index, method='ffill'), df_1h_c.reindex(df_5m.index, method='ffill')], axis=1).dropna()
        
        features = [c for c in df_final.columns if c not in exclude + ['timestamp']]
        X = np.nan_to_num(df_final[features].values, nan=0.0)
        probs = (self.xgb.predict_proba(X)[:,1] + self.lgb.predict(X) + self.cat.predict_proba(X)[:,1]) / 3
        
        signals_idx = np.where(probs >= self.threshold)[0]
        balance = self.capital
        trades = []
        last_exit_idx = -1
        
        for idx in signals_idx:
            if idx <= last_exit_idx: continue
            if balance <= 0: break
            
            entry_price = df_final.iloc[idx]['close']
            tp_price = entry_price * (1 + self.tp_pct)
            liq_price = entry_price * (1 - self.liq_pct)
            
            outcome = "OPEN"
            for j in range(idx + 1, len(df_final)):
                h, l = df_final.iloc[j]['high'], df_final.iloc[j]['low']
                # At 400x, Liquidation happens 2x FASTER than our Stop Loss
                if l <= liq_price:
                    outcome = "LIQUIDATED 💀"
                    break
                if h >= tp_price:
                    outcome = "WIN"
                    break
            
            if outcome != "OPEN":
                if outcome == "WIN":
                    # Profit = Balance * Leverage * TP
                    pnl = balance * self.leverage * self.tp_pct
                    balance += pnl
                else:
                    # Liquidation = $0
                    pnl = -balance
                    balance = 0
                
                last_exit_idx = j
                trades.append({
                    'Time': df_final.index[idx],
                    'Outcome': outcome,
                    'Gain/Loss $': pnl,
                    'New Balance': balance
                })

        if not trades:
            print("No signals found.")
            return

        res = pd.DataFrame(trades)
        print("\n" + "="*60)
        print(f"📉 HYPER-LEVERAGE REPORT ({self.leverage}x)")
        print("="*60)
        print(f"💰 Result: ${balance:.2f}")
        print(f"📊 Win Rate: {(res['Outcome']=='WIN').mean()*100:.1f}%")
        print(f"💀 Liquidation count: {(res['Outcome']=='LIQUIDATED 💀').sum()}")
        print("="*60)
        print("\nDETAILED LOG:")
        print(res.to_string(index=False))

if __name__ == "__main__":
    HyperLeverageSimulator(leverage=400).run_simulation()
    # Also run 125x for comparison (some exchanges allow this)
    # HyperLeverageSimulator(leverage=125).run_simulation()
