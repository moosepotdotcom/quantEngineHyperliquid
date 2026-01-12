#!/usr/bin/env python3
"""
🚀 AGGRESSIVE GROWTH SIMULATION: $60 TO THE MOON?
Start: $60 USD
Position: 0.02 BTC (Fixed)
Leverage: ~30x-50x
Model: Volume Optimized (Gem 0.75 / MTF 0.90)
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

class AggressiveSimulation:
    def __init__(self, initial_balance=60.0, pos_size_btc=0.02):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.pos_size_btc = pos_size_btc
        print(f"💰 Initial Balance: ${initial_balance}")
        print(f"📦 Position Size: {pos_size_btc} BTC")
        
        # Load Models
        print("📦 Loading Trio Ensemble...")
        self.wh_prefix = os.path.join(MODEL_DIR, 'winner_hunter_1h_trio_')
        self.mtf_prefix = os.path.join(MODEL_DIR, 'mtf_scalper_5m_trio_')
        self.mtf_xgb = xgb.XGBClassifier(); self.mtf_xgb.load_model(f'{self.mtf_prefix}xgb.json')
        self.mtf_lgb = lgb.Booster(model_file=f'{self.mtf_prefix}lgb.json')
        self.mtf_cat = CatBoostClassifier(); self.mtf_cat.load_model(f'{self.mtf_prefix}cat.json')

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
        df_5m_raw = self.fetch_data('5m')
        df_15m_raw = self.fetch_data('15m')
        df_1h_raw = self.fetch_data('1h')
        
        df_5m = add_all_indicators(df_5m_raw)
        df_15m = add_all_indicators(df_15m_raw)
        df_1h = add_all_indicators(df_1h_raw)
        
        df, probs = self.get_probs(df_5m, df_15m, df_1h)
        
        # Combined rules for 6 trades/day: Gem (0.75 thresh, 0.3%/0.5%) + MTF (0.90 thresh, 1.5%/0.8%)
        trades = []
        last_exit_time = pd.Timestamp.min
        
        # Track drawdown
        max_drawdown = 0
        peak_balance = self.balance
        
        for idx in range(len(df)):
            if df.index[idx] <= last_exit_time: continue
            
            # Check signals
            is_mtf = probs[idx] >= 0.90
            is_gem = probs[idx] >= 0.75
            
            if not is_mtf and not is_gem: continue
            
            # Setup
            entry_price = df.iloc[idx]['close']
            entry_time = df.index[idx]
            
            if is_mtf:
                tp_pct, sl_pct, name = 0.015, 0.008, "MTF Scalper"
            else:
                tp_pct, sl_pct, name = 0.003, 0.005, "Gem Sniper"
                
            tp_price = entry_price * (1 + tp_pct)
            sl_price = entry_price * (1 - sl_pct)
            
            # Position Value
            pos_value = self.pos_size_btc * entry_price
            leverage = pos_value / self.balance
            
            if self.balance <= 0: break # REKT
            
            # Outcome
            outcome = "OPEN"
            df_verify = df_5m_raw[df_5m_raw['timestamp'] >= entry_time]
            
            for _, row in df_verify.iterrows():
                if row['high'] >= tp_price: 
                    outcome = "WIN"; pnl = tp_pct * pos_value; break
                if row['low'] <= sl_price: 
                    outcome = "LOSS"; pnl = -sl_pct * pos_value; break
            
            if outcome != "OPEN":
                self.balance += pnl
                last_exit_time = row['timestamp']
                
                if self.balance > peak_balance: peak_balance = self.balance
                drawdown = (peak_balance - self.balance) / peak_balance * 100
                if drawdown > max_drawdown: max_drawdown = drawdown
                
                trades.append({
                    'Time': entry_time,
                    'Model': name,
                    'Price': f"${entry_price:,.0f}",
                    'Lev': f"{leverage:.1f}x",
                    'Result': "✅" if outcome == "WIN" else "❌",
                    'PnL $': f"{pnl:+.2f}",
                    'Balance': f"${self.balance:,.2f}"
                })

        # Report
        report = pd.DataFrame(trades)
        print("\n" + "="*80)
        print(f"🚀 AGGRESSIVE GROWTH REPORT: {self.pos_size_btc} BTC Position")
        print("="*80)
        print(report.to_string(index=False))
        
        print("\n" + "="*80)
        print("📊 FINAL STATS")
        print("="*80)
        print(f"🏁 Starting Balance: ${self.initial_balance}")
        print(f"🏆 Final Balance:    ${self.balance:,.2f}")
        print(f"📈 Total Return:     {((self.balance - self.initial_balance)/self.initial_balance*100):,.1f}%")
        print(f"📊 Total Trades:     {len(trades)}")
        print(f"✅ Wins:             {sum(report['Result'] == '✅')}")
        print(f"❌ Losses:           {sum(report['Result'] == '❌')}")
        print(f"📉 Max Drawdown:     {max_drawdown:.1f}%")
        print(f"⚠️  Risk of Liq:      {'Extremely Low' if max_drawdown < 15 else 'Moderate'}")
        print("="*80)

if __name__ == "__main__":
    AggressiveSimulation().run_simulation()
