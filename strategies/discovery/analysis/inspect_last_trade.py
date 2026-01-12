
import sys
import os
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION'))
sys.path.append(os.path.abspath('ADAPTIVE_SHIELD_V1_PRODUCTION/utils'))

from quant_engine import TradingEngine, add_all_indicators

def inspect_trade():
    print("🔍 INSPECTING TRADE: 2026-01-09 13:25:00")
    engine = TradingEngine()
    
    # Fetch Data
    df_raw = engine.fetch_data('5m', 4000)
    df_raw = add_all_indicators(df_raw)
    try:
        from utils.advanced_features import get_rolling_hurst
        df_raw['hurst'] = get_rolling_hurst(df_raw, window=100)
    except:
        df_raw['hurst'] = 0.5 
    df_raw.set_index('timestamp', inplace=True)
    
    # 15m/1h Context
    df_15m = add_all_indicators(engine.fetch_data('15m', 4000))
    df_1h = add_all_indicators(engine.fetch_data('1h', 4000))
    df_15m.set_index('timestamp', inplace=True)
    df_1h.set_index('timestamp', inplace=True)
    
    exclude = ['open', 'high', 'low', 'close', 'volume', 'hurst']
    
    c15 = [c for c in df_15m.columns if c not in exclude]
    df15_r = df_15m[c15].copy()
    df15_r.columns = [f"{c}_15m" for c in c15]
    df_merged = pd.concat([df_raw, df15_r.reindex(df_raw.index, method='ffill')], axis=1)
    
    c1h = [c for c in df_1h.columns if c not in exclude]
    df1h_r = df_1h[c1h].copy()
    df1h_r.columns = [f"{c}_1h" for c in c1h]
    df_merged = pd.concat([df_merged, df1h_r.reindex(df_raw.index, method='ffill')], axis=1)

    # Locate Target Candle
    target_time = pd.Timestamp("2026-01-09 13:25:00")
    
    if target_time in df_merged.index:
        row = df_merged.loc[target_time]
        
        # Calculate Model Prob
        row_vals = row.drop(labels=exclude + ['hurst'], errors='ignore')
        X = row_vals.values.reshape(1, -1)
        X = np.nan_to_num(X, nan=0.0)
        if X.shape[1] > 239: X = X[:, :239]
        
        p1 = engine.mtf_xgb.predict_proba(X)[0]
        p2 = engine.mtf_lgb.predict(X)[0]
        p3 = engine.mtf_cat.predict_proba(X)[0]
        avg = (p1+p2+p3)/3
        
        print("\n📊 ENGINE PARAMETERS")
        print("="*40)
        print(f"⏰ Time:      {target_time}")
        print(f"💰 Price:     ${row['close']:.2f}")
        print(f"📈 ATR (14):  {row.get('atr_14', 0):.2f}")
        print(f"📊 RSI (14):  {row.get('rsi_14', 0):.2f}")
        print(f"📉 MACD Hist: {row.get('macd_hist', 0):.4f}")
        print(f"🌊 Hurst:     {row.get('hurst', 0):.4f}")
        print("-"*40)
        print(f"🤖 Model Confidence:")
        print(f"   LONG:  {avg[1]:.4f} ({(avg[1]*100):.1f}%)")
        print(f"   SHORT: {avg[2]:.4f} ({(avg[2]*100):.1f}%)")
        print("="*40)
        
        # Threshold Logic Re-check
        limit = 0.45
        if row.get('atr_14', 0) > 70:
            limit += (row.get('atr_14', 0) - 70) * 0.002
        print(f"🛡️ Required Threshold: {limit:.4f}")
        if avg[1] >= limit: print(f"✅ LONG Signal Valid")
        else: print(f"❌ LONG Signal Valid (Wait, it traded so it should be valid)")
        
    else:
        print(f"❌ Timestamp {target_time} not found in data!")

if __name__ == "__main__":
    inspect_trade()
