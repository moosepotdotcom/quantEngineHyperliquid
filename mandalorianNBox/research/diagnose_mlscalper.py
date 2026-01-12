
"""
Diagnostic script to check live MLScalper probability distribution.
This helps understand why no trades are triggering.
"""
import os
import sys
import pandas as pd
import numpy as np
import joblib

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from research.mtf_feature_engineer import MTFFeatureGenerator
from data.loader import DataLoader

def diagnose_live():
    print("=" * 50)
    print("MLScalper Live Diagnostic")
    print("=" * 50)
    
    # 1. Fetch the same data the bot would fetch
    print("\n📥 Fetching live data (same as bot)...")
    df_5m = DataLoader.fetch_yfinance("BTC-USD", period="5d", interval="5m", quiet=True)
    df_15m = DataLoader.fetch_yfinance("BTC-USD", period="1mo", interval="15m", quiet=True)
    df_30m = DataLoader.fetch_yfinance("BTC-USD", period="1mo", interval="30m", quiet=True)
    
    print(f"   5m bars: {len(df_5m)}")
    print(f"   15m bars: {len(df_15m)}")
    print(f"   30m bars: {len(df_30m)}")
    
    if df_5m.empty or df_15m.empty or df_30m.empty:
        print("❌ ERROR: Empty dataframes!")
        return
    
    # 2. Generate MTF Features
    print("\n⚙️ Generating MTF Features...")
    try:
        gen = MTFFeatureGenerator(df_5m, df_15m, df_30m)
        df_feat = gen.generate()
        print(f"   Feature matrix shape: {df_feat.shape}")
        print(f"   Feature columns: {list(df_feat.columns)}")
    except Exception as e:
        print(f"❌ ERROR generating features: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 3. Load Model
    print("\n🤖 Loading MTF Model...")
    model_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'scalp_mtf_xgb.pkl')
    if not os.path.exists(model_path):
        print(f"❌ ERROR: Model not found at {model_path}")
        return
    model = joblib.load(model_path)
    print(f"   Model loaded: {type(model)}")
    
    # 4. Get expected features from model
    print("\n📊 Checking feature alignment...")
    try:
        model_features = model.get_booster().feature_names
        print(f"   Model expects {len(model_features)} features")
        print(f"   Sample: {model_features[:5]}...")
    except:
        model_features = None
        print("   Could not get feature names from model")
    
    # 5. Prepare features like the bot does
    cols_to_drop = ['open', 'high', 'low', 'close', 'volume', 'target', 'dividends', 'stock splits', 
                    'open_15m', 'close_15m', 'high_15m', 'low_15m', 'volume_15m', 
                    'open_30m', 'close_30m', 'high_30m', 'low_30m', 'volume_30m']
    feature_cols = [c for c in df_feat.columns if c not in cols_to_drop]
    print(f"   Available features after dropping: {len(feature_cols)}")
    
    X = df_feat[feature_cols]
    
    # 6. Run prediction on ALL recent bars
    print("\n🔮 Running predictions on recent data...")
    try:
        probs = model.predict_proba(X)[:, 1]
        
        print(f"\n   Probability Distribution (last 100 bars):")
        recent_probs = probs[-100:]
        print(f"   Min: {recent_probs.min():.4f}")
        print(f"   Max: {recent_probs.max():.4f}")
        print(f"   Mean: {recent_probs.mean():.4f}")
        print(f"   Median: {np.median(recent_probs):.4f}")
        
        print(f"\n   Threshold Analysis:")
        for t in [0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9]:
            count = np.sum(recent_probs >= t)
            print(f"   >= {t}: {count} bars ({count/len(recent_probs)*100:.1f}%)")
        
        print(f"\n   LATEST BAR:")
        print(f"   Probability: {probs[-1]:.4f}")
        print(f"   Would trigger (>0.75)? {'YES ✅' if probs[-1] > 0.75 else 'NO ❌'}")
        
    except Exception as e:
        print(f"❌ ERROR during prediction: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 7. Compare with training data distribution
    print("\n📈 Loading training data for comparison...")
    base_dir = os.path.join(os.path.dirname(__file__), '..', 'datasets')
    df_train_5m = pd.read_csv(os.path.join(base_dir, "BTCUSD-5m-max-data.csv"))
    df_train_15m = pd.read_csv(os.path.join(base_dir, "BTCUSD-15m-max-data.csv"))
    df_train_30m = pd.read_csv(os.path.join(base_dir, "BTCUSD-30m-max-data.csv"))
    
    for df in [df_train_5m, df_train_15m, df_train_30m]:
        col = 'datetime' if 'datetime' in df.columns else 'timestamp'
        df[col] = pd.to_datetime(df[col])
    
    gen_train = MTFFeatureGenerator(df_train_5m, df_train_15m, df_train_30m)
    df_train = gen_train.generate()
    X_train = df_train[[c for c in df_train.columns if c not in cols_to_drop]]
    
    train_probs = model.predict_proba(X_train)[:, 1]
    
    print(f"\n   Training Data Probability Distribution:")
    print(f"   Min: {train_probs.min():.4f}")
    print(f"   Max: {train_probs.max():.4f}")
    print(f"   Mean: {train_probs.mean():.4f}")
    print(f"   Signals >= 0.75: {np.sum(train_probs >= 0.75)}")
    
    print("\n" + "=" * 50)
    print("DIAGNOSIS COMPLETE")
    print("=" * 50)

if __name__ == "__main__":
    diagnose_live()
