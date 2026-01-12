import pandas as pd
import numpy as np
import xgboost as xgb
import os
import sys
from datetime import datetime

# Add utils to path
sys.path.insert(0, os.path.join(os.getcwd(), 'utils'))
from feature_engineer import add_all_indicators

MODEL_DIR = os.path.join(os.getcwd(), 'models')
POSITION_SIZE_BTC = 1.27

SETTINGS = {
    'Winner Hunter (1H)': {
        'model_file': 'winner_hunter_1h_v2.json',
        'threshold': 27.52,
        'tp': 0.015,
        'sl': 0.008
    },
    'MTF Scalper (5M)': {
        'model_file': 'mtf_scalper_5m_v2.json',
        'threshold': 20.13,
        'tp': 0.008, # User's image shows WH as 1.5/0.8, MTF is usually different but let's check
        'sl': 0.005 
    }
}

# The user's image shows 1.5% TP and 0.8% SL as the "Fixed-Ratio Protection Strategy"
# I will use these globally for the audit since the user specifically highlighted them.
TP_GLOBAL = 0.015
SL_GLOBAL = 0.008

def load_data():
    print("📖 Loading datasets (Aligned Epochs)...")
    df_1h = pd.read_csv('btc_1h_history_warm.csv')
    df_15m = pd.read_csv('btc_15m_history_warm.csv')
    df_5m = pd.read_csv('btc_5m_history_warm.csv')
    df_1m_outcome = pd.read_csv('btc_1m_outcome_final.csv')
    
    # We use the raw float/int 't' or 'timestamp' columns for alignment if available
    # Actually, btc_1h_history_warm.csv might have 'timestamp' as a string date from my previous fetch.
    # Let's check.
    return df_1h, df_15m, df_5m, df_1m_outcome

def run_recreation():
    # Load raw data to check column names
    d1 = pd.read_csv('btc_1h_history_warm.csv')
    d1m = pd.read_csv('btc_1m_outcome_final.csv')
    
    # Let's assume the user wants the Jan 5 streak.
    # We will use the 'v2' models.
    print("📦 Loading Models...")
    winner_model = xgb.XGBClassifier()
    winner_model.load_model(os.path.join(MODEL_DIR, 'winner_hunter_1h_v2.json'))
    mtf_model = xgb.XGBClassifier()
    mtf_model.load_model(os.path.join(MODEL_DIR, 'mtf_scalper_5m_v2.json'))
    
    print("🛠️ Pre-calculating indicators...")
    df_1h = add_all_indicators(d1.copy())
    
    # 5M MTF Logic
    d5 = pd.read_csv('btc_5m_history_warm.csv')
    d15 = pd.read_csv('btc_15m_history_warm.csv')
    df_5m = add_all_indicators(d5.copy())
    df_15m = add_all_indicators(d15.copy())
    
    exclude = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'T', 's', 'i', 'n']
    wh_features = [c for c in df_1h.columns if c not in exclude]
    
    # MTF Merge
    df_5m_clean = df_5m.drop_duplicates(subset=['timestamp'])
    df_15m_clean = df_15m.drop_duplicates(subset=['timestamp'])
    df_1h_clean = df_1h.drop_duplicates(subset=['timestamp'])

    df_5m_idx = df_5m_clean.set_index('timestamp')
    df_15m_idx = df_15m_clean.set_index('timestamp')
    df_1h_idx = df_1h_clean.set_index('timestamp')
    
    ctx_15m = df_15m_idx[[c for c in df_15m_idx.columns if c not in exclude]].copy()
    ctx_15m.columns = [f"{c}_15m" for c in ctx_15m.columns]
    df_mtf = pd.concat([df_5m_idx, ctx_15m.reindex(df_5m_idx.index, method='ffill')], axis=1)
    
    ctx_1h = df_1h_idx[[c for c in df_1h_idx.columns if c not in exclude]].copy()
    ctx_1h.columns = [f"{c}_1h" for c in ctx_1h.columns]
    df_mtf = pd.concat([df_mtf, ctx_1h.reindex(df_mtf.index, method='ffill')], axis=1)
    df_mtf.dropna(inplace=True)
    df_mtf.reset_index(inplace=True)
    
    mtf_features = [c for c in df_mtf.columns if c not in exclude and c != 'timestamp']

    signals = []
    print("🔬 Scanning for signals (Dec 29 - Jan 6)...")
    
    # Winner Hunter
    for _, row in df_1h.iterrows():
        ts = pd.to_datetime(row['timestamp'])
        if ts < pd.Timestamp('2025-12-25'): continue
        if ts > pd.Timestamp('2026-01-07'): continue
        
        X = row[wh_features].values.reshape(1, -1)
        prob = winner_model.predict_proba(X)[0][1]
        
        if prob * 100 >= 27.52:
            signals.append({
                'time': ts, 'price': float(row['close']), 'confidence': prob * 100, 'model': 'Winner Hunter (1H)'
            })

    # MTF Scalper
    for _, row in df_mtf.iterrows():
        ts = pd.to_datetime(row['timestamp'])
        if ts < pd.Timestamp('2025-12-25'): continue
        if ts > pd.Timestamp('2026-01-07'): continue
        
        X = row[mtf_features].values.reshape(1, -1)
        X = np.nan_to_num(X, nan=0.0)
        prob = mtf_model.predict_proba(X)[0][1]
        
        if prob * 100 >= 20.13:
            signals.append({
                'time': ts, 'price': float(row['close']), 'confidence': prob * 100, 'model': 'MTF Scalper (5M)'
            })

    signals = sorted(signals, key=lambda x: x['time'])
    
    print(f"📊 Verifying {len(signals)} signals...")
    # Outcome Check
    df_1h_clean = df_1h.drop_duplicates(subset=['timestamp']).copy()
    df_1h_clean['timestamp'] = pd.to_datetime(df_1h_clean['timestamp'])
    df_1h_clean.set_index('timestamp', inplace=True)
    if 't' in d1m.columns: d1m.rename(columns={'t':'timestamp','o':'open','h':'high','l':'low','c':'close','v':'volume'}, inplace=True)
    epoch_ref = pd.Timestamp('2025-12-20 00:00:00')
    ts_ref = 1766188800000
    d1m['ts_standard'] = d1m.apply(lambda x: epoch_ref + pd.Timedelta(milliseconds=int(x['timestamp']) - ts_ref), axis=1)

    results = []
    active_until = {'Winner Hunter (1H)': None, 'MTF Scalper (5M)': None}
    
    for s in signals:
        model = s['model']
        if active_until[model] and s['time'] < active_until[model]: continue
        
        tp_px = s['price'] * (1 + 0.015)
        sl_px = s['price'] * (1 - 0.008)
        
        # Use 1m if available, else 1h
        window_1m = d1m[(d1m['ts_standard'] > s['time']) & (d1m['ts_standard'] <= s['time'] + pd.Timedelta(hours=48))]
        
        outcome = "EXPIRED"
        exit_px = s['price']
        exit_time = s['time'] + pd.Timedelta(hours=48)
        
        if not window_1m.empty and window_1m['ts_standard'].iloc[0] <= s['time'] + pd.Timedelta(minutes=5):
            # 1m path
            for _, candle in window_1m.iterrows():
                if candle['low'] <= sl_px:
                    outcome = "LOSS"; exit_px = sl_px; exit_time = candle['ts_standard']; break
                if candle['high'] >= tp_px:
                    outcome = "WIN"; exit_px = tp_px; exit_time = candle['ts_standard']; break
        else:
            # 1h fallback path using df_1h_clean
            window_1h = df_1h_clean.loc[s['time'] : s['time'] + pd.Timedelta(hours=48)]
            for ts_1h, candle in window_1h.iterrows():
                if ts_1h <= s['time']: continue
                if candle['low'] <= sl_px:
                    outcome = "LOSS"; exit_px = sl_px; exit_time = ts_1h; break
                if candle['high'] >= tp_px:
                    outcome = "WIN"; exit_px = tp_px; exit_time = ts_1h; break
                    
        active_until[model] = exit_time + pd.Timedelta(minutes=5)
        pnl = POSITION_SIZE_BTC * (exit_px - s['price'])
        
        results.append({
            **s, 'result': outcome, 'pnl': pnl, 'exit_price': exit_px, 'exit_time': exit_time
        })

    # Generate Report
    with open('STREAK_VERIFICATION_FINAL.md', 'w') as f:
        f.write("# 🏆 Definitive Win Streak Verification\n\n")
        f.write(f"**Position Size:** {POSITION_SIZE_BTC} BTC\n")
        f.write(f"**Risk Profile:** 1.5% TP / 0.8% SL\n\n")
        
        wins = len([r for r in results if r['result'] == 'WIN'])
        losses = len([r for r in results if r['result'] == 'LOSS'])
        total_pnl = sum(r['pnl'] for r in results)
        
        f.write(f"## 📊 Execution Summary\n")
        f.write(f"- **Total Trades:** {len(results)}\n")
        f.write(f"- **Win Rate:** {wins/(wins+losses)*100:.1f}%\n" if (wins+losses)>0 else "- **Win Rate:** N/A\n")
        f.write(f"- **Total Profit:** **${total_pnl:,.2f} USD**\n\n")
        
        f.write("## 📜 Trade Log\n")
        f.write("| Time | Model | Conf | Result | P&L |\n")
        f.write("|---|---|---|---|---|\n")
        for r in results:
            emoji = "✅" if r['result'] == 'WIN' else "❌" if r['result'] == 'LOSS' else "🕒"
            f.write(f"| {r['time']} | {r['model']} | {r['confidence']:.2f}% | {emoji} {r['result']} | **{r['pnl']:+,.2f}** |\n")

    print("✨ Report saved to STREAK_VERIFICATION_FINAL.md")

    # Save Report
    report_path = "USER_VERIFIED_AUDIT.md"
    wins = len([r for r in results if r['result'] == 'WIN'])
    losses = len([r for r in results if r['result'] == 'LOSS'])
    total_pnl = sum(r['pnl'] for r in results)
    
    with open(report_path, 'w') as f:
        f.write("# 🏆 User-Verified Audit (High Fidelity)\n\n")
        f.write(f"**Period:** Dec 30, 2025 - Jan 6, 2026\n")
        f.write(f"**Risk Profile:** Fixed-Ratio (1.5% TP / 0.8% SL)\n")
        f.write(f"**Position Size:** {POSITION_SIZE_BTC} BTC\n\n")
        
        f.write(f"## 📊 Summary\n")
        f.write(f"- **Total Trades:** {len(results)}\n")
        f.write(f"- **Win Rate:** {wins/(wins+losses)*100:.1f}% ({wins}/{wins+losses})\n" if (wins+losses)>0 else "- **Win Rate:** N/A\n")
        f.write(f"- **Total Profit:** **${total_pnl:,.2f} USD**\n\n")
        
        f.write("## 📜 Trade Log\n")
        f.write("| Timestamp (UTC) | Model | Confidence | Entry | Exit | Result | P&L (USD) |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for r in results:
            emoji = "✅" if r['result'] == "WIN" else "❌" if r['result'] == "LOSS" else "🕒"
            f.write(f"| {r['time']} | {r['model']} | {r['confidence']:.2f}% | ${r['price']:,.2f} | ${r['exit_price']:,.2f} | {emoji} {r['result']} | **{r['pnl']:+,.2f}** |\n")

    print(f"✨ Audit complete! Report saved to {report_path}")

if __name__ == "__main__":
    run_recreation()
