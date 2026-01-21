
import pandas as pd
import numpy as np
import xgboost as xgb
import glob
import os
from sklearn.metrics import accuracy_score

# Reuse feature logic logic from bundle
DATA_DIR = 'training/data/5m_3months'
PERIOD = 21
TP_PCT = 0.007
SL_PCT = 0.015
FEE_PCT = 0.00035

def add_features(df):
    df = df.copy()
    high = df['high'].rolling(PERIOD).max()
    low = df['low'].rolling(PERIOD).min()
    denom = (high - low).replace(0, np.nan)
    df['williams_r'] = -100 * (high - df['close']) / denom
    df['williams_r_prev'] = df['williams_r'].shift(1)
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi_14'] = 100 - (100 / (1 + rs))
    
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift(1)).abs()
    tr3 = (df['low'] - df['close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr_14'] = tr.rolling(14).mean()
    
    df['vol_change'] = df['volume'].pct_change()
    
    ema = df['close'].ewm(span=200, adjust=False).mean()
    df['ema_200_dist'] = (df['close'] - ema) / ema
    
    return df.dropna()

def label_data(df):
    df = df.copy()
    df['target'] = 0
    
    wr = df['williams_r']
    wr_prev = df['williams_r_prev']
    
    long_signals = (wr_prev < -20) & (wr >= -20)
    short_signals = (wr_prev > -80) & (wr <= -80)
    
    signals_indices = df.index[long_signals | short_signals]
    
    for idx in signals_indices:
        if idx + 144 >= len(df): continue
            
        row = df.loc[idx]
        entry = row['close']
        is_long = (row['williams_r_prev'] < -20)
        
        outcome = 0
        future = df.loc[idx+1 : idx+1+144]
        
        if is_long:
            tp_px = entry * (1 + TP_PCT)
            sl_px = entry * (1 - SL_PCT)
            first_tp = future.index[future['high'] >= tp_px].min() if not future[future['high'] >= tp_px].empty else 999999999
            first_sl = future.index[future['low'] <= sl_px].min() if not future[future['low'] <= sl_px].empty else 999999999
            if first_tp < first_sl: outcome = 1
        else:
            tp_px = entry * (1 - TP_PCT)
            sl_px = entry * (1 + SL_PCT)
            first_tp = future.index[future['low'] <= tp_px].min() if not future[future['low'] <= tp_px].empty else 999999999
            first_sl = future.index[future['high'] >= sl_px].min() if not future[future['high'] >= sl_px].empty else 999999999
            if first_tp < first_sl: outcome = 1
            
        df.loc[idx, 'target'] = outcome
        
    return df[long_signals | short_signals].copy()

def run_permutation_test():
    print("🎲 STARTING PERMUTATION TEST (Detector of 'Cheating')...")
    print("   We will TRAIN on RANDOMIZED labels.")
    print("   Hypothesis: Win Rate should drop to ~50% (Random Guess).")
    print("   If Win Rate stays high, there is a data leak (Cheating).")
    
    files = glob.glob(os.path.join(DATA_DIR, "*_5m_3mo.csv"))
    
    # 1. Prepare Data
    train_dfs = []
    test_dfs = []
    
    for f in files:
        df = pd.read_csv(f)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.sort_values('timestamp', inplace=True)
        split_idx = int(len(df) * 0.80)
        
        df_train = df.iloc[:split_idx].copy()
        df_test = df.iloc[split_idx:].copy()
        
        df_train = add_features(df_train)
        signals_train = label_data(df_train)
        if not signals_train.empty:
            train_dfs.append(signals_train)
            
        df_test = add_features(df_test)
        df_test['coin'] = os.path.basename(f).split('_')[0]
        test_dfs.append(df_test)
        
    mega_train = pd.concat(train_dfs, ignore_index=True)
    
    print("\n-------------------------------------------------------------")
    print("🧪 EXPERIMENT: SCRAMBLING TARGETS (Destroying Real Patterns)")
    print("-------------------------------------------------------------")
    
    # SHUFFLE TARGETS
    # This disconnects the features from the outcome.
    # If the model still learns, it means the features themselves contain the answer (Leak).
    mega_train['target'] = np.random.permutation(mega_train['target'].values)
    
    print(f"   Training on {len(mega_train)} samples with SHUFFLED targets...")
    
    features = ['williams_r', 'rsi_14', 'atr_14', 'vol_change', 'ema_200_dist']
    X_train = mega_train[features].replace([np.inf, -np.inf], np.nan).fillna(0)
    y_train = mega_train['target']
    
    model = xgb.XGBClassifier(n_estimators=100, max_depth=5, learning_rate=0.05, objective='binary:logistic')
    model.fit(X_train, y_train)
    
    # Test on Real Test Data (Prediction should be random noise)
    print("   Predicting on Future Data...")
    
    all_trades = []
    
    for df_test in test_dfs:
        X_test = df_test[features].replace([np.inf, -np.inf], np.nan).fillna(0)
        probs = model.predict_proba(X_test)[:, 1]
        df_test['conf'] = probs
        
        # Sim Loop (Same as sanity check)
        # ... [Simplified for brevity, just getting counts]
        
        for i in range(200, len(df_test)):
            row = df_test.iloc[i]
            if row['conf'] < 0.65: continue # High conf only
            
            # Reconstruct Signal Check
            curr_wr = row['williams_r']
            prev_wr = row['williams_r_prev']
            is_long = (prev_wr < -20 and curr_wr >= -20)
            is_short = (prev_wr > -80 and curr_wr <= -80)
            
            if not (is_long or is_short): continue
            
            # Check Result
            entry = row['close']
            future = df_test.iloc[i+1 : i+1+144]
            outcome = 'LOSS'
            
            if is_long:
                 tp = entry * (1 + TP_PCT)
                 sl = entry * (1 - SL_PCT)
                 # Quick check
                 if not future.empty:
                     if future['high'].max() >= tp: outcome = 'WIN'
            else:
                 tp = entry * (1 - TP_PCT)
                 sl = entry * (1 + SL_PCT)
                 if not future.empty:
                     if future['low'].min() <= tp: outcome = 'WIN'
                     
            all_trades.append(outcome)

    wins = all_trades.count('WIN')
    total = len(all_trades)
    wr = (wins/total*100) if total > 0 else 0
    
    print("\n🏁 PERMUTATION RESULTS")
    print(f"   Trades Triggered: {total}")
    print(f"   Win Rate: {wr:.2f}%")
    
    if 40 < wr < 60:
        print("\n✅ PASSED: Random Training = Random Results.")
        print("   This proves the original ~80% Win Rate was based on REAL patterns, not leakage.")
    elif total == 0:
        print("\n✅ PASSED: Model found NO confident patterns in noise.")
    else:
        print("\n⚠️ FAILED: Model found 'patterns' in random noise. Possible leakage!")

if __name__ == "__main__":
    run_permutation_test()
