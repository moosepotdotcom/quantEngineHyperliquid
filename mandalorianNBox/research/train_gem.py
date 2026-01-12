
import sys
import os
import pandas as pd
import numpy as np
import backtrader as bt
import xgboost as xgb

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../dashboard'))

from research.train_legacy_models import DataCollectorMixin
from dashboard.strategies_complete import RSIStrategy

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(PROJECT_ROOT, 'models')

# Define the Gem Strategy Class with fixed params
class AIGemV1(RSIStrategy):
    params = (
        ('rsi_period', 10),
        ('rsi_oversold', 30),
        ('rsi_overbought', 70),
    )

def train_gem():
    print("💎 Training AI GEM V1 Model...")
    
    data_path = os.path.join(PROJECT_ROOT, 'data', 'BTC_1h.csv')
    if not os.path.exists(data_path):
        print("❌ Data not found")
        return
        
    df = pd.read_csv(data_path, parse_dates=True, index_col='timestamp')
    if 'datetime' in df.columns: df.drop(columns=['datetime'], inplace=True)
    
    cerebro = bt.Cerebro()
    cerebro.adddata(bt.feeds.PandasData(dataname=df))
    
    # Use the Mixin to verify signals
    class GemTrainer(DataCollectorMixin, AIGemV1):
        pass
        
    cerebro.addstrategy(GemTrainer)
    cerebro.run()
    
    strat = cerebro.runstrats[0][0]
    X = np.array(strat.features)
    y = np.array(strat.labels)
    
    if len(X) == 0:
        print("⚠️ No trades to train on")
        return
        
    print(f"   Collected {len(X)} samples. Win Rate: {np.mean(y):.2%}")
    
    model = xgb.XGBClassifier(n_estimators=100, max_depth=3, learning_rate=0.1)
    model.fit(X, y)
    
    model_path = os.path.join(MODELS_DIR, 'ai_gem_v1_xgb.json')
    model.save_model(model_path)
    print(f"✅ Gem Model Saved: {model_path}")

if __name__ == '__main__':
    train_gem()
