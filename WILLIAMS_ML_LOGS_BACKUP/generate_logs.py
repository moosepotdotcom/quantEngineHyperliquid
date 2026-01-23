#!/usr/bin/env python3
"""
GENERATE DETAILED TRADE LOGS (OPTIMIZED V1)
Target: Jan 2 - Jan 23
Settings: TP 0.9% | SL 2.0% | Conf 0.65
Output: CSV-style log for review
"""

import pandas as pd
import numpy as np
import requests
import xgboost as xgb
import os
import sys

# Import components
sys.path.append(os.getcwd())
try:
    from trend_filter import get_market_regime, should_trade
except ImportError:
    print("❌ Run from WILLIAMS_ML_STRATEGY_FINAL directory")
    exit(1)

# Load Model
model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model_v1.json')
xgb_model = xgb.XGBClassifier()
xgb_model.load_model(model_path)

FEATURES = ['williams_r', 'rsi_14', 'atr_14', 'vol_change', 'ema_200_dist']
PERIOD = 21

# Data Fetch
def fetch_data(coin):
    url = "https://api.hyperliquid.xyz/info"
    start_ts = int(pd.Timestamp("2026-01-02").timestamp() * 1000)
    end_ts = int(pd.Timestamp("2026-01-23").timestamp() * 1000)
    
    all_data = []
    curr = end_ts
    while curr > start_ts:
        start = int(max(start_ts, curr - (2000 * 5 * 60 * 1000)))
        curr_int = int(curr)
        req = {"type": "candleSnapshot", "req": {"coin": coin, "interval": "5m", "startTime": start, "endTime": curr_int}}
        try:
            resp = requests.post(url, json=req, timeout=10).json()
            if not resp: break
            chunk = pd.DataFrame(resp)
            all_data.append(chunk)
            curr = chunk.iloc[0]['t'] - 1
        except: break
            
    df = pd.concat(all_data).sort_values('t').drop_duplicates('t').reset_index(drop=True)
    df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
    cols = ['o', 'h', 'l', 'c', 'v']
    new_cols = ['open', 'high', 'low', 'close', 'volume']
    for c, n in zip(cols, new_cols):
        df[n] = df[c].astype(float)
        
    # Features
    df['high_roll'] = df['high'].rolling(PERIOD).max()
    df['low_roll'] = df['low'].rolling(PERIOD).min()
    denom = (df['high_roll'] - df['low_roll']).replace(0, np.nan)
    df['williams_r'] = -100 * (df['high_roll'] - df['close']) / denom
    df['williams_r_prev'] = df['williams_r'].shift(1)
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi_14'] = 100 - (100 / (1 + rs))
    
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift(1)).abs()
    tr3 = (df['low'] - df['close'].shift(1)).abs()
    df['atr_14'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1).rolling(14).mean()
    
    df['vol_change'] = df['volume'].pct_change()
    ema = df['close'].ewm(span=200, adjust=False).mean()
    df['ema_200_dist'] = (df['close'] - ema) / ema
    
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    df = df.dropna().reset_index(drop=True)
    X = df[FEATURES].values
    df['proba'] = xgb_model.predict_proba(X)[:, 1]
    
    return df

COINS = ['BTC', 'ETH', 'SOL', 'AVAX', 'SUI']
print("📥 Fetching Data...")
DATA = {c: fetch_data(c) for c in COINS}

# Simulation
def generate_log(tp_pct, sl_pct):
    all_trades = []
    
    for coin, df in DATA.items():
        in_trade = False
        trade = {}
        
        for i, row in df.iterrows():
            if in_trade:
                curr_h, curr_l = row['high'], row['low']
                win, loss = False, False
                
                # Check outcome
                if trade['dir'] == 'LONG':
                    if curr_l <= trade['sl']: loss = True
                    elif curr_h >= trade['tp']: win = True
                else: 
                    if curr_h >= trade['sl']: loss = True
                    elif curr_l <= trade['tp']: win = True
                    
                if win or loss:
                    trade['exit_time'] = row['timestamp']
                    trade['outcome'] = 'WIN' if win else 'LOSS'
                    trade['pnl_pct'] = tp_pct if win else -sl_pct
                    all_trades.append(trade)
                    in_trade = False
                    trade = {}
                continue
            
            # Entry
            if row['proba'] < 0.65: continue
            wr = row['williams_r']
            wr_p = row['williams_r_prev']
            
            signal = None
            if wr_p < -20 and wr >= -20: signal = 'LONG'
            elif wr_p > -80 and wr <= -80: signal = 'SHORT'
            
            if signal:
                e20, e50 = row['ema_20'], row['ema_50']
                regime = 'RANGING'
                if e20 > e50 * 1.001: regime = 'BULLISH'
                elif e20 < e50 * 0.999: regime = 'BEARISH'
                
                allowed, reason = should_trade(signal, regime)
                if not allowed: continue
                
                in_trade = True
                entry = row['close']
                tp = entry * (1 + tp_pct) if signal == 'LONG' else entry * (1 - tp_pct)
                sl = entry * (1 - sl_pct) if signal == 'LONG' else entry * (1 + sl_pct)
                
                trade = {
                    'coin': coin,
                    'entry_time': row['timestamp'],
                    'dir': signal,
                    'price': entry,
                    'tp': tp,
                    'sl': sl,
                    'regime': regime
                }

    df_logs = pd.DataFrame(all_trades).sort_values('entry_time')
    return df_logs

print("\n🚀 GENERATING OPTIMIZED LOGS (TP 0.9% / SL 2.0%)")
df_logs = generate_log(0.009, 0.020)

# 1. SAVE TO CSV
csv_path = "OPTIMIZED_TRADES_JAN2_JAN23.csv"
df_logs.to_csv(csv_path, index=False)
print(f"✅ Saved full logs to {csv_path}")

# 2. ANALYSIS
print("\n🔎 INTERESTING OBSERVATIONS")

# A. Streaks
df_logs['win'] = df_logs['outcome'] == 'WIN'
# Magic one-liner for streaks
df_logs['streak_grp'] = (df_logs['win'] != df_logs['win'].shift()).cumsum()
streaks = df_logs.groupby(['streak_grp', 'win']).size()
max_win_streak = streaks[streaks.index.get_level_values(1) == True].max()
max_loss_streak = streaks[streaks.index.get_level_values(1) == False].max()

print(f"🔥 Longest Winning Streak: {max_win_streak} trades")
print(f"❄️ Longest Losing Streak: {max_loss_streak} trades")

# B. Best Coin
coin_metrics = df_logs.groupby('coin').apply(lambda x: pd.Series({
    'trades': len(x),
    'wr': (x['outcome']=='WIN').mean() * 100,
    'pnl_sum': x['pnl_pct'].sum() * 100 # Sum of % PnL
}))
best_coin = coin_metrics.sort_values('pnl_sum', ascending=False).iloc[0]
worst_coin = coin_metrics.sort_values('pnl_sum', ascending=True).iloc[0]

print(f"👑 MVP Coin: {best_coin.name} ({best_coin['trades']} trades, {best_coin['wr']:.1f}% WR, Total PnL +{best_coin['pnl_sum']:.1f}%)")

# C. Hourly Edge
df_logs['hour'] = df_logs['entry_time'].dt.hour
hourly_wr = df_logs.groupby('hour')['win'].mean() * 100
best_hour = hourly_wr.idxmax()
print(f"⏰ Golden Hour: {best_hour}:00 UTC (Win Rate: {hourly_wr.max():.1f}%)")

# 3. EXPORT MARKDOWN REPORT
md_path = "TRADE_LOG_ANALYSIS.md"
with open(md_path, "w") as f:
    f.write("# 📊 Trade Log Analysis (Optimized V1)\n")
    f.write(f"**Period**: Jan 2 - Jan 23\n")
    f.write(f"**Settings**: TP 0.9% | SL 2.0%\n\n")
    
    f.write("## 💡 Key Observations\n")
    f.write(f"- **Consistency**: The strategy hit a max winning streak of **{max_win_streak} trades** in a row.\n")
    f.write(f"- **Top Performer**: **{best_coin.name}** was the most profitable asset.\n")
    f.write(f"- **Best Time**: Trading around **{best_hour}:00 UTC** yielded the highest reliability.\n\n")
    
    f.write("## 📝 Complete Trade Log\n")
    f.write("| Time (UTC) | Coin | Dir | Price | Outcome | PnL |\n")
    f.write("|---|---|---|---|---|---|\n")
    for i, row in df_logs.iterrows():
        icon = "✅" if row['outcome'] == 'WIN' else "❌"
        pnl = f"{row['pnl_pct']*100:+.1f}%"
        f.write(f"| {row['entry_time']} | **{row['coin']}** | {row['dir']} | ${row['price']:.4f} | {icon} {row['outcome']} | {pnl} |\n")

print(f"✅ Analysis Report generated: {md_path}")

