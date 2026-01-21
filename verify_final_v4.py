
import pandas as pd
import numpy as np
import os
import sys

# Add root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.fetch_data import fetch_live_data
from utils.feature_engineer import add_all_indicators
from utils.mtf_feature_engineer import MTFFeatureGenerator
from model_engines.mtf_scalper_v3.logic import MTFScalperV3Logic

def verify_final_v4():
    print("🚀 Verifying FINAL V4 Composite Logic...")
    
    # 1. SETUP
    params = {
        'initial_capital': 10000,
        'position_size': 10000,
        'tp_pct': 0.015,
        'sl_pct': 0.008,
        'fee': 0.0004
    }
    
    start_date = "2026-01-02"
    end_date = "2026-01-14"
    
    # 2. DATA
    print("   📥 Fetching Data...")
    def get_data(tf):
        df = fetch_live_data("BTC", tf, limit=4500)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        s = pd.Timestamp(start_date).tz_localize('UTC')
        e = pd.Timestamp(end_date).tz_localize('UTC') + pd.Timedelta(days=1)
        df = df[(df['timestamp'] >= s) & (df['timestamp'] <= e)]
        df = add_all_indicators(df)
        return df.sort_values('timestamp').reset_index(drop=True)

    df_5m = get_data('5m')
    df_15m = get_data('15m')
    df_30m = get_data('30m')
    
    # 3. PREDICTIONS
    print("   🧠 Generating Predictions...")
    logic = MTFScalperV3Logic()
    gen = MTFFeatureGenerator(df_5m, df_15m, df_30m)
    X_feat, price_df = gen.generate()
    X_feat = X_feat.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    probs = logic.model.predict_proba(X_feat.values)
    
    full_df = df_5m.set_index('timestamp').reindex(price_df.index)
    atr_values = full_df['atr_14'].values
    adx_values = full_df['adx'].values
    
    # 4. SIMULATION
    print("\n⚡ Running Simulation Loop...")
    balance = params['initial_capital']
    trades = []
    position = None 
    
    for i in range(len(price_df)):
        ts = price_df.index[i]
        price = price_df['close'].iloc[i]
        high = price_df['high'].iloc[i]
        low = price_df['low'].iloc[i]
        
        # Check Entry
        if not position:
            p_long = probs[i][1]
            p_short = probs[i][2]
            atr = atr_values[i]
            adx = adx_values[i]
            
            signal = None
            reason = ""
            
            # --- FINAL LOGIC ---
            conf = 0.0
            
            if p_long > p_short:
                conf = p_long
                if conf > 0.80: signal='LONG'; reason='Sniper'
                elif conf > 0.50 and atr < 70: signal='LONG'; reason='Shield'
                elif conf > 0.50 and adx > 50: signal='LONG'; reason='Extreme'
                elif conf > 0.60 and adx > 30: signal='LONG'; reason='Trend'
                
            elif p_short > p_long:
                conf = p_short
                if conf > 0.80: signal='SHORT'; reason='Sniper'
                elif conf > 0.50 and atr < 70: signal='SHORT'; reason='Shield'
                elif conf > 0.50 and adx > 50: signal='SHORT'; reason='Extreme'
                elif conf > 0.60 and adx > 30: signal='SHORT'; reason='Trend'
                
            if signal:
                tp = price * (1 + params['tp_pct']) if signal == 'LONG' else price * (1 - params['tp_pct'])
                sl = price * (1 - params['sl_pct']) if signal == 'LONG' else price * (1 + params['sl_pct'])
                position = {'type': signal, 'entry': price, 'size': params['position_size'], 'tp': tp, 'sl': sl, 'reason': reason}
                
        # Check Exit
        if position:
            p = position
            exit_p = None
            
            if p['type'] == 'LONG':
                if low <= p['sl']: exit_p = p['sl']
                elif high >= p['tp']: exit_p = p['tp']
            elif p['type'] == 'SHORT':
                if high >= p['sl']: exit_p = p['sl']
                elif low <= p['tp']: exit_p = p['tp']
            
            if exit_p:
                raw = (exit_p - p['entry'])/p['entry'] if p['type']=='LONG' else (p['entry'] - exit_p)/p['entry']
                net = raw - (params['fee']*2)
                amt = p['size'] * net
                balance += amt
                trades.append({'net': amt, 'reason': p['reason']})
                position = None
                
    # 5. RESULTS
    print("\n📊 FINAL V4 PERFORMANCE:")
    wins = len([t for t in trades if t['net'] > 0])
    total = len(trades)
    wr = wins/total if total>0 else 0
    pnl = balance - params['initial_capital']
    
    print(f"   Trades: {total} (~{total/12:.1f}/day)")
    print(f"   Win Rate: {wr:.1%} ({wins}/{len(trades)-wins})")
    print(f"   PnL: ${pnl:.2f}")
    
    print("\n🔍 By Strategy:")
    for r in ['Sniper', 'Shield', 'Extreme', 'Trend']:
        sub = [t for t in trades if t['reason'] == r]
        w = len([t for t in sub if t['net']>0])
        print(f"   {r:<10}: {len(sub):>3} trades | {(w/len(sub) if sub else 0):.1%} WR")

if __name__ == "__main__":
    verify_final_v4()
