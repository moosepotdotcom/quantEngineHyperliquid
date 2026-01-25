import pandas as pd
import numpy as np
import joblib
import os
import sys

class RenaissanceSingleSlotSimulator:
    def __init__(self):
        # Load Renaissance Neural Core (Relative to deployment folder)
        base_dir = os.path.join(os.path.dirname(__file__), 'models')
        self.meta_classifier = joblib.load(f'{base_dir}/renaissance_meta_classifier.pkl')
        self.specialists = {
            0: joblib.load(f'{base_dir}/renaissance_super_bull_ensemble.pkl'),
            1: joblib.load(f'{base_dir}/renaissance_orderly_bear_ensemble.pkl'),
            2: joblib.load(f'{base_dir}/renaissance_sideways_decay_ensemble.pkl'),
            3: joblib.load(f'{base_dir}/renaissance_volatile_crush_ensemble.pkl')
        }
        
    def run_single_slot_test(self, data_path, balance=1000.0, leverage=3.0, lot_size=0.02, tp_pct=0.005, sl_pct=0.004):
        print(f"🕵️‍♂️ Renaissance SINGLE-SLOT Engine Execution: {data_path}")
        print(f"   Settings: ${balance} Start | {tp_pct*100}% TP | {sl_pct*100}% SL | {lot_size} BTC")
        df = pd.read_csv(data_path)
        
        exclude = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'label', 'regime_label']
        features = [c for c in df.columns if c not in exclude]
        X = df[features].replace([np.inf, -np.inf], np.nan).fillna(0)
        
        # 1. Batch Prediction
        model_features = self.specialists[0].get_booster().feature_names
        X_filtered = X.reindex(columns=model_features, fill_value=0)
        regime_indices = self.meta_classifier.predict(X_filtered)
        
        all_conf_long = np.zeros(len(df))
        all_conf_short = np.zeros(len(df))
        for r_id, model in self.specialists.items():
            mask = (regime_indices == r_id)
            if mask.any():
                probs = model.predict_proba(X_filtered[mask])
                all_conf_long[mask] = probs[:, 1]
                all_conf_short[mask] = probs[:, 2]

        # 2. Simulation (SINGLE SLOT: One Trade at a Time)
        trades = []
        equity = balance
        i = 100
        
        while i < len(df):
            conf_long = all_conf_long[i]
            conf_short = all_conf_short[i]
            
            signal = 0 
            if conf_long > 0.65: signal = 1
            elif conf_short > 0.65: signal = 2
            
            if signal > 0:
                entry_price = df.iloc[i]['close']
                tp_price = entry_price * (1 + tp_pct) if signal == 1 else entry_price * (1 - tp_pct)
                sl_price = entry_price * (1 - sl_pct) if signal == 1 else entry_price * (1 + sl_pct)
                
                # Check future window
                future = df.iloc[i+1:i+288] # 24h max hold
                if future.empty: 
                    i += 1
                    continue
                
                exit_price = 0
                outcome = "NONE"
                duration = 0
                
                # Trailing TP State
                trailing_active = False
                peak_price = 0
                callback_pct = 0.002 # 0.2% Trailing Offset
                
                for idx_offset, row in enumerate(future.values):
                    duration += 1
                    low_val = row[3]
                    high_val = row[2]
                    curr_close = row[4]
                    
                    if signal == 1: # LONG
                        if not trailing_active:
                            if low_val <= sl_price:
                                exit_price = sl_price; outcome = "SL"; break
                            if high_val >= tp_price:
                                trailing_active = True
                                peak_price = high_val
                        
                        if trailing_active:
                            # Update peak
                            if high_val > peak_price: peak_price = high_val
                            # Check trailing exit (Must be at or above original TP)
                            trail_stop = peak_price * (1 - callback_pct)
                            if low_val <= trail_stop and trail_stop >= tp_price:
                                exit_price = trail_stop
                                outcome = "TP_TRAIL"
                                break
                    else: # SHORT
                        if not trailing_active:
                            if high_val >= sl_price:
                                exit_price = sl_price; outcome = "SL"; break
                            if low_val <= tp_price:
                                trailing_active = True
                                peak_price = low_val
                        
                        if trailing_active:
                            # Update peak
                            if low_val < peak_price: peak_price = low_val
                            # Check trailing exit (Must be at or below original TP)
                            trail_stop = peak_price * (1 + callback_pct)
                            if high_val >= trail_stop and trail_stop <= tp_price:
                                exit_price = trail_stop
                                outcome = "TP_TRAIL"
                                break
                
                if outcome != "NONE":
                    pnl = (exit_price - entry_price) * lot_size if signal == 1 else (entry_price - exit_price) * lot_size
                    points = abs(exit_price - entry_price)
                    equity += pnl
                    trades.append({
                        'timestamp': df.iloc[i]['timestamp'],
                        'side': 'LONG' if signal == 1 else 'SHORT',
                        'entry': entry_price,
                        'exit': exit_price,
                        'tp': tp_price,
                        'sl': sl_price,
                        'outcome': outcome,
                        'points': points,
                        'pnl': pnl,
                        'balance': equity
                    })
                    i += duration # POSITION LOCK
                else:
                    i += 1
            else:
                i += 1
        
        res_df = pd.DataFrame(trades)
        if res_df.empty:
            print("❌ No trades executed.")
            return res_df
            
        print(f"\n✅ SINGLE-SLOT Execution Complete. Average Points: {res_df['points'].mean():.2f}")
        return res_df

if __name__ == "__main__":
    sim = RenaissanceSingleSlotSimulator()
    
    data_path = sys.argv[1] if len(sys.argv) > 1 else '../training/data/BTC_5m_aug2025_blind.csv'
    tp = float(sys.argv[2]) if len(sys.argv) > 2 else 0.005
    sl = float(sys.argv[3]) if len(sys.argv) > 3 else 0.015
    lot_size = float(sys.argv[4]) if len(sys.argv) > 4 else 0.02
    
    initial_balance = 1000.0
    report = sim.run_single_slot_test(data_path, balance=initial_balance, tp_pct=tp, sl_pct=sl, lot_size=lot_size)
    
    if not report.empty:
        # Resolve results directory relative to this script
        results_dir = os.path.join(os.path.dirname(__file__), 'results')
        os.makedirs(results_dir, exist_ok=True)
        
        basename = os.path.basename(data_path).replace('.csv', '_single_slot.csv')
        out_path = os.path.join(results_dir, basename)
        report.to_csv(out_path, index=False)
        print(f"📊 Saved Single-Slot Report: {out_path}")
        
        final_bal = report['balance'].iloc[-1]
        wr = (report['outcome'].str.contains('TP')).mean() * 100
        roi = ((final_bal - initial_balance) / initial_balance) * 100
        print(f"\n📈 SINGLE-SLOT Performance")
        print(f"   Final Balance: ${final_bal:,.2f}")
        print(f"   Total ROI: {roi:.2f}%")
        print(f"   Total Trades: {len(report)}")
        print(f"   Win Rate: {wr:.2f}%")
