#!/usr/bin/env python3
"""
💎 HYPER-DISCOVERY: VOLUME SCALING
Sweeps thresholds across all 3 engines to find the configuration
that delivers 5-6 high-precision winners per day (~40-45 trades/week).
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

class HyperDiscovery:
    def __init__(self):
        print("📦 Loading Trio Ensemble Models...")
        self.wh_prefix = os.path.join(MODEL_DIR, 'winner_hunter_1h_trio_')
        self.mtf_prefix = os.path.join(MODEL_DIR, 'mtf_scalper_5m_trio_')
        
        self.mtf_xgb = xgb.XGBClassifier(); self.mtf_xgb.load_model(f'{self.mtf_prefix}xgb.json')
        self.mtf_lgb = lgb.Booster(model_file=f'{self.mtf_prefix}lgb.json')
        self.mtf_cat = CatBoostClassifier(); self.mtf_cat.load_model(f'{self.mtf_prefix}cat.json')
        
        self.wh_xgb = xgb.XGBClassifier(); self.wh_xgb.load_model(f'{self.wh_prefix}xgb.json')
        self.wh_lgb = lgb.Booster(model_file=f'{self.wh_prefix}lgb.json')
        self.wh_cat = CatBoostClassifier(); self.wh_cat.load_model(f'{self.wh_prefix}cat.json')

    def fetch_data(self, interval, days=9):
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

    def get_probs(self, df_5m, df_15m, df_1h, target='mtf'):
        exclude = ['open', 'high', 'low', 'close', 'volume']
        df_5m_idx = df_5m.set_index('timestamp')
        df_15m_idx = df_15m.set_index('timestamp')
        df_1h_idx = df_1h.set_index('timestamp')
        
        if target == 'wh':
            base_df = df_1h_idx.copy()
            ctx_5m = df_5m_idx[[c for c in df_5m_idx.columns if c not in exclude]].copy()
            ctx_5m.columns = [f"{c}_5m" for c in ctx_5m.columns]
            ctx_15m = df_15m_idx[[c for c in df_15m_idx.columns if c not in exclude]].copy()
            ctx_15m.columns = [f"{c}_15m" for c in ctx_15m.columns]
            df_final = pd.concat([base_df, ctx_5m.reindex(base_df.index, method='ffill'), ctx_15m.reindex(base_df.index, method='ffill')], axis=1).dropna()
            X = np.nan_to_num(df_final[[c for c in df_final.columns if c not in exclude]].values, nan=0.0)
            probs = (self.wh_xgb.predict_proba(X)[:,1] + self.wh_lgb.predict(X) + self.wh_cat.predict_proba(X)[:,1]) / 3
        else:
            base_df = df_5m_idx.copy()
            ctx_1h = df_1h_idx[[c for c in df_1h_idx.columns if c not in exclude]].copy()
            ctx_1h.columns = [f"{c}_1h" for c in ctx_1h.columns]
            ctx_15m = df_15m_idx[[c for c in df_15m_idx.columns if c not in exclude]].copy()
            ctx_15m.columns = [f"{c}_15m" for c in ctx_15m.columns]
            df_final = pd.concat([base_df, ctx_1h.reindex(base_df.index, method='ffill'), ctx_15m.reindex(base_df.index, method='ffill')], axis=1).dropna()
            X = np.nan_to_num(df_final[[c for c in df_final.columns if c not in exclude]].values, nan=0.0)
            probs = (self.mtf_xgb.predict_proba(X)[:,1] + self.mtf_lgb.predict(X) + self.mtf_cat.predict_proba(X)[:,1]) / 3
            
        return df_final, probs

    def simulate_threshold(self, df, df_raw_5m, probs, thresh, tp, sl):
        signals = np.where(probs >= thresh)[0]
        wins = 0
        losses = 0
        last_exit_idx = -1
        
        for idx in signals:
            if idx <= last_exit_idx: continue
            
            entry_price = df.iloc[idx]['close']
            entry_time = df.index[idx]
            tp_price = entry_price * (1 + tp)
            sl_price = entry_price * (1 - sl)
            
            df_verify = df_raw_5m[df_raw_5m['timestamp'] >= entry_time]
            
            outcome = "OPEN"
            for _, row in df_verify.iterrows():
                if row['high'] >= tp_price: 
                    outcome = "WIN"; wins += 1
                    res_time = row['timestamp']
                    try:
                        last_exit_idx = df.index.get_indexer([res_time], method='ffill')[0]
                    except:
                        last_exit_idx = idx + 1
                    break
                if row['low'] <= sl_price: 
                    outcome = "LOSS"; losses += 1
                    res_time = row['timestamp']
                    try:
                        last_exit_idx = df.index.get_indexer([res_time], method='ffill')[0]
                    except:
                        last_exit_idx = idx + 1
                    break
        
        n_trades = wins + losses
        win_rate = (wins / n_trades * 100) if n_trades > 0 else 0
        return n_trades, win_rate

    def run_discovery(self):
        print("\n" + "🔥"*20)
        print("💎 HYPER-DISCOVERY: VOLUME SCALING")
        print("🔥"*20)
        
        df_5m_raw = self.fetch_data('5m')
        df_15m_raw = self.fetch_data('15m')
        df_1h_raw = self.fetch_data('1h')
        
        df_5m = add_all_indicators(df_5m_raw)
        df_15m = add_all_indicators(df_15m_raw)
        df_1h = add_all_indicators(df_1h_raw)
        
        print("\n🔍 Calculating probabilities...")
        df_wh, probs_wh = self.get_probs(df_5m, df_15m, df_1h, target='wh')
        df_mtf, probs_mtf = self.get_probs(df_5m, df_15m, df_1h, target='mtf')
        
        print("\n📈 Sweeping thresholds for 5-6 trades/day (approx 40-50 trades total over 7.5 days active)...")
        
        results = []
        
        # Test 1: WH Sniper (1H)
        print("\nChecking WH (1H) volume sweep...")
        for t in np.arange(0.30, 0.60, 0.05):
            n, wr = self.simulate_threshold(df_wh, df_5m_raw, probs_wh, t, 0.015, 0.008)
            results.append({'model': 'Winner Hunter (1H)', 'thresh': t, 'trades': n, 'win_rate': wr, 'tp': 0.015, 'sl': 0.008})
            
        # Test 2: MTF Scalper (5M)
        print("Checking MTF Scalper (5M) volume sweep...")
        for t in np.arange(0.50, 0.96, 0.05):
            n, wr = self.simulate_threshold(df_mtf, df_5m_raw, probs_mtf, t, 0.015, 0.008)
            results.append({'model': 'MTF Scalper (5M)', 'thresh': t, 'trades': n, 'win_rate': wr, 'tp': 0.015, 'sl': 0.008})
            
        # Test 3: Gem Sniper (5M)
        print("Checking Gem Sniper (5M) volume sweep...")
        for t in np.arange(0.50, 0.91, 0.05):
            n, wr = self.simulate_threshold(df_mtf, df_5m_raw, probs_mtf, t, 0.003, 0.005)
            results.append({'model': 'Gem Sniper (5M)', 'thresh': t, 'trades': n, 'win_rate': wr, 'tp': 0.003, 'sl': 0.005})

        res_df = pd.DataFrame(results)
        print("\n" + "="*80)
        print("🎯 DISCOVERY RESULTS: FREQUENCY VS PRECISION")
        print("="*80)
        print(res_df.to_string(index=False))
        
        # Find best combination for ~45 trades total
        print("\n" + "="*80)
        print("👑 RECOMMENDED VOLUME CONFIGURATION")
        print("="*80)
        
        # We need sum(trades) ~ 45
        # Example: WH@0.40 (X trades) + MTF@0.80 (Y trades) + Gem@0.75 (Z trades)
        # Let's look for high win rates first.
        
        high_precision = res_df[res_df['win_rate'] >= 90]
        print("\nRows with 90%+ Win Rate:")
        print(high_precision.to_string(index=False))

if __name__ == "__main__":
    HyperDiscovery().run_discovery()
