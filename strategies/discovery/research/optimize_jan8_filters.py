
import pandas as pd
import numpy as np
import json
import joblib
import os
from sklearn.tree import DecisionTreeClassifier, export_text
from datetime import datetime

# Files
LOG_FILE = 'logs/trades/predictions_20260108.jsonl'
HIST_FILE = 'jan8_historical_1m.json'
MODEL_FILE = 'models/mtf_scalper_5m_v2_calibrated.pkl'

print("🚀 Starting AI Filter Optimization...")

# 1. Load Historical Data for Simulation
print("📥 Loading Historical Data...")
with open(HIST_FILE, 'r') as f:
    candles = json.load(f)
df_1m = pd.DataFrame(candles)
df_1m['timestamp'] = pd.to_datetime(df_1m['t'], unit='ms')
df_1m['open'] = df_1m['o'].astype(float)
df_1m['high'] = df_1m['h'].astype(float)
df_1m['low'] = df_1m['l'].astype(float)
df_1m['close'] = df_1m['c'].astype(float)
df_1m['volume'] = df_1m['v'].astype(float)
df_1m.set_index('timestamp', inplace=True)
df_5m = df_1m.resample('5T').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna()

# 2. Load V2 Model
print("🤖 Loading V2 Model...")
try:
    model = joblib.load(MODEL_FILE)
except Exception as e:
    print(f"Error loading model: {e}")
    exit(1)

import sys
sys.path.append(os.getcwd())
from utils.feature_engineer import add_all_indicators

# Generate feature list dynamically to match reconstruction
print("🔧 Generatng feature list...")
dummy_df = pd.DataFrame({'open': [100]*50, 'high': [105]*50, 'low': [95]*50, 'close': [100]*50, 'volume': [1000]*50})
dummy_df = add_all_indicators(dummy_df)
exclude = ['open', 'high', 'low', 'close', 'volume']
base_cols = [c for c in dummy_df.columns if c not in exclude]
cols_15m = [f"{c}_15m" for c in base_cols]
cols_1h = [f"{c}_1h" for c in base_cols]
feature_names = base_cols + cols_15m + cols_1h
feature_names = [c for c in feature_names if 'hurst' not in c]

print(f"✅ Generated {len(feature_names)} features.")

# 3. Simulate and Collect Data
print("📜 Processing Logs...")
data = []
target_window_start = pd.Timestamp("2026-01-08 00:00:00")
target_window_end = pd.Timestamp("2026-01-08 01:00:00")

def simulate_outcome(entry_price, direction, timestamp, df):
    tp_pct = 0.015
    sl_pct = 0.008
    start_idx = df.index.get_indexer([timestamp], method='bfill')[0]
    future_candles = df.iloc[start_idx:start_idx+20] # 20 candles ~ 1.5h
    
    # Debug First Trade
    if not hasattr(simulate_outcome, "debugged"):
        print(f"\n🐛 DEBUG SIMULATION:")
        print(f"Entry: {entry_price}, TP: {entry_price * (1-tp_pct):.2f}, SL: {entry_price * (1+sl_pct):.2f}")
        print(f"Timestamp: {timestamp}")
        print(f"First Candle: \n{future_candles.iloc[0] if not future_candles.empty else 'EMPTY'}")
        simulate_outcome.debugged = True
        
    for i, row in future_candles.iterrows():
        if direction == 'SHORT':
            tp = entry_price * (1 - tp_pct)
            sl = entry_price * (1 + sl_pct)
            if row['low'] <= tp: return "WIN"
            if row['high'] >= sl: return "LOSS"
    return "OPEN"

with open(LOG_FILE, 'r') as f:
    for line in f:
        if "MTF Scalper" not in line: continue
        row = json.loads(line)
        ts = pd.to_datetime(row['timestamp'])
        
        if not (target_window_start <= ts <= target_window_end): continue
        if 'features' not in row: continue
        
        log_feats = row['features']
        
        # Build X
        X_val = []
        try:
            for fname in feature_names:
                X_val.append(log_feats.get(fname, 0.0))
        except Exception:
            continue
            
        X = np.array(X_val).reshape(1, -1)
        
        # Predict V2 Confidence
        probs = model.predict_proba(X)[0]
        v2_conf = probs[0] # Class 0 (Short)
        
        # Filter for candidates
        if v2_conf > 0.65: # Candidates for trade
            
            entry = row['market_data']['close']
            outcome = simulate_outcome(entry, "SHORT", ts, df_5m)
            
            if outcome in ["WIN", "LOSS"]:
                # Record
                record = {
                    'outcome': 1 if outcome == "WIN" else 0,
                    'outcome_str': outcome,
                    'timestamp': ts,
                    'v2_conf': v2_conf
                }
                # Add key features for DT
                for k in ['rsi_7', 'rsi_14', 'volume_surge', 'adx', 'stoch_k', 'cci', 'cmf']:
                    record[k] = log_feats.get(k, 0)
                
                data.append(record)

df = pd.DataFrame(data)
print(f"Analyzed {len(df)} High-Confidence Candidates.")
print(df[['timestamp', 'v2_conf', 'outcome_str']])

# 4. Train Decision Tree
print("\n🧠 Training AI Filter...")
feature_cols = ['rsi_7', 'rsi_14', 'volume_surge', 'adx', 'stoch_k', 'cci', 'cmf', 'v2_conf']
X = df[feature_cols]
y = df['outcome']

clf = DecisionTreeClassifier(max_depth=3, random_state=42, min_samples_leaf=2)
clf.fit(X, y)

print("\n--- AI RULES ---")
print(export_text(clf, feature_names=feature_cols))

# Check 00:30 specifically
print("\nDiagnostics for 00:30 Loss:")
loss_cand = df[df['timestamp'].astype(str).str.contains('00:30')]
if not loss_cand.empty:
    print(loss_cand.iloc[0])
