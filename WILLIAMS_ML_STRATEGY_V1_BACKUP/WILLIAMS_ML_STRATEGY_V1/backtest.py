
import pandas as pd
import numpy as np
import xgboost as xgb
import os
import glob
import json

# --- CONFIG ---
DATA_DIR = '../training/data/5m_3months' # Relative path to data
MODEL_PATH = 'model_v1.json'
PERIOD = 21
TP_PCT = 0.007
SL_PCT = 0.015
FEE_PCT = 0.00035
CONF_THRESH = 0.65

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

def run_backtest():
    print("🧪 Running Backtest (Bundle Version)...")
    
    # Load Model
    if not os.path.exists(MODEL_PATH):
        print(f"❌ Model not found: {MODEL_PATH}. Run train_model.py first.")
        return
        
    model = xgb.XGBClassifier()
    model.load_model(MODEL_PATH)
    
    # Load Data
    search_path = os.path.join(os.path.dirname(__file__), '../training/data/5m_3months')
    files = glob.glob(os.path.join(search_path, "*_5m_3mo.csv"))
    
    if not files:
        print(f"❌ No data found in {search_path}.")
        return 
        
    all_trades = []
    
    features = ['williams_r', 'rsi_14', 'atr_14', 'vol_change', 'ema_200_dist']
    
    for f in files:
        coin = os.path.basename(f).split('_')[0]
        df = pd.read_csv(f)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.sort_values('timestamp', inplace=True)
        
        df = add_features(df)
        
        # Predict
        X = df[features].replace([np.inf, -np.inf], np.nan).fillna(0)
        probs = model.predict_proba(X)[:, 1]
        df['conf'] = probs
        
        # Sim Loop
        position = None
        trades = []
        
        for i in range(len(df)):
            row = df.iloc[i]
            
            # Manage Position
            if position:
                outcome=None; exit_px=0
                if position['type'] == 'LONG':
                    if row['high'] >= position['tp']: outcome='WIN'; exit_px=position['tp']
                    elif row['low'] <= position['sl']: outcome='LOSS'; exit_px=position['sl']
                else:
                    if row['low'] <= position['tp']: outcome='WIN'; exit_px=position['tp']
                    elif row['high'] >= position['sl']: outcome='LOSS'; exit_px=position['sl']
                    
                if outcome:
                    pnl = (exit_px - position['entry']) / position['entry']
                    if position['type'] == 'SHORT': pnl = -pnl
                    pnl -= (FEE_PCT*2)
                    trades.append({'coin':coin, 'outcome':outcome, 'pnl':pnl, 'ts':row['timestamp']})
                    position = None
                continue
            
            # Entry Signal
            curr_wr = row['williams_r']
            prev_wr = row['williams_r_prev']
            conf = row['conf']
            
            if conf < CONF_THRESH: continue
            
            if (prev_wr < -20 and curr_wr >= -20): # Long
                entry = row['close']
                position={'type':'LONG', 'entry':entry, 'tp':entry*(1+TP_PCT), 'sl':entry*(1-SL_PCT)}
                
            elif (prev_wr > -80 and curr_wr <= -80): # Short
                entry = row['close']
                position={'type':'SHORT', 'entry':entry, 'tp':entry*(1-TP_PCT), 'sl':entry*(1+SL_PCT)}
        
        all_trades.extend(trades)
        
    # Results
    if all_trades:
        total = len(all_trades)
        wins = len([t for t in all_trades if t['outcome']=='WIN'])
        wr = wins/total * 100
        pnl = sum([t['pnl'] for t in all_trades]) * 100
        
        print(f"\n📊 Backtest Results:")
        print(f"   Total Trades: {total}")
        print(f"   Win Rate:     {wr:.2f}%")
        print(f"   Total PnL:    {pnl:.2f}%")
        
        # Save Log
        pd.DataFrame(all_trades).to_csv('trades.csv', index=False)
        print("   💾 Log saved to trades.csv")
    else:
        print("   ⚠️ No trades generated.")

if __name__ == "__main__":
    run_backtest()
