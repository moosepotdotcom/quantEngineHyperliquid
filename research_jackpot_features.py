
import pandas as pd
import sys
import os
import joblib
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# Add root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.v5_feature_engineer import generate_v5_features

def research_jackpot_features():
    print("🔬 Deep Dive: Finding the 'Jackpot Code' (Feature Importance)...")
    
    # 1. Load Data (Jan 2026)
    data_path = 'training/data/BTC_5m_2025_enriched.csv'
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df[df['timestamp'] >= '2026-01-01'].copy().reset_index(drop=True)
    
    # 2. Re-create V6 Volatility Signal
    model = joblib.load('model_engines/v6_grid/weights/vol_model.pkl')
    
    print("   🧠 Generating Features...")
    df_enriched = generate_v5_features(df)
    
    drop_cols_engine = ['timestamp', 'target', 'open', 'high', 'low', 'close', 
                 'taker_buy_base', 'taker_sell_base', 'future_high', 'future_low', 'future_range_pct',
                 'prob_low', 'prob_high', 'jackpot_label']
                 
    features = [c for c in df_enriched.columns if c not in drop_cols_engine]
    
    # Predict Regimes
    probs = model.predict_proba(df_enriched[features])
    df_enriched['prob_high_vol'] = probs[:, 2]
    
    # 3. Filter for High Volatility Events ONLY
    # We want to know: Among the "Danger Zones", which ones were actually "Golden Opportunities"?
    high_vol_df = df_enriched[df_enriched['prob_high_vol'] > 0.70].copy()
    
    if len(high_vol_df) < 50:
        print("   ⚠️ Not enough High Vol events to analyze.")
        return
        
    print(f"   found {len(high_vol_df)} High Volatility Events to Analyze.")
    
    # 4. Create "Jackpot Labels"
    # Look 2 hours ahead (24 candles)
    # Label 1: Pump > 1.0% (AND no dump > 0.5% first)
    # Label 2: Dump < -1.0% (AND no pump > 0.5% first)
    # Label 0: Choppy / Whipsaw / Small Move
    
    labels = []
    
    # We need to access the full dataframe for future price, mapping by index
    # (high_vol_df is a subset, indices are preserved)
    
    for idx in high_vol_df.index:
        if idx >= len(df_enriched) - 24:
            labels.append(0)
            continue
            
        entry_price = df_enriched.loc[idx, 'close']
        future = df_enriched.iloc[idx+1:idx+25]
        
        # Check path
        outcome = 0
        
        for _, candle in future.iterrows():
            pct_change = (candle['close'] - entry_price) / entry_price
            
            if pct_change > 0.01: # +1%
                outcome = 1 # PUMP
                break
            if pct_change < -0.01: # -1%
                outcome = 2 # DUMP
                break
                
            # Stop Loss Check (if we entered early, would we die?)
            # Actually let's keeps it simple: Did it go +1% or -1% first?
            
        labels.append(outcome)
        
    high_vol_df['jackpot_label'] = labels
    
    print("\n   📊 Event Distribution:")
    print(f"      No Major Move (0): {len(high_vol_df[high_vol_df['jackpot_label']==0])}")
    print(f"      Jackpot PUMP  (1): {len(high_vol_df[high_vol_df['jackpot_label']==1])}")
    print(f"      Jackpot DUMP  (2): {len(high_vol_df[high_vol_df['jackpot_label']==2])}")
    
    # 5. Train Classifier to distinguish (0 vs 1 vs 2)
    # Or simpler: (0 vs 1/2) -> Is it a Trade? 
    # Let's try to predict DIRECTION (1 vs 2). Because if we know direction, we get rich.
    
    directional_df = high_vol_df[high_vol_df['jackpot_label'].isin([1, 2])].copy()
    
    if len(directional_df) < 10:
        print("   ⚠️ Not enough directional events.")
        return
        
    X = directional_df[features]
    y = directional_df['jackpot_label']
    
    clf = RandomForestClassifier(n_estimators=100, max_depth=4, random_state=42)
    clf.fit(X, y)
    
    # 6. Feature Importance
    print("\n   🔑 TOP PREDICTORS of Direction (Pump vs Dump):")
    importances = pd.Series(clf.feature_importances_, index=features).sort_values(ascending=False)
    print(importances.head(10))
    
    # 7. Extract Rules (Decision Tree)
    tree = DecisionTreeClassifier(max_depth=3, random_state=42)
    tree.fit(X, y)
    
    print("\n   📜 Simple Rules:")
    print(export_text(tree, feature_names=features))

if __name__ == "__main__":
    research_jackpot_features()
