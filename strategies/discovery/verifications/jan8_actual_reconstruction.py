#!/usr/bin/env python3
"""
Jan 8, 2026 - ACTUAL Trade Reconstruction
Runs the real ML models on historical Jan 8 data to identify what trades
would have been executed with current thresholds.
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier

# Import feature engineering
from utils.feature_engineer import add_all_indicators

def load_historical_data(interval):
    """Load saved historical data for Jan 8"""
    filename = f'jan8_historical_{interval}.json'
    with open(filename, 'r') as f:
        candles = json.load(f)
    
    # Convert to DataFrame
    df = pd.DataFrame(candles)
    df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
    df['open'] = df['o'].astype(float)
    df['high'] = df['h'].astype(float)
    df['low'] = df['l'].astype(float)
    df['close'] = df['c'].astype(float)
    df['volume'] = df['v'].astype(float)
    
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    return df

def reconstruct_jan8_actual():
    """Run actual ML models on Jan 8 data"""
    
    print("=" * 70)
    print("📅 JAN 8, 2026 - ACTUAL TRADE RECONSTRUCTION")
    print("=" * 70)
    print("Running REAL ML models on historical data")
    print("Current thresholds:")
    print("  Winner Hunter: L:34.12%, S:47.89%")
    print("  MTF Scalper:   L:59.87%, S:68.91%")
    print("=" * 70)
    
    # Load models
    print("\n🤖 Loading ML Models...")
    MODEL_DIR = 'models'
    
    # Winner Hunter (1H)
    wh_xgb = xgb.XGBClassifier()
    wh_xgb.load_model(f'{MODEL_DIR}/winner_hunter_1h_trio_xgb.json')
    wh_lgb = lgb.Booster(model_file=f'{MODEL_DIR}/winner_hunter_1h_trio_lgb.json')
    wh_cat = CatBoostClassifier()
    wh_cat.load_model(f'{MODEL_DIR}/winner_hunter_1h_trio_cat.json')
    
    # MTF Scalper (5M)
    mtf_xgb = xgb.XGBClassifier()
    mtf_xgb.load_model(f'{MODEL_DIR}/mtf_scalper_5m_trio_xgb.json')
    mtf_lgb = lgb.Booster(model_file=f'{MODEL_DIR}/mtf_scalper_5m_trio_lgb.json')
    mtf_cat = CatBoostClassifier()
    mtf_cat.load_model(f'{MODEL_DIR}/mtf_scalper_5m_trio_cat.json')
    
    print("✅ Models loaded")
    
    # Load historical data
    print("\n📊 Loading Jan 8 Historical Data...")
    df_1h = load_historical_data('1h')
    df_5m = load_historical_data('5m')
    df_15m = load_historical_data('15m')
    
    print(f"  1h:  {len(df_1h)} candles")
    print(f"  5m:  {len(df_5m)} candles")
    print(f"  15m: {len(df_15m)} candles")
    
    # Add indicators
    print("\n🔧 Engineering Features...")
    df_1h = add_all_indicators(df_1h)
    df_5m = add_all_indicators(df_5m)
    df_15m = add_all_indicators(df_15m)
    
    # Prepare feature sets
    exclude = ['open', 'high', 'low', 'close', 'volume', 'timestamp']
    
    # Winner Hunter features (1H + 5M + 15M context)
    df_1h_wh = df_1h.set_index('timestamp')
    df_5m_wh = df_5m.set_index('timestamp')
    df_15m_wh = df_15m.set_index('timestamp')
    
    # Add 5M context to 1H
    ctx_cols_5m = [c for c in df_5m_wh.columns if c not in exclude]
    df_5m_ctx = df_5m_wh[ctx_cols_5m].copy()
    df_5m_ctx.columns = [f"{c}_5m" for c in ctx_cols_5m]
    df_5m_resampled = df_5m_ctx.reindex(df_1h_wh.index, method='ffill')
    df_1h_wh = pd.concat([df_1h_wh, df_5m_resampled], axis=1)
    
    # Add 15M context to 1H
    ctx_cols_15m = [c for c in df_15m_wh.columns if c not in exclude]
    df_15m_ctx = df_15m_wh[ctx_cols_15m].copy()
    df_15m_ctx.columns = [f"{c}_15m" for c in ctx_cols_15m]
    df_15m_resampled = df_15m_ctx.reindex(df_1h_wh.index, method='ffill')
    df_1h_wh = pd.concat([df_1h_wh, df_15m_resampled], axis=1)
    df_1h_wh.dropna(inplace=True)
    
    wh_features = [c for c in df_1h_wh.columns if c not in exclude]
    
    # MTF features (5M + 15M + 1H)
    df_5m_indexed = df_5m.set_index('timestamp')
    df_15m_indexed = df_15m.set_index('timestamp')
    df_1h_indexed = df_1h.set_index('timestamp')
    
    # Merge for MTF
    ctx_cols_15m = [c for c in df_15m_indexed.columns if c not in exclude]
    df_15m_renamed = df_15m_indexed[ctx_cols_15m].copy()
    df_15m_renamed.columns = [f"{c}_15m" for c in ctx_cols_15m]
    
    ctx_cols_1h = [c for c in df_1h_indexed.columns if c not in exclude]
    df_1h_renamed = df_1h_indexed[ctx_cols_1h].copy()
    df_1h_renamed.columns = [f"{c}_1h" for c in ctx_cols_1h]
    
    df_mtf = df_5m_indexed.copy()
    df_mtf = pd.concat([df_mtf, df_15m_renamed.reindex(df_mtf.index, method='ffill')], axis=1)
    df_mtf = pd.concat([df_mtf, df_1h_renamed.reindex(df_mtf.index, method='ffill')], axis=1)
    df_mtf.dropna(inplace=True)
    
    mtf_features = [c for c in df_mtf.columns if c not in exclude]
    
    print(f"  Winner Hunter: {len(wh_features)} features")
    print(f"  MTF Scalper:   {len(mtf_features)} features")
    
    # Run predictions
    print("\n" + "=" * 70)
    print("🎯 RUNNING PREDICTIONS")
    print("=" * 70)
    
    signals = []
    
    # Winner Hunter (check every hour)
    print("\n🏆 Winner Hunter (1H) - Checking hours...")
    for i in range(len(df_1h_wh)):
        row = df_1h_wh.iloc[i]
        X = row[wh_features].values.reshape(1, -1)
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        
        # Ensemble prediction
        p1 = wh_xgb.predict_proba(X)
        p2 = wh_lgb.predict(X)
        p3 = wh_cat.predict_proba(X)
        probas = (p1 + p2 + p3) / 3
        
        prob_long = float(probas[0][1])
        prob_short = float(probas[0][2])
        
        # Check thresholds
        if prob_long >= 0.3412:
            signals.append({
                'time': row.name,
                'model': 'Winner Hunter (1H)',
                'direction': 'LONG',
                'confidence': prob_long,
                'price': row['close']
            })
            print(f"  ✅ {row.name} - LONG @ ${row['close']:,.2f} (Conf: {prob_long:.2%})")
        elif prob_short >= 0.4789:
            signals.append({
                'time': row.name,
                'model': 'Winner Hunter (1H)',
                'direction': 'SHORT',
                'confidence': prob_short,
                'price': row['close']
            })
            print(f"  ✅ {row.name} - SHORT @ ${row['close']:,.2f} (Conf: {prob_short:.2%})")
    
    if len([s for s in signals if 'Winner' in s['model']]) == 0:
        print("  ❌ No signals generated")
    
    # MTF Scalper (check every 5 minutes)
    print("\n🎯 MTF Scalper (5M) - Checking 288 intervals...")
    print("  (This may take a minute...)")
    
    # Calculate Hurst for the entire 5M dataset
    try:
        from utils.advanced_features import get_rolling_hurst
        df_mtf['hurst'] = get_rolling_hurst(df_5m.set_index('timestamp'), window=100)
        print("  ✅ Hurst Exponent calculated")
    except Exception as e:
        print(f"  ⚠️  Hurst calculation failed: {e}, defaulting to 0.5")
        df_mtf['hurst'] = 0.5
    
    mtf_count = 0
    blocked_count = 0
    
    for i in range(len(df_mtf)):
        row = df_mtf.iloc[i]
        X = row[mtf_features].values.reshape(1, -1)
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        
        # Ensemble prediction
        p1 = mtf_xgb.predict_proba(X)
        p2 = mtf_lgb.predict(X)
        p3 = mtf_cat.predict_proba(X)
        probas = (p1 + p2 + p3) / 3
        
        prob_long = float(probas[0][1])
        prob_short = float(probas[0][2])
        
        # Check thresholds
        if prob_long >= 0.5987:
            # MANDALORIAN PROTOCOL: Hurst Filter
            rsi = row.get('rsi_14', 50)
            hurst = row.get('hurst', 0.5)
            
            if rsi < 30 and hurst > 0.50:
                blocked_count += 1
                print(f"  🛑 {row.name} - BLOCKED Falling Knife (Hurst={hurst:.3f}, RSI={rsi:.1f})")
            else:
                signals.append({
                    'time': row.name,
                    'model': 'MTF Scalper (5M)',
                    'direction': 'LONG',
                    'confidence': prob_long,
                    'price': row['close']
                })
                mtf_count += 1
                print(f"  ✅ {row.name} - LONG @ ${row['close']:,.2f} (Conf: {prob_long:.2%})")
        elif prob_short >= 0.6891:
            signals.append({
                'time': row.name,
                'model': 'MTF Scalper (5M)',
                'direction': 'SHORT',
                'confidence': prob_short,
                'price': row['close']
            })
            mtf_count += 1
            print(f"  ✅ {row.name} - SHORT @ ${row['close']:,.2f} (Conf: {prob_short:.2%})")
    
    if mtf_count == 0:
        print("  ❌ No signals generated")
    if blocked_count > 0:
        print(f"  🛡️  {blocked_count} signals blocked by Hurst filter")
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 FINAL RESULTS")
    print("=" * 70)
    
    if len(signals) == 0:
        print("\n❌ ZERO TRADES would have been executed on Jan 8")
        print("\nReason:")
        print("  The current thresholds (WH: 34.12%/47.89%, MTF: 59.87%/68.91%)")
        print("  are very conservative and designed for high-confidence setups.")
        print("  Jan 8's market conditions did not meet these criteria.")
    else:
        print(f"\n✅ {len(signals)} TRADE(S) would have been executed:\n")
        for i, sig in enumerate(signals, 1):
            print(f"{i}. {sig['time']} - {sig['model']}")
            print(f"   {sig['direction']} @ ${sig['price']:,.2f}")
            print(f"   Confidence: {sig['confidence']:.2%}")
            print()
    
    print("=" * 70)

if __name__ == '__main__':
    reconstruct_jan8_actual()
