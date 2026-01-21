
import pandas as pd
import numpy as np
import xgboost as xgb
import glob
import os
import json

# --- CONFIG ---
DATA_DIR = '../training/data/5m_3months' # Relative path to data (adjust if needed, or use 'data')
# Since this script is inside WILLIAMS_ML_STRATEGY_V1, and data is in ../training/data/5m_3months...
# But for the export bundle, expecting data in ./data folder?
# Let's support both or just point to where we downloaded data.
# For bundle export, I should probably copy data to ./data, but user might want to train on existing data.
# I'll point to the 5m_3months directory as default for now.

PERIOD = 21
TP_PCT = 0.007 # 0.7%
SL_PCT = 0.015 # 1.5%
FEE_PCT = 0.00035

def add_features(df):
    df = df.copy()
    # Williams %R
    high = df['high'].rolling(PERIOD).max()
    low = df['low'].rolling(PERIOD).min()
    denom = (high - low).replace(0, np.nan)
    df['williams_r'] = -100 * (high - df['close']) / denom
    df['williams_r_prev'] = df['williams_r'].shift(1)
    
    # RSI 14
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi_14'] = 100 - (100 / (1 + rs))
    
    # ATR 14
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift(1)).abs()
    tr3 = (df['low'] - df['close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr_14'] = tr.rolling(14).mean()
    
    # Volume Change
    df['vol_change'] = df['volume'].pct_change()
    
    # EMA Distance
    ema = df['close'].ewm(span=200, adjust=False).mean()
    df['ema_200_dist'] = (df['close'] - ema) / ema
    
    return df.dropna()

def label_data(df):
    df = df.copy()
    df['target'] = 0
    
    # Signals
    wr = df['williams_r']
    wr_prev = df['williams_r_prev']
    
    # Long: Cross above -20
    long_signals = (wr_prev < -20) & (wr >= -20)
    # Short: Cross below -80
    short_signals = (wr_prev > -80) & (wr <= -80)
    
    signals_indices = df.index[long_signals | short_signals]
    
    for idx in signals_indices:
        if idx + 144 >= len(df): continue
            
        row = df.loc[idx]
        entry = row['close']
        is_long = (row['williams_r_prev'] < -20)
        
        outcome = 0
        future = df.loc[idx+1 : idx+1+144] # ~12 hours max hold
        
        if is_long:
            tp_px = entry * (1 + TP_PCT)
            sl_px = entry * (1 - SL_PCT)
            
            hits_tp = future[future['high'] >= tp_px]
            hits_sl = future[future['low'] <= sl_px]
            
            first_tp = hits_tp.index[0] if not hits_tp.empty else 999999999
            first_sl = hits_sl.index[0] if not hits_sl.empty else 999999999
            
            if first_tp < first_sl: outcome = 1
        else:
            tp_px = entry * (1 - TP_PCT)
            sl_px = entry * (1 + SL_PCT)
            
            hits_tp = future[future['low'] <= tp_px]
            hits_sl = future[future['high'] >= sl_px]
            
            first_tp = hits_tp.index[0] if not hits_tp.empty else 999999999
            first_sl = hits_sl.index[0] if not hits_sl.empty else 999999999
            
            if first_tp < first_sl: outcome = 1
            
        df.loc[idx, 'target'] = outcome
        
    return df[long_signals | short_signals].copy()

def train():
    print("🚀 Training Final Model (All 5m Data)...")
    
    # Handle path resolution to find the training data
    # Assuming script is run from inside 'WILLIAMS_ML_STRATEGY_V1'
    # And data is in '../../training/data/5m_3months'
    # Try looking for data
    
    search_path = os.path.join(os.path.dirname(__file__), '../training/data/5m_3months')
    files = glob.glob(os.path.join(search_path, "*_5m_3mo.csv"))
    
    if not files:
        print(f"❌ No data found in {search_path}. Please check path.")
        return

    dfs = []
    for f in files:
        df = pd.read_csv(f)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.sort_values('timestamp', inplace=True)
        
        df = add_features(df)
        signals = label_data(df)
        if not signals.empty:
            dfs.append(signals)
            
    mega_df = pd.concat(dfs, ignore_index=True)
    print(f"📚 Training on {len(mega_df)} total signals.")
    print(f"   Baseline Win Rate: {mega_df['target'].mean()*100:.2f}%")
    
    features = ['williams_r', 'rsi_14', 'atr_14', 'vol_change', 'ema_200_dist']
    X = mega_df[features].replace([np.inf, -np.inf], np.nan).fillna(0)
    y = mega_df['target']
    
    model = xgb.XGBClassifier(n_estimators=200, max_depth=6, learning_rate=0.03, objective='binary:logistic')
    model.fit(X, y)
    
    model_path = os.path.join(os.path.dirname(__file__), 'model_v1.json')
    model.save_model(model_path)
    print(f"✅ Model saved to {model_path}")

if __name__ == "__main__":
    train()
