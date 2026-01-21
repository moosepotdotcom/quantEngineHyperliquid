import pandas as pd
import numpy as np

def analyze_patterns(file_path):
    df = pd.read_csv(file_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Calculate returns over 5-minute windows
    results = []
    
    coins = df['coin'].unique()
    for coin in coins:
        c_df = df[df['coin'] == coin].copy().sort_values('timestamp')
        c_df['return_5m'] = c_df['price'].pct_change(periods=1).shift(-1) # Next row is ~5m later
        
        # High Impact Moves (>0.1%)
        big_moves = c_df[abs(c_df['return_5m']) > 0.0008]
        
        for idx, row in big_moves.iterrows():
            # Look at state BEFORE the move
            pre_state = row
            
            # Check market convergence (how many others were in same dir?)
            ts = row['timestamp']
            others = df[(df['timestamp'] == ts) & (df['coin'] != coin)]
            dir = 1 if row['return_5m'] > 0 else -1
            
            others_dir = 0
            for _, o in others.iterrows():
                if o['imbalance'] * dir > 0:
                    others_dir += 1
            
            results.append({
                'coin': coin,
                'time': ts,
                'move': row['return_5m'],
                'pre_imb': row['imbalance'],
                'convergence': others_dir,
                'whale_ratio': (row['whale_bids'] - row['whale_asks']) * dir
            })
            
    res_df = pd.DataFrame(results)
    print("\n--- BIG MOVE ANALYSIS ---")
    # Print sorted by absolute move size
    res_df['abs_move'] = res_df['move'].abs()
    print(res_df.sort_values('abs_move', ascending=False).to_string())
    
    # Summary of winning cues
    print("\n--- WINNING CUES SUMMARY ---")
    avg_imb = res_df['pre_imb'].abs().mean()
    print(f"Avg Imbalance before Big Move: {avg_imb:.2f}")
    print(f"Avg Convergence (Others in Sync): {res_df['convergence'].mean():.1f} / 4")

if __name__ == "__main__":
    analyze_patterns('/Users/alifiyaa/Downloads/quantEngineHyperliquid/MANDALORIAN_ENGINE/PHASE4_PRECISION/multi_asset_data.csv')
