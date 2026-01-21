
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import joblib
import os
import sys

# Add root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model_engines.mtf_scalper_v3.logic import MTFScalperV3Logic

def simulate_scenario():
    print("🚀 Starting User Scenario Simulation...")
    print("   💰 Capital: $53")
    print("   💪 Leverage: 27x")
    print("   📦 Lot Size: 0.02 BTC")
    
    # PARAMETERS
    INITIAL_CAPITAL = 100.0
    LEVERAGE = 27.0
    LOT_SIZE = 0.02
    TP_PCT = 0.015
    SL_PCT = 0.008
    FEE_RATE = 0.00035 # Taker fee approx
    
    # 1. LOAD DATA (Re-using cached if possible to save time)
    # We need 5m, 15m, 30m data for Jan 2026.
    # Assuming standard path or fetching. 
    # For speed, I'll rely on the logic in specific files or just load the big csv and slice?
    # Actually, let's use the fetcher from backtest_suite logic or similar.
    
    # 1. LOAD DATA 
    from utils.fetch_data import fetch_live_data
    from utils.feature_engineer import add_all_indicators
    
    start_date = "2026-01-02"
    end_date = "2026-01-14"
    
    print("   📥 Fetching Data...")
    
    # helper to fetch and prep
    def get_tf_data(tf):
        # approx limit for 12 days
        limit = 4000 if tf == '5m' else 2000
        df = fetch_live_data("BTC", tf, limit=limit)
        if df is not None:
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            # Filter
            start_dt = pd.Timestamp(start_date).tz_localize('UTC')
            end_dt = pd.Timestamp(end_date).tz_localize('UTC') + pd.Timedelta(days=1)
            df = df[(df['timestamp'] >= start_dt) & (df['timestamp'] <= end_dt)]
            # Indicators
            df = add_all_indicators(df)
            return df.sort_values('timestamp').reset_index(drop=True)
        return None

    df_5m = get_tf_data('5m')
    df_15m = get_tf_data('15m')
    df_30m = get_tf_data('30m')
    
    if df_5m is None or df_15m is None or df_30m is None:
        print("❌ Data fetch failed")
        return
    
    # 2. INIT ENGINE
    logic = MTFScalperV3Logic()
    logic.threshold = 0.80 # Using the optimized V4 threshold
    
    # 3. RUN LOOP
    balance = INITIAL_CAPITAL
    equity = INITIAL_CAPITAL
    trades = []
    
    # Simulation State
    position = None # {type: 'LONG'/'SHORT', entry: price, size: 0.02}
    
    print(f"   🏃 Running simulation on {len(df_5m)} candles...")
    
    # Align Dataframes (Simplification: assuming mostly aligned index)
    # We iterate through 5m candles
    
    for i in range(50, len(df_5m)):
        # Simulate realtime feed roughly
        # We need to slice data up to 'i' for the logic to see "past" only
        # Optimization: Logic.analyze expects full DFs but *internally* we might need to be careful?
        # Actually logic.analyze takes whole DF? logic.py: "current_price = price_df['close'].iloc[-1]"
        # So we must Pass SLICED dataframes to simulate correctly. 
        # This is SLOW if we do it for every candle.
        # Faster approach: Generate ALL signals first, then iterate for PnL.
        
        # ACTUALLY: logic.py does feature engineering on the whole DF. 
        # So we can generate signals on the WHOLE DF, then iterate signals to apply constraints.
        pass

    # OPTIMIZED APPROACH:
    # 1. Generate Signal Series
    print("   ⚡ Generating Signals (Batch)...")
    signals = []
    
    # We can rely on logic.analyze? No, logic.analyze does feature gen taking full DF.
    # Let's perform Feature Gen ONCE.
    from utils.mtf_feature_engineer import MTFFeatureGenerator
    gen = MTFFeatureGenerator(df_5m, df_15m, df_30m)
    X_feat, price_df = gen.generate()
    X_feat = X_feat.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    # Predict
    probs = logic.model.predict_proba(X_feat.values) # [[n, l, s], ...]
    
    # Iterate through Time
    for idx in range(len(price_df)):
        ts = price_df.index[idx]
        current_price = price_df['close'].iloc[idx]
        
        # Check Exit first
        if position:
            entry_price = position['entry']
            pnl_pct = 0
            
            if position['type'] == 'LONG':
                pnl_pct = (current_price - entry_price) / entry_price
            else:
                pnl_pct = (entry_price - current_price) / entry_price
                
            # TP/SL Report
            if pnl_pct >= TP_PCT:
                # WIN
                raw_pnl = (position['size'] * entry_price) * pnl_pct
                # Fee
                fee = (position['size'] * current_price) * FEE_RATE
                
                net_pnl = raw_pnl - fee
                balance += net_pnl
                trades.append({'time': ts, 'type': 'WIN', 'pnl': net_pnl, 'bal': balance})
                position = None
                
            elif pnl_pct <= -SL_PCT:
                # LOSS
                raw_pnl = (position['size'] * entry_price) * pnl_pct # negative
                fee = (position['size'] * current_price) * FEE_RATE
                
                net_pnl = raw_pnl - fee
                balance += net_pnl
                trades.append({'time': ts, 'type': 'LOSS', 'pnl': net_pnl, 'bal': balance})
                position = None
                
            # Check Liquidation (Simple approximation)
            # Maintenance Margin failure?
            # Max loss = Balance?
            if balance <= 0:
                print(f"   💀 LIQUIDATED at {ts} price {current_price}")
                break
                
        # Check Entry
        if not position:
            p_long = probs[idx][1]
            p_short = probs[idx][2]
            
            signal_type = None
            if p_long > logic.threshold: signal_type = 'LONG'
            elif p_short > logic.threshold: signal_type = 'SHORT'
            
            if signal_type:
                # Check Buying Power
                notional = LOT_SIZE * current_price
                margin_required = notional / LEVERAGE
                
                if balance >= margin_required:
                    # Fee on entry
                    fee = notional * FEE_RATE
                    balance -= fee
                    
                    position = {
                        'type': signal_type,
                        'entry': current_price,
                        'size': LOT_SIZE
                    }
                    # trades.append({'time': ts, 'type': 'OPEN', 'pnl': -fee, 'bal': balance})
                else:
                    # print(f"   ⚠️ nsufficient Funds for {signal_type} at {ts}. Req: ${margin_required:.2f}, Bal: ${balance:.2f}")
                    pass

    print("\n📊 User Simulation Results 📊")
    print(f"   Initial Balance: ${INITIAL_CAPITAL}")
    print(f"   Final Balance:   ${balance:.2f}")
    if balance <= 0:
        print("   Outcome: REKT (Liquidated)")
    else:
        pnl = balance - INITIAL_CAPITAL
        roi = (pnl / INITIAL_CAPITAL) * 100
        print(f"   PnL: ${pnl:.2f} ({roi:.2f}%)")
        print(f"   Trades: {len(trades)}")
        wins = len([t for t in trades if t['type'] == 'WIN'])
        losses = len([t for t in trades if t['type'] == 'LOSS'])
        print(f"   W/L: {wins}/{losses}")

if __name__ == "__main__":
    simulate_scenario()
