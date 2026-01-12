import pandas as pd
import numpy as np
import os
import json
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier

# Mock the indicators to avoid complex dependencies
def add_indicators(df):
    # Simplistic version for audit
    df = df.copy()
    df['c'] = df['c'].astype(float)
    df['h'] = df['h'].astype(float)
    df['l'] = df['l'].astype(float)
    df['o'] = df['o'].astype(float)
    df['v'] = df['v'].astype(float)
    return df

print("🕵️‍♂️ FULL BACKTRACK AUDIT - GEM SNIPER 0.75")
print("="*70)

# Load model paths
MODEL_DIR = 'models'
gem_prefix = os.path.join(MODEL_DIR, 'gem_sniper_5m_trio_')

try:
    # Load Gem Sniper (5M) Trio
    gem_xgb = xgb.XGBClassifier()
    gem_xgb.load_model(f'{gem_prefix}xgb.json')
    gem_lgb = lgb.Booster(model_file=f'{gem_prefix}lgb.json')
    gem_cat = CatBoostClassifier()
    gem_cat.load_model(f'{gem_prefix}cat.json')
    print("✅ Models Loaded")
except Exception as e:
    print(f"❌ Model Load Error: {e}")
    sys.exit(1)

# Note: The models expect specific features. 
# Reconstructing them exactly is hard without quant_engine's add_all_indicators.
# Let's just use the TradingEngine directly on the files if possible.

from quant_engine import TradingEngine
engine = TradingEngine()

# We need to feed the engine the data.
# But engine fetches it live.
# Let's mock the 'self.tracker.get_recent_data' if it exists.
# Actually, lets just look at the logs for Check #1-20 again.
