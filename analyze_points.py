
import pandas as pd
import numpy as np

def analyze():
    print("📊 POINTS CAPTURED ANALYSIS")
    print("--------------------------------------------------")
    
    try:
        df = pd.read_csv('portfolio_trades.csv')
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return

    # Points Calculation
    # For Long: Exit - Entry
    # For Short: Entry - Exit
    
    df['points'] = 0.0
    
    for i, row in df.iterrows():
        if row['type'] == 'LONG':
            points = row['exit'] - row['entry']
        else:
            points = row['entry'] - row['exit']
        df.at[i, 'points'] = points
        
    # Group by Coin
    stats = df.groupby('coin').agg({
        'points': ['sum', 'mean'],
        'pnl': 'sum',
        'outcome': 'count'
    })
    
    stats.columns = ['total_points', 'avg_points', 'total_pnl_pct', 'trades']
    stats['avg_move_pct'] = (df.groupby('coin')['points'].sum() / df.groupby('coin')['entry'].mean()) * 100
    
    # Calculate Average Price for reference
    avg_prices = df.groupby('coin')['entry'].mean()
    
    print(f"{'Coin':<8} | {'Trades':<6} | {'Avg Price':<12} | {'Total Points':<12} | {'Avg Points':<12} | {'Avg Move':<10}")
    print("-" * 80)
    
    for coin in stats.index:
        row = stats.loc[coin]
        avg_price = avg_prices.loc[coin]
        
        # PnL % sum * 100
        pnl_sum = row['total_pnl_pct'] * 100
        
        # Format
        avg_pts_str = f"{row['avg_points']:.4f}"
        if avg_price > 1000: avg_pts_str = f"{row['avg_points']:.2f}"
        
        tot_pts_str = f"{row['total_points']:.4f}"
        if avg_price > 1000: tot_pts_str = f"{row['total_points']:.2f}"
        
        print(f"{coin:<8} | {row['trades']:<6} | ${avg_price:<11.2f} | {tot_pts_str:<12} | {avg_pts_str:<12} | {row['avg_move_pct']:.2f}%")
        
    print("-" * 80)
    print("\n💡 INTERPRETATION:")
    print("   'Points' = Dollar price movement captured per trade.")
    print("   'Avg Move' = Average % price change captured per coin.")

if __name__ == "__main__":
    analyze()
