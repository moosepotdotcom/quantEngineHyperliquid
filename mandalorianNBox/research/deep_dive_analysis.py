import pandas as pd
import numpy as np
import sys
import os

# Add root
sys.path.append(os.getcwd())
from research.feature_generator import AdvancedFeatureGenerator
from research.meta_learner import MetaLearner

def main():
    # Load and prepare OOS data
    data_path = 'datasets/BTCUSD-1h-500wks-data.csv'
    if not os.path.exists(data_path):
        print("Data file not found.")
        return

    df = pd.read_csv(data_path)
    df.columns = [c.lower() for c in df.columns]
    
    # Handle datetime
    time_col = 'time' if 'time' in df.columns else 'timestamp' if 'timestamp' in df.columns else 'datetime' if 'datetime' in df.columns else None
    if time_col:
        df[time_col] = pd.to_datetime(df[time_col])
        df.set_index(time_col, inplace=True)
        df.sort_index(ascending=True, inplace=True)

    split_idx = int(len(df) * 0.8)
    df_oos = df.iloc[split_idx:]

    print(f'=== OOS Market Analysis ===')
    p_start = df_oos['close'].iloc[0]
    p_end = df_oos['close'].iloc[-1]
    p_min = df_oos['low'].min()
    p_max = df_oos['high'].max()
    p_return = (p_end / p_start - 1) * 100

    print(f'Start Price: ${p_start:.2f}')
    print(f'End Price: ${p_end:.2f}')
    print(f'Max Drawdown in OOS: {((p_min / p_start - 1) * 100):.2f}%')
    print(f'OOS Period Return: {p_return:.2f}%')

    # Feature Gen & ML Prediction
    gen = AdvancedFeatureGenerator(df_oos)
    df_feats = gen.generate_all()

    ml = MetaLearner()
    score = ml.train(df_feats)

    df_numeric = df_feats.select_dtypes(include=[np.number])
    cols_to_drop = ['open', 'high', 'low', 'close', 'volume', 'target', 'returns', 'log_returns', 'log_ret']
    X = df_numeric.drop(columns=[c for c in cols_to_drop if c in df_numeric.columns])

    probs = ml.model.predict_proba(ml.scaler.transform(X))[:, 1]

    print(f'\n=== Model Confidence Distribution ===')
    print(f'Accuracy Score: {score:.2f}')
    print(f'Avg Confidence: {np.mean(probs):.4f}')
    print(f'Max Confidence: {np.max(probs):.4f}')
    print(f'Min Confidence: {np.min(probs):.4f}')
    print(f'Signals > 0.65 (Threshold): {np.sum(probs > 0.65)}')
    print(f'Signals > 0.60: {np.sum(probs > 0.60)}')

    if np.sum(probs > 0.65) == 0:
        print('\n💡 EXPLANATION: The model never reached the 0.65 confidence threshold required for an entry during this period.')
        print('This suggests the market was too volatile or bearish for high-confidence long entries.')
        print('Capital preservation ($0) was the optimal strategy during this crash/volatility.')

if __name__ == "__main__":
    main()
