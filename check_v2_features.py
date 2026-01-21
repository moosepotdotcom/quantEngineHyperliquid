
import joblib
import os
import pandas as pd
import numpy as np

model_path = '/Users/alifiyaa/Downloads/quantEngineHyperliquid/models/mtf_scalper_5m_v2_calibrated.pkl'
if os.path.exists(model_path):
    model = joblib.load(model_path)
    
    # Force an error by passing a dataframe with the wrong shape/names
    try:
        X = pd.DataFrame(np.zeros((1, 1)), columns=['dummy_feature'])
        model.predict_proba(X)
    except Exception as e:
        print(f"EXPECTED ERROR: {e}")
else:
    print("Model not found")
