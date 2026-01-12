
"""
Extended Live Market Analysis
Monitors probability distribution over time and compares feature distributions.
"""
import os
import sys
import pandas as pd
import numpy as np
import joblib
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from research.mtf_feature_engineer import MTFFeatureGenerator
from data.loader import DataLoader

def analyze_market():
    print("=" * 60)
    print("EXTENDED LIVE MARKET ANALYSIS")
    print("=" * 60)
    
    # Load model
    model_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'scalp_mtf_xgb.pkl')
    model = joblib.load(model_path)
    
    # Get feature importances
    print("\n📊 TOP 10 FEATURE IMPORTANCES:")
    importances = model.get_booster().get_score(importance_type='weight')
    sorted_imp = sorted(importances.items(), key=lambda x: x[1], reverse=True)[:10]
    for feat, score in sorted_imp:
        print(f"   {feat}: {score}")
    
    # Fetch live data
    print("\n📥 Fetching live data...")
    df_5m = DataLoader.fetch_yfinance("BTC-USD", period="5d", interval="5m", quiet=True)
    df_15m = DataLoader.fetch_yfinance("BTC-USD", period="1mo", interval="15m", quiet=True)
    df_30m = DataLoader.fetch_yfinance("BTC-USD", period="1mo", interval="30m", quiet=True)
    
    gen = MTFFeatureGenerator(df_5m, df_15m, df_30m)
    df_live = gen.generate()
    
    # Load training data
    print("\n📂 Loading training data...")
    base_dir = os.path.join(os.path.dirname(__file__), '..', 'datasets')
    df_train_5m = pd.read_csv(os.path.join(base_dir, "BTCUSD-5m-max-data.csv"))
    df_train_15m = pd.read_csv(os.path.join(base_dir, "BTCUSD-15m-max-data.csv"))
    df_train_30m = pd.read_csv(os.path.join(base_dir, "BTCUSD-30m-max-data.csv"))
    
    for df in [df_train_5m, df_train_15m, df_train_30m]:
        col = 'datetime' if 'datetime' in df.columns else 'timestamp'
        df[col] = pd.to_datetime(df[col])
    
    gen_train = MTFFeatureGenerator(df_train_5m, df_train_15m, df_train_30m)
    df_train = gen_train.generate()
    
    # Compare feature distributions
    print("\n📈 FEATURE DISTRIBUTION COMPARISON (Live vs Training):")
    print("-" * 60)
    
    feature_cols = [c for c in df_live.columns if c not in ['open', 'high', 'low', 'close', 'volume', 'target']]
    
    for feat in feature_cols[:10]:  # Top 10 features
        live_mean = df_live[feat].iloc[-100:].mean()
        train_mean = df_train[feat].mean()
        live_std = df_live[feat].iloc[-100:].std()
        train_std = df_train[feat].std()
        
        diff_pct = abs(live_mean - train_mean) / train_std * 100 if train_std > 0 else 0
        
        status = "✅" if diff_pct < 50 else "⚠️" if diff_pct < 100 else "❌"
        print(f"{status} {feat:20s} | Live: {live_mean:8.2f} | Train: {train_mean:8.2f} | Diff: {diff_pct:.1f}%")
    
    # Analyze when training data had high probability
    print("\n🎯 ANALYZING HIGH-PROBABILITY CONDITIONS IN TRAINING DATA:")
    print("-" * 60)
    
    cols_to_drop = ['open', 'high', 'low', 'close', 'volume', 'target', 'dividends', 'stock splits']
    X_train = df_train[[c for c in df_train.columns if c not in cols_to_drop]]
    train_probs = model.predict_proba(X_train)[:, 1]
    
    high_prob_mask = train_probs >= 0.75
    high_prob_df = df_train[high_prob_mask]
    low_prob_df = df_train[~high_prob_mask]
    
    print(f"High Prob Samples: {len(high_prob_df)}")
    print(f"\nKey Feature Differences (High Prob vs Low Prob):")
    
    for feat in feature_cols[:8]:
        high_mean = high_prob_df[feat].mean()
        low_mean = low_prob_df[feat].mean()
        print(f"   {feat:20s} | High: {high_mean:8.2f} | Low: {low_mean:8.2f}")
    
    # Current market regime
    print("\n🌐 CURRENT MARKET REGIME:")
    print("-" * 60)
    latest = df_live.iloc[-1]
    
    print(f"   RSI 5m:  {latest.get('rsi_5m', 'N/A'):.2f}")
    print(f"   RSI 15m: {latest.get('rsi_15m', 'N/A'):.2f}")
    print(f"   RSI 30m: {latest.get('rsi_30m', 'N/A'):.2f}")
    print(f"   BB Width 5m:  {latest.get('bb_width_5m', 'N/A'):.4f}")
    print(f"   BB Width 15m: {latest.get('bb_width_15m', 'N/A'):.4f}")
    print(f"   MACD 5m:  {latest.get('macd_5m', 'N/A'):.2f}")
    print(f"   MACD 15m: {latest.get('macd_15m', 'N/A'):.2f}")
    
    # Price trend
    print(f"\n   Price (Current): ${df_5m['close'].iloc[-1]:.2f}")
    print(f"   Price (1h ago):  ${df_5m['close'].iloc[-12]:.2f}")
    print(f"   Price (4h ago):  ${df_5m['close'].iloc[-48]:.2f}")
    
    hourly_change = (df_5m['close'].iloc[-1] - df_5m['close'].iloc[-12]) / df_5m['close'].iloc[-12] * 100
    print(f"   1H Change: {hourly_change:+.2f}%")
    
    # Recommendations
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)
    
    X_live = df_live[[c for c in df_live.columns if c not in cols_to_drop]].iloc[-100:]
    live_probs = model.predict_proba(X_live)[:, 1]
    
    print(f"\n1. Current Probability Range: {live_probs.min():.3f} - {live_probs.max():.3f}")
    
    if live_probs.max() < 0.50:
        print("   ⚠️ Market conditions significantly different from training data")
        print("   → Consider RETRAINING model on more recent data")
        print("   → Or LOWER threshold to 0.45")
    elif live_probs.max() < 0.75:
        print("   ℹ️ Probabilities compressed but within reasonable range")
        print("   → Current threshold (0.50) should trigger soon")
    else:
        print("   ✅ Normal probability distribution")
    
    print(f"\n2. If hourly change: {hourly_change:+.2f}%")
    if hourly_change < -0.5:
        print("   → Market is bearish. Model may be correctly avoiding longs.")
    elif hourly_change > 0.5:
        print("   → Market showing bullish momentum. Should see higher probabilities soon.")
    else:
        print("   → Market is ranging. Low volatility = compressed probabilities.")
    
    print("\n3. SUGGESTED NEXT STEPS:")
    print("   A) Lower threshold to 0.45 for more signals")
    print("   B) Retrain model on last 5 days of 5m data")
    print("   C) Add a 'momentum filter' to only trade in uptrend")
    print("   D) Wait for market conditions to shift")

if __name__ == "__main__":
    analyze_market()
