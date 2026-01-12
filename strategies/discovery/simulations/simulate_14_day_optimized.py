#!/usr/bin/env python3
"""
🚀 OPTIMIZED 14-DAY SIMULATION: $53 TO ???
Period: Last 14 Days
Start: $53 USD
Position: 0.02 BTC
Thresholds: Gem 0.75, MTF 0.90, WH 0.47
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

class OptimizedSimulation:
    def __init__(self, initial_balance=53.0, pos_size_btc=0.02):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.pos_size_btc = pos_size_btc
        
        # Load Models
        print("📦 Loading Trio Ensemble Models...")
        self.wh_prefix = os.path.join(MODEL_DIR, 'winner_hunter_1h_trio_')
        self.mtf_prefix = os.path.join(MODEL_DIR, 'mtf_scalper_5m_trio_')
        
        self.mtf_xgb = xgb.XGBClassifier(); self.mtf_xgb.load_model(f'{self.mtf_prefix}xgb.json')
        self.mtf_lgb = lgb.Booster(model_file=f'{self.mtf_prefix}lgb.json')
        self.mtf_cat = CatBoostClassifier(); self.mtf_cat.load_model(f'{self.mtf_prefix}cat.json')
        
        self.wh_xgb = xgb.XGBClassifier(); self.wh_xgb.load_model(f'{self.wh_prefix}xgb.json')
        self.wh_lgb = lgb.Booster(model_file=f'{self.wh_prefix}lgb.json')
        self.wh_cat = CatBoostClassifier(); self.wh_cat.load_model(f'{self.wh_prefix}cat.json')

    def fetch_data(self, interval, days=15):
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

    def get_wh_probs(self, df_5m, df_15m, df_1h):
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

    def get_mtf_probs(self, df_5m, df_15m, df_1h):
        exclude = ['open', 'high', 'low', 'close', 'volume']
        df_5m_idx = df_5m.set_index('timestamp')
        df_15m_idx = df_15m.set_index('timestamp')
        df_1h_idx = df_1h.set_index('timestamp')
        
        base_df = df_5m_idx.copy()
        ctx_1h = df_1h_idx[[c for c in df_1h_idx.columns if c not in exclude]].copy()
        ctx_1h.columns = [f"{c}_1h" for c in ctx_1h.columns]
        ctx_15m = df_15m_idx[[c for c in df_15m_idx.columns if c not in exclude]].copy()
        ctx_15m.columns = [f"{c}_15m" for c in ctx_15m.columns]
        df_final = pd.concat([base_df, ctx_1h.reindex(base_df.index, method='ffill'), ctx_15m.reindex(base_df.index, method='ffill')], axis=1).dropna()
        X = np.nan_to_num(df_final[[c for c in df_final.columns if c not in exclude]].values, nan=0.0)
        probs = (self.mtf_xgb.predict_proba(X)[:,1] + self.mtf_lgb.predict(X) + self.mtf_cat.predict_proba(X)[:,1]) / 3
        return df_final, probs

    def run_simulation(self):
        print(f"💰 Start Balance: ${self.balance}")
        print(f"📦 Position Size: {self.pos_size_btc} BTC")
        
        df_5m_raw = self.fetch_data('5m')
        df_15m_raw = self.fetch_data('15m')
        df_1h_raw = self.fetch_data('1h')
        
        print("🔧 Engineering features...")
        df_5m = add_all_indicators(df_5m_raw)
        df_15m = add_all_indicators(df_15m_raw)
        df_1h = add_all_indicators(df_1h_raw)
        
        df_wh, probs_wh = self.get_wh_probs(df_5m, df_15m, df_1h)
        df_5m_mtf, probs_5m = self.get_mtf_probs(df_5m, df_15m, df_1h)
        
        configs = [
            {'name': 'Winner Hunter (1H)', 'df': df_wh, 'probs': probs_wh, 'thresh': 0.47, 'tp': 0.015, 'sl': 0.008},
            {'name': 'MTF Scalper (5M)',   'df': df_5m_mtf, 'probs': probs_5m, 'thresh': 0.90, 'tp': 0.015, 'sl': 0.008},
            {'name': 'Gem Sniper (5M)',    'df': df_5m_mtf, 'probs': probs_5m, 'thresh': 0.75, 'tp': 0.003, 'sl': 0.005}
        ]
        
        trades = []
        last_exit_time = pd.Timestamp.min
        
        # Combine all signals and sort by time
        potential_signals = []
        for cfg in configs:
            sig_indices = np.where(cfg['probs'] >= cfg['thresh'])[0]
            for idx in sig_indices:
                potential_signals.append({
                    'time': cfg['df'].index[idx],
                    'price': cfg['df'].iloc[idx]['close'],
                    'cfg': cfg
                })
        
        potential_signals.sort(key=lambda x: x['time'])
        
        for sig in potential_signals:
            if sig['time'] <= last_exit_time: continue
            if self.balance <= 0: break
            
            entry_time = sig['time']
            entry_price = sig['price']
            cfg = sig['cfg']
            
            tp_price = entry_price * (1 + cfg['tp'])
            sl_price = entry_price * (1 - cfg['sl'])
            
            # Position Value
            pos_value = self.pos_size_btc * entry_price
            leverage = pos_value / self.balance
            
            df_verify = df_5m_raw[df_5m_raw['timestamp'] >= entry_time]
            
            outcome = "OPEN"
            for _, row in df_verify.iterrows():
                if row['high'] >= tp_price: 
                    outcome = "WIN"; pnl = cfg['tp'] * pos_value; break
                if row['low'] <= sl_price: 
                    outcome = "LOSS"; pnl = -cfg['sl'] * pos_value; break
            
            if outcome != "OPEN":
                self.balance += pnl
                last_exit_time = row['timestamp']
                trades.append({
                    'Time': entry_time,
                    'Model': cfg['name'],
                    'Entry': f"${entry_price:,.0f}",
                    'Lev': f"{leverage:.1f}x",
                    'Result': "✅" if outcome == "WIN" else "❌",
                    'PnL $': f"{pnl:+.2f}",
                    'Balance': f"${self.balance:,.2f}"
                })

        report = pd.DataFrame(trades)
        print("\n" + "="*80)
        print(f"📊 OPTIMIZED 14-DAY GROWTH: {self.pos_size_btc} BTC @ {self.initial_balance} Start")
        print("="*80)
        print(report.to_string(index=False) if not report.empty else "No trades found.")
        
        print("\n" + "="*80)
        print("📈 FINAL STATS")
        print("="*80)
        print(f"🏁 Starting Balance: ${self.initial_balance}")
        print(f"🏆 Final Balance:    ${self.balance:,.2f}")
        print(f"💰 Total PnL $:      ${(self.balance - self.initial_balance):,.2f}")
        print(f"📈 Total Return %:   {((self.balance - self.initial_balance)/self.initial_balance*100):,.1f}%")
        print(f"📊 Total Trades:     {len(trades)}")
        print(f"✅ Wins:             {sum(report['Result'] == '✅') if not report.empty else 0}")
        print(f"❌ Losses:           {sum(report['Result'] == '❌') if not report.empty else 0}")
        print("="*80)

if __name__ == "__main__":
    OptimizedSimulation().run_simulation()
