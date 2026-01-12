#!/usr/bin/env python3
"""
🏹 WINNER HUNTER (1H) GRANULAR DISCOVERY
Finding the threshold where 1H model actually fires trades
while maintaining acceptable risk/reward.
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
import warnings
warnings.filterwarnings('ignore')

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))
from utils.feature_engineer import add_all_indicators

MODEL_DIR = 'training/models/'

class WHDiscovery:
    def __init__(self):
        print("📦 Loading Winner Hunter Trio...")
        self.wh_prefix = os.path.join(MODEL_DIR, 'winner_hunter_1h_trio_')
        self.wh_xgb = xgb.XGBClassifier(); self.wh_xgb.load_model(f'{self.wh_prefix}xgb.json')
        self.wh_lgb = lgb.Booster(model_file=f'{self.wh_prefix}lgb.json')
        self.wh_cat = CatBoostClassifier(); self.wh_cat.load_model(f'{self.wh_prefix}cat.json')

    def fetch_data(self, interval, days=31):
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
        df = pd.DataFrame([[c['t'], float(c['o']), float(c['h']), float(c['l']), float(c['c']), float(c['v'])] for c in all_data], 
                         columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.sort_values('timestamp', inplace=True)
        return df

    def get_probs(self, df_5m, df_15m, df_1h):
        exclude = ['open', 'high', 'low', 'close', 'volume']
        df_5m_idx = df_5m.set_index('timestamp')
        df_15m_idx = df_15m.set_index('timestamp')
        df_1h_idx = df_1h.set_index('timestamp')
        
        base_df = df_1h_idx.copy()
        ctx_5m = df_5m_idx[[c for c in df_5m_idx.columns if c not in exclude]].copy()
        ctx_5m.columns = [f"{c}_5m" for c in ctx_5m.columns]
        ctx_15m = df_15m_idx[[c for c in df_15m_idx.columns if c not in exclude]].copy()
        ctx_15m.columns = [f"{c}_15m" for c in ctx_15m.columns]
        df_final = pd.concat([base_df, ctx_5m.reindex(base_df.index, method='ffill'), ctx_15m.reindex(base_df.index, method='ffill')], axis=1).dropna()
        X = np.nan_to_num(df_final[[c for c in df_final.columns if c not in exclude]].values, nan=0.0)
        probs = (self.wh_xgb.predict_proba(X)[:,1] + self.wh_lgb.predict(X) + self.wh_cat.predict_proba(X)[:,1]) / 3
        return df_final, probs

    def simulate(self, df, df_5m_raw, probs, thresh, tp=0.015, sl=0.008):
        signals = np.where(probs >= thresh)[0]
        wins, losses = 0, 0
        last_exit_idx = -1
        
        for idx in signals:
            if idx <= last_exit_idx: continue
            entry_time = df.index[idx]
            entry_price = df.iloc[idx]['close']
            tp_price = entry_price * (1 + tp)
            sl_price = entry_price * (1 - sl)
            
            df_verify = df_5m_raw[df_5m_raw['timestamp'] >= entry_time]
            
            outcome = "OPEN"
            for _, row in df_verify.iterrows():
                if row['high'] >= tp_price: 
                    outcome = "WIN"; wins += 1
                    res_time = row['timestamp']
                    try: last_exit_idx = df.index.get_indexer([res_time], method='ffill')[0]
                    except: last_exit_idx = idx + 1
                    break
                if row['low'] <= sl_price: 
                    outcome = "LOSS"; losses += 1
                    res_time = row['timestamp']
                    try: last_exit_idx = df.index.get_indexer([res_time], method='ffill')[0]
                    except: last_exit_idx = idx + 1
                    break
        
        total = wins + losses
        wr = (wins / total * 100) if total > 0 else 0
        return total, wr

    def run(self):
        print("📥 Fetching 31 days of data...")
        df_5m_raw = self.fetch_data('5m')
        df_15m_raw = self.fetch_data('15m')
        df_1h_raw = self.fetch_data('1h')
        
        print("🔧 Engineering features...")
        df_5m = add_all_indicators(df_5m_raw)
        df_15m = add_all_indicators(df_15m_raw)
        df_1h = add_all_indicators(df_1h_raw)
        
        print("🔍 Calculating Winner Hunter probabilities...")
        df, probs = self.get_probs(df_5m, df_15m, df_1h)
        
        print("\n" + "="*80)
        print("🎯 WINNER HUNTER THRESHOLD SWEEP (30 DAYS)")
        print("="*80)
        results = []
        for t in np.arange(0.35, 0.53, 0.01):
            n, wr = self.simulate(df, df_5m_raw, probs, t)
            results.append({'Threshold': f"{t:.2f}", 'Trades': n, 'Win Rate': f"{wr:.1f}%"})
            
        print(pd.DataFrame(results).to_string(index=False))

if __name__ == "__main__":
    WHDiscovery().run()
