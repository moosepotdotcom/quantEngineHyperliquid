import pandas as pd
import numpy as np
import xgboost as xgb
import os
import sys
from datetime import datetime
import time

# Insert utils into path for feature_engineer
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "utils"))
from feature_engineer import add_all_indicators

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')
POSITION_SIZE_BTC = 1.27

# Model Settings
SETTINGS = {
    'Winner Hunter (1H)': {
        'model_file': 'winner_hunter_1h_v2.json',
        'threshold': 0.2752,
        'tp': 0.015,
        'sl': 0.008
    },
    'MTF Scalper (5M)': {
        'model_file': 'mtf_scalper_5m_v2.json',
        'threshold': 0.2013,
        'tp': 0.008,
        'sl': 0.005
    }
}

def load_data():
    print("📖 Loading warmed historical data...")
    df_1h = pd.read_csv('btc_1h_history_warm.csv')
    df_15m = pd.read_csv('btc_15m_history_warm.csv')
    df_5m = pd.read_csv('btc_5m_history_warm.csv')
    
    # Convert timestamp to datetime and drop duplicates
    for df_name, df in [('1h', df_1h), ('15m', df_15m), ('5m', df_5m)]:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        # Store initial count
        before = len(df)
        df.drop_duplicates(subset=['timestamp'], inplace=True)
        after = len(df)
        if before > after:
            print(f"   ⚠️ Dropped {before - after} duplicate rows from {df_name}")
        
    return df_1h, df_15m, df_5m

def run_reconstruction():
    df_1h_raw, df_15m_raw, df_5m_raw = load_data()
    
    # Define Jan 1st Start
    jan_start = pd.Timestamp('2026-01-01 00:00:00')
    
    # Load Models
    print("📦 Loading Models...")
    winner_model = xgb.XGBClassifier()
    winner_model.load_model(os.path.join(MODEL_DIR, SETTINGS['Winner Hunter (1H)']['model_file']))
    mtf_model = xgb.XGBClassifier()
    mtf_model.load_model(os.path.join(MODEL_DIR, SETTINGS['MTF Scalper (5M)']['model_file']))
    
    # 1. Pre-calculate indicators for all timeframes (Full history for warm-up)
    print("🛠️ Pre-calculating indicators (Warmed)...")
    df_1h = add_all_indicators(df_1h_raw.copy())
    df_15m = add_all_indicators(df_15m_raw.copy())
    df_5m = add_all_indicators(df_5m_raw.copy())
    
    # Prepare MTF context merge
    exclude = ['open', 'high', 'low', 'close', 'volume']
    
    print("🔀 Merging timeframes for MTF Scalper...")
    df_5m_mtf = df_5m.copy().set_index('timestamp')
    df_15m_idx = df_15m.set_index('timestamp')
    df_1h_idx = df_1h.set_index('timestamp')
    
    ctx_cols_15m = [c for c in df_15m_idx.columns if c not in exclude]
    df_15m_renamed = df_15m_idx[ctx_cols_15m].copy()
    df_15m_renamed.columns = [f"{c}_15m" for c in ctx_cols_15m]
    df_5m_mtf = pd.concat([df_5m_mtf, df_15m_renamed.reindex(df_5m_mtf.index, method='ffill')], axis=1)
    
    ctx_cols_1h = [c for c in df_1h_idx.columns if c not in exclude]
    df_1h_renamed = df_1h_idx[ctx_cols_1h].copy()
    df_1h_renamed.columns = [f"{c}_1h" for c in ctx_cols_1h]
    df_5m_mtf = pd.concat([df_5m_mtf, df_1h_renamed.reindex(df_5m_mtf.index, method='ffill')], axis=1)
    
    df_5m_mtf.dropna(inplace=True)
    df_5m_mtf.reset_index(inplace=True)

    signals = []

    # 2. Scanning Jan 1st onwards
    print("🔬 Scanning Winner Hunter (1H) from Jan 1st...")
    wh_features = [c for c in df_1h.columns if c not in exclude and c != 'timestamp']
    for i in range(len(df_1h)):
        row = df_1h.iloc[i]
        if row['timestamp'] < jan_start: continue
        
        X = row[wh_features].values.reshape(1, -1)
        prob = winner_model.predict_proba(X)[0][1]
        
        if prob >= SETTINGS['Winner Hunter (1H)']['threshold']:
            signals.append({
                'model': 'Winner Hunter (1H)',
                'time': row['timestamp'],
                'price': float(row['close']),
                'confidence': prob
            })

    print("🔬 Scanning MTF Scalper (5M) from Jan 1st...")
    mtf_features = [c for c in df_5m_mtf.columns if c not in exclude and c != 'timestamp']
    for i in range(len(df_5m_mtf)):
        row = df_5m_mtf.iloc[i]
        if row['timestamp'] < jan_start: continue
        
        X = row[mtf_features].values.reshape(1, -1)
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        prob = mtf_model.predict_proba(X)[0][1]
        
        if prob >= SETTINGS['MTF Scalper (5M)']['threshold']:
            signals.append({
                'model': 'MTF Scalper (5M)',
                'time': row['timestamp'],
                'price': float(row['close']),
                'confidence': prob
            })

    signals = sorted(signals, key=lambda x: x['time'])
    print(f"✅ Generated {len(signals)} initial signals.")
    
    # Simulate Outcomes (Realistic: Only one trade at a time per model)
    results = []
    active_trades = {'Winner Hunter (1H)': None, 'MTF Scalper (5M)': None}
    
    print("\n📊 Simulating Outcomes (Realistic Logic)...")
    
    for s in signals:
        model = s['model']
        if active_trades[model] and s['time'] < active_trades[model]:
            continue
            
        rules = SETTINGS[model]
        tp_px = s['price'] * (1 + rules['tp'])
        sl_px = s['price'] * (1 - rules['sl'])
        
        start_time = s['time']
        end_time = start_time + pd.Timedelta(hours=24)
        # Use fresh 5m history for outcomes
        window = df_5m_raw[(df_5m_raw['timestamp'] > start_time) & (df_5m_raw['timestamp'] <= end_time)]
        
        outcome = "EXPIRED"
        exit_px = s['price']
        exit_time = end_time
        
        if not window.empty:
            for _, candle in window.iterrows():
                if candle['low'] <= sl_px:
                    outcome = "LOSS"
                    exit_px = sl_px
                    exit_time = candle['timestamp']
                    break
                if candle['high'] >= tp_px:
                    outcome = "WIN"
                    exit_px = tp_px
                    exit_time = candle['timestamp']
                    break
        
        cooldown = pd.Timedelta(hours=1) if 'Winner' in model else pd.Timedelta(minutes=15)
        active_trades[model] = exit_time + cooldown
        
        pnl = POSITION_SIZE_BTC * (exit_px - s['price'])
        results.append({
            **s,
            'result': outcome,
            'exit_price': exit_px,
            'exit_time': exit_time,
            'pnl': pnl
        })
    
    # FINAL REPORT GENERATION
    report_path = "DEFINITIVE_JAN_AUDIT_REPORT.md"
    wins = len([r for r in results if r['result'] == 'WIN'])
    losses = len([r for r in results if r['result'] == 'LOSS'])
    total_pnl = sum(r['pnl'] for r in results)
    
    with open(report_path, 'w') as f:
        f.write("# 🏆 Definitive Performance Audit: Jan 1st - Jan 6th\n\n")
        f.write(f"**Reconstruction Logic:** One trade per model max, 500-bar indicator warm-up, local BTC 5m data.\n\n")
        f.write(f"**Position Size:** {POSITION_SIZE_BTC} BTC\n")
        f.write(f"**Win Rate (Completed):** {wins/(wins+losses)*100:.1f}% ({wins}/{wins+losses})\n" if (wins+losses) > 0 else "N/A\n")
        f.write(f"**Total USD Profit/Loss:** **${total_pnl:,.2f} USD**\n\n")
        
        f.write("## 📜 Detailed Trade Log\n")
        f.write("| Time (UTC) | Model | Conf | Entry | Exit | Result | P&L (USD) |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for r in results:
            emoji = "✅" if r['result'] == "WIN" else "❌" if r['result'] == "LOSS" else "🕒"
            f.write(f"| {r['time']} | {r['model']} | {r['confidence']:.2%} | ${r['price']:,.2f} | ${r['exit_price']:,.2f} | {emoji} {r['result']} | **{r['pnl']:+,.2f}** |\n")

    print(f"✨ Definitive reconstruction complete! Report saved to {report_path}")

    print(f"✨ Reconstruction complete! Report saved to {report_path}")

if __name__ == "__main__":
    run_reconstruction()
