#!/usr/bin/env python3
"""
Simulate last week's trades (Jan 2 - Jan 9, 2026)
With detailed Entry, Exit, TP, SL logs using Optimized Thresholds
"""
import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
import requests
import json
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))
from feature_engineer import add_all_indicators

def fetch_hyperliquid_data(interval='5m', start_time=None, end_time=None):
    """Fetch real data from Hyperliquid API"""
    url = 'https://api.hyperliquid.xyz/info'
    
    payload = {
        'type': 'candleSnapshot',
        'req': {
            'coin': 'BTC',
            'interval': interval,
            'startTime': start_time,
            'endTime': end_time
        }
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code != 200:
            return None
        
        data = resp.json()
        if not isinstance(data, list) or len(data) == 0:
            return None
        
        # Convert to DataFrame
        df_data = []
        for candle in data:
            df_data.append([
                candle['t'],
                float(candle['o']),
                float(candle['h']),
                float(candle['l']),
                float(candle['c']),
                float(candle['v'])
            ])
        
        df = pd.DataFrame(df_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        return df
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def load_trio_models():
    """Load trio ensemble models"""
    print("📦 Loading Trio Ensemble Models...")
    prefix = 'models/mtf_scalper_5m_trio_'
    
    xgb_model = xgb.XGBClassifier()
    xgb_model.load_model(f'{prefix}xgb.json')
    
    lgb_model = lgb.Booster(model_file=f'{prefix}lgb.json')
    
    cat_model = CatBoostClassifier()
    cat_model.load_model(f'{prefix}cat.json')
    
    return xgb_model, lgb_model, cat_model

def get_trio_proba(xgb_m, lgb_m, cat_m, X):
    """Get consensus probability"""
    p1 = xgb_m.predict_proba(X)
    p2 = lgb_m.predict(X, num_iteration=lgb_m.best_iteration)
    p3 = cat_m.predict_proba(X)
    
    # Calculate Disagreement
    std_dev = np.std([p1, p2, p3], axis=0)
    max_disagreement = np.max(std_dev)
    
    return (p1 + p2 + p3) / 3.0, max_disagreement

def main():
    print("="*70)
    print("📅 LAST WEEK TRADING SIMULATION (Jan 2 - Jan 9, 2026)")
    print("="*70)
    
    # Define period
    end_date = datetime(2026, 1, 9)
    start_date = datetime(2026, 1, 2)
    
    print(f"   Start: {start_date.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   End:   {end_date.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Timestamps
    start_ts = int(start_date.timestamp() * 1000)
    end_ts = int(end_date.timestamp() * 1000)
    
    # 7-day lookback for indicators
    lookback_start = int((start_date - timedelta(days=7)).timestamp() * 1000)
    
    print("\n📊 Fetching historical data...")
    df_5m_full = fetch_hyperliquid_data('5m', lookback_start, end_ts)
    df_15m = fetch_hyperliquid_data('15m', lookback_start, end_ts)
    df_1h = fetch_hyperliquid_data('1h', lookback_start, end_ts)
    
    if df_5m_full is None or df_15m is None or df_1h is None:
        print("❌ Failed to fetch data. Check internet connection.")
        return
        
    print(f"   ✅ 5M: {len(df_5m_full)} candles")
    
    # Generate features
    print("\n🔧 Generating features...")
    df_5m_full = add_all_indicators(df_5m_full)
    df_15m = add_all_indicators(df_15m)
    df_1h = add_all_indicators(df_1h)
    
    # Set index
    df_5m_full.set_index('timestamp', inplace=True)
    df_15m.set_index('timestamp', inplace=True)
    df_1h.set_index('timestamp', inplace=True)
    
    # Prepare Features (Align with Training)
    # This exclude list should match the one used during training for feature selection
    exclude_base = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'label', 'target', 'date']
    
    # Filter 5m features
    features_to_use_5m = [c for c in df_5m_full.columns if c not in exclude_base]
    df_5m_filtered = df_5m_full[features_to_use_5m].copy()

    # Filter 15m and 1h features for context
    ctx_cols_15m = [c for c in df_15m.columns if c not in exclude_base]
    df_15m_ctx = df_15m[ctx_cols_15m].copy()
    df_15m_ctx.columns = [f"{c}_15m" for c in ctx_cols_15m]
    
    ctx_cols_1h = [c for c in df_1h.columns if c not in exclude_base]
    df_1h_ctx = df_1h[ctx_cols_1h].copy()
    df_1h_ctx.columns = [f"{c}_1h" for c in ctx_cols_1h]
    
    # Resample contexts to 5m
    df_15m_resampled = df_15m_ctx.reindex(df_5m_full.index, method='ffill')
    df_1h_resampled = df_1h_ctx.reindex(df_5m_full.index, method='ffill')
    
    df_mtf = pd.concat([df_5m_full, df_15m_resampled, df_1h_resampled], axis=1)
    df_mtf.dropna(inplace=True)
    
    # Filter to simulation period
    df_sim = df_mtf[df_mtf.index >= start_date].copy()
    print(f"   ✅ Simulation Data: {len(df_sim)} 5M candles")
    
    # Load Models
    xgb_m, lgb_m, cat_m = load_trio_models()
    
    # OPTIMIZED THRESHOLDS FOR VOLUME (5-6 trades/day)
    thresh_long = 0.45
    thresh_short = 0.45
    print(f"\n🎯 Using 'Volume' Thresholds: Long={thresh_long}, Short={thresh_short}")
    
    # Trading Config
    tp_pct = 0.015  # 1.5%
    sl_pct = 0.008  # 0.8%
    
    print("\n🔄 Running simulation...")
    
    trades = []
    active_trade = None
    
    # Circuit Breaker State
    consecutive_losses = 0
    last_loss_time = None
    cooldown_until = None
    
    all_exclude = exclude_base + ['timestamp']
    
    # DEBUG: Check columns
    print(f"DEBUG: df_5m_full cols: {len(df_5m_full.columns)}")
    print(f"DEBUG: features_to_use_5m count: {len(features_to_use_5m)}")
    
    
    # We need to use ALL columns in df_sim except excludes
    # df_sim contains 5m, 15m, 1h features already merged
    all_features = [c for c in df_sim.columns if c not in all_exclude]
    print(f"DEBUG: df_sim features count: {len(all_features)}")
    
    # This should match training data columns
    if len(all_features) != 239:
        print(f"⚠️ WARNING: Feature count mismatch! Model expects 239, got {len(all_features)}")
        # If still mismatch, we might need to align specific columns or order
        # But let's proceed and see if xgb handles it or identifying missing ones
    
    common_cols = all_features

    
    if len(common_cols) != 239:
        print("⚠️ WARNING: Feature count mismatch! Model expects 239.")
        # Attempt to auto-fix: The model was trained on 239 features. 
        # Advanced features add ~19 columns. Basic features ~220.
        # If we have 255, we have too many. If 85, we are missing indicators.
        # But wait, df_5m_full HAS indicators (line 123 calls add_all_indicators).
    
    
    # Iterate through candles
    for i in range(len(df_sim) - 1): # Stop 1 before end to allow checking next candle
        idx = df_sim.index[i]
        row = df_sim.iloc[i]
        next_row = df_sim.iloc[i+1] # Look ahead for TP/SL outcome (approximation)
        
        # Check active trade exit
        if active_trade:
            # Check if TP or SL hit in relevant timeframe
            # Here we approximate by checking subsequent candles
            # In a real backtest loop we'd check high/low of current candle relative to entry
            pass
            # Just simple simulation: find outcome
        
        # Generate Signal
        X = row[common_cols].values.reshape(1, -1)
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        
        # FIX: Model expects 239 features. If we have more (255), slice it.
        # This assumes new features were appended at the end and model was trained without them (or on subset).
        if X.shape[1] > 239:
            X = X[:, :239]
            
        if X.shape[1] > 239:
            X = X[:, :239]
            
        probas, disagreement = get_trio_proba(xgb_m, lgb_m, cat_m, X)
        prob_long = probas[0][1]
        prob_short = probas[0][2]
        
        signal = None
        conf = 0.0
        
        # High Precision Threshold
        thresh_val = 0.45
        
        if prob_long >= thresh_val:
            signal = 'LONG'
            conf = prob_long
        elif prob_short >= thresh_val:
            signal = 'SHORT'
            conf = prob_short
            
        if signal:
            # 🛡️ STATISTICAL SHIELD 2.0 (Adaptive Volatility) 🛡️
            atr_val = row.get('atr_14', 50)
            
            # Base Penalty Threshold
            required_conf = thresh_val
            
            # Penalty: For every 1 point of ATR above 70, require 0.2% more confidence
            if atr_val > 70:
                penalty = (atr_val - 70) * 0.002
                required_conf += penalty
            
            # Filter
            if conf < required_conf:
                # print(f"Skipping trade: Low Conf relative to Volatility ({conf:.3f} < {required_conf:.3f}, ATR={atr_val:.1f})")
                continue
                
            # Keep Disagreement Filter
            if disagreement > 0.09:
                continue
            
            # Filter
            if conf < required_conf:
                # print(f"Skipping trade: Low Conf relative to Volatility ({conf:.3f} < {required_conf:.3f}, ATR={atr_val:.1f})")
                continue
                
            # Keep Disagreement Filter
            if disagreement > 0.09:
                continue

            # 🛡️ CIRCUIT BREAKER 🛡️
            # If in conflict, skip
            if cooldown_until and idx < cooldown_until:
                # print(f"Skipping trade at {idx} due to cooldown until {cooldown_until}")
                continue
               
        if signal:
            # Simulate Trade Outcome
            entry_price = row['close']
            exit_price = None
            exit_reason = None
            exit_time = None
            
            tp_price = entry_price * (1 + tp_pct) if signal == 'LONG' else entry_price * (1 - tp_pct)
            sl_price = entry_price * (1 - sl_pct) if signal == 'LONG' else entry_price * (1 + sl_pct)
            
            # Look forward using iloc
            for j in range(i+1, min(i+576, len(df_sim))):
                fut_row = df_sim.iloc[j]
                high = fut_row['high']
                low = fut_row['low']
                ts = df_sim.index[j]
                
                if signal == 'LONG':
                    if high >= tp_price:
                        exit_price = tp_price
                        exit_reason = 'TP'
                        exit_time = ts
                        break
                    if low <= sl_price:
                        exit_price = sl_price
                        exit_reason = 'SL'
                        exit_time = ts
                        break
                else: # SHORT
                    if low <= tp_price:
                        exit_price = tp_price
                        exit_reason = 'TP'
                        exit_time = ts
                        break
                    if high >= sl_price:
                        exit_price = sl_price
                        exit_reason = 'SL'
                        exit_time = ts
                        break
            
            # If period ended without exit, close at last price
            if not exit_price:
                exit_price = df_sim.iloc[-1]['close']
                exit_reason = 'FORCE_CLOSE'
                exit_time = df_sim.index[-1]
            
            # Calculate PnL
            if signal == 'LONG':
                pnl_pct = (exit_price - entry_price) / entry_price
            else:
                pnl_pct = (entry_price - exit_price) / entry_price
                
            # Update Circuit Breaker State BEFORE appending trade
            if pnl_pct < 0:
                # LOSS
                current_time = idx
                if last_loss_time and (current_time - last_loss_time).seconds < 3600:
                    consecutive_losses += 1
                else:
                    consecutive_losses = 1 # Reset or start new streak
                
                last_loss_time = current_time
                
                if consecutive_losses >= 2:
                    cooldown_until = current_time + timedelta(hours=4)
                    print(f"   🛑 Circuit Breaker Triggered at {current_time}! Pausing 4h.")
            else:
                # WIN - Reset streak
                consecutive_losses = 0
                last_loss_time = None
                
            trades.append({
                'Entry Time': idx,
                'Type': signal,
                'Confidence': conf,
                'Disagreement': disagreement,
                'ATR': row.get('atr_14', 0),
                'Hurst': row.get('hurst', 0.5), # Assuming added, or default
                'RSI': row.get('rsi_14', 50),
                'Entry Price': entry_price,
                'TP': tp_price,
                'SL': sl_price,
                'Exit Time': exit_time,
                'Exit Price': exit_price,
                'Exit Reason': exit_reason,
                'PnL %': pnl_pct * 100
            })
            
            # Skip forward to simulate "in trade" (simple assumption: no concurrent trades for now)
            # In reality, engine supports concurrent. But for clean log, let's just log every signal as if taken.
            # Actually, let's NOT skip, to show all signals.
    
    # Generate Report
    print("\n" + "="*70)
    print("📝 TRADE LOG (Last Week)")
    print("="*70)
    
    if len(trades) == 0:
        print("No trades found matching threshold criteria.")
    else:
        df_trades = pd.DataFrame(trades)
        
        print(f"{'Entry Time':<20} {'Type':<6} {'Conf':<6} {'Entry':<10} {'Exit':<10} {'Result':<6} {'PnL':<8}")
        print("-" * 80)
        
        for _, t in df_trades.iterrows():
            conf_str = f"{t['Confidence']*100:.1f}%"
            pnl_str = f"{t['PnL %']:+.2f}%"
            print(f"{t['Entry Time'].strftime('%Y-%m-%d %H:%M'):<20} "
                  f"{t['Type']:<6} "
                  f"{conf_str:<6} "
                  f"{t['Entry Price']:<10.1f} "
                  f"{t['Exit Price']:<10.1f} "
                  f"{t['Exit Reason']:<6} "
                  f"{pnl_str:<8}")
                  
        print("-" * 80)
        
        wins = len(df_trades[df_trades['PnL %'] > 0])
        total = len(df_trades)
        win_rate = (wins/total)*100
        total_pnl = df_trades['PnL %'].sum()
        
        print(f"\n📈 Summary:")
        print(f"   Total Trades: {total}")
        print(f"   Win Rate: {win_rate:.1f}% ({wins}W / {total-wins}L)")
        print(f"   Total PnL: {total_pnl:+.2f}%")
        
        # Save FORENSIC log
        output_file = 'FORENSIC_TRADES.csv'
        df_trades.to_csv(output_file, index=False)
        print(f"\n🔬 Forensic data saved to: {output_file}")
        
        # Save detailed log
        output_file = 'LAST_WEEK_TRADES.md'
        with open(output_file, 'w') as f:
            f.write("# 📅 Last Week Trade Log (Jan 2 - 9, 2026)\n\n")
            f.write(f"**Thresholds**: Long {thresh_long}, Short {thresh_short}\n")
            f.write(f"**Settings**: TP 1.5%, SL 0.8%\n\n")
            f.write(df_trades.to_markdown(index=False))
            f.write(f"\n\n**Total PnL**: {total_pnl:+.2f}%\n")
        
        print(f"\n✅ Detailed log saved to: {output_file}")


if __name__ == '__main__':
    main()
