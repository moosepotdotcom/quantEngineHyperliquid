import pickle
import sys

try:
    with open('/Users/alifiyaa/Downloads/quantEngineHyperliquid/HYBRID_V1_EXPORT/feature_names.pkl', 'rb') as f:
        features = pickle.load(f)
    print(f"Features in HYBRID_V1_EXPORT: {len(features)}")
    print("Sample features:")
    for feat in features[:20]:
        print(f"  - {feat}")
        
    print("\nChecking for '21'...")
    has_21 = any('21' in f for f in features)
    print(f"Has Period 21 features? {has_21}")
    
    match_21 = [f for f in features if '21' in f]
    print(f"Matches: {match_21[:10]}")

except Exception as e:
    print(f"Error: {e}")
