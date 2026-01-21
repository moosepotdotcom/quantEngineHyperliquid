
import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
import os
import sys

# Add root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.v5_feature_engineer import generate_v5_features

def train_volatility_model():
    print("🚀 Starting Volatility Engine (V6) Training...")
    
    # 1. Load Data
    data_path = 'training/data/BTC_5m_2025_enriched.csv'
    if not os.path.exists(data_path):
        print(f"❌ Data not found: {data_path}")
        return

    print("   📂 Loading Data...")
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # 2. Features (V5 MTF)
    print("   🧠 Generating Features (Order Flow + MTF Trend)...")
    df = generate_v5_features(df)
    
    # 3. Labeling for VOLATILITY
    print("   🏷️  Labeling Volatility (Future 1h Range)...")
    
    # We want to predict the "Range" of the next 1 hour (12 candles)
    # Range = (Max High - Min Low) / Open
    
    indexer = pd.api.indexers.FixedForwardWindowIndexer(window_size=12)
    df['future_high'] = df['high'].rolling(window=indexer).max()
    df['future_low'] = df['low'].rolling(window=indexer).min()
    df['future_range_pct'] = (df['future_high'] - df['future_low']) / df['close']
    
    # Define Classes based on Quantiles
    # Low Vol (Chop) vs High Vol (Trend/Crash)
    
    # Let's look at the distribution
    df.dropna(subset=['future_range_pct'], inplace=True)
    
    # Thresholds (we can tune these)
    # Bottom 40% = LOW VOL (Safe for Grid)
    # Top 30%    = HIGH VOL (Danger/Opportunity)
    # Middle 30% = MEDIUM
    
    low_thresh = df['future_range_pct'].quantile(0.40)
    high_thresh = df['future_range_pct'].quantile(0.70)
    
    print(f"   📊 Volatility Thresholds:")
    print(f"      Low Vol (< {low_thresh:.2%}): Safe for Tight Grid")
    print(f"      High Vol (> {high_thresh:.2%}): Danger Zone")
    
    conditions = [
        (df['future_range_pct'] <= low_thresh),
        (df['future_range_pct'] >= high_thresh)
    ]
    choices = [0, 2] # 0=Low, 2=High. (1=Medium implicitly)
    
    df['target'] = np.select(conditions, choices, default=1)
    
    # 4. Train/Test Split (Time based)
    split_date = '2026-01-01'
    train_df = df[df['timestamp'] < split_date]
    test_df = df[df['timestamp'] >= split_date]
    
    print(f"   📊 Train Set: {len(train_df)}")
    print(f"   📊 Test Set:  {len(test_df)}")
    
    # 5. XGBoost
    features = [c for c in df.columns if c not in ['timestamp', 'target', 'open', 'high', 'low', 'close', 
                                                 'taker_buy_base', 'taker_sell_base', 'future_high', 'future_low', 'future_range_pct']]
                                                 
    X_train = train_df[features]
    y_train = train_df['target']
    X_test = test_df[features]
    y_test = test_df['target']
    
    model = xgb.XGBClassifier(
        n_estimators=1000,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        objective='multi:softprob',
        num_class=3,
        n_jobs=-1,
        early_stopping_rounds=50,
        eval_metric='mlogloss'
    )
    
    print("   🏋️  Training Volatility Predictor...")
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=100
    )
    
    # 6. Evaluate
    print("\n   🔍 Evaluation (Jan 2026):")
    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)
    
    from sklearn.metrics import classification_report, accuracy_score
    print(classification_report(y_test, preds))
    
    # Specifically check prediction of HIGH VOLATILITY (Class 2)
    # This is critical to avoid blowing up the grid bot.
    
    test_df = test_df.copy()
    test_df['prob_high_vol'] = probs[:, 2]
    test_df['prob_low_vol'] = probs[:, 0]
    
    high_vol_alert = test_df[test_df['prob_high_vol'] > 0.70]
    if len(high_vol_alert) > 0:
        precision = (high_vol_alert['target'] == 2).mean()
        print(f"   ⚠️ High Vol Prediction (>70% Conf): {precision:.1%} Correct ({len(high_vol_alert)} alerts)")
    
    # Check Low Vol Prediction
    low_vol_safe = test_df[test_df['prob_low_vol'] > 0.70]
    if len(low_vol_safe) > 0:
        precision = (low_vol_safe['target'] == 0).mean()
        print(f"   ✅ Low Vol Prediction (>70% Conf): {precision:.1%} Correct ({len(low_vol_safe)} safe zones)")

    # Save
    os.makedirs('model_engines/volatility_v1/weights', exist_ok=True)
    joblib.dump(model, 'model_engines/volatility_v1/weights/vol_model.pkl')
    print("   💾 Model Saved: model_engines/volatility_v1/weights/vol_model.pkl")

if __name__ == "__main__":
    train_volatility_model()
