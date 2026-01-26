import pandas as pd
import numpy as np
import sys

def calculate_metrics(csv_path):
    df = pd.read_csv(csv_path)
    if df.empty:
        print("Empty log.")
        return

    # Basic Metrics
    initial_balance = 1000.0
    final_balance = df['balance'].iloc[-1]
    roi = ((final_balance - initial_balance) / initial_balance) * 100
    win_rate = (df['outcome'].str.contains('TP')).mean() * 100
    total_trades = len(df)
    
    # Returns for Sharpe/Sortino
    # Assuming each trade is a 'period' for this context
    returns = df['pnl'] / (df['balance'] - df['pnl'])
    
    avg_return = returns.mean()
    std_return = returns.std()
    
    # Yearly scaling (rough estimate: ~100 trades a month -> 1200 trades a year)
    ann_factor = np.sqrt(1200) 
    
    sharpe = (avg_return / std_return) * ann_factor if std_return != 0 else 0
    
    downside_std = returns[returns < 0].std()
    sortino = (avg_return / downside_std) * ann_factor if downside_std != 0 else sharpe
    
    # Max Drawdown
    df['peak'] = df['balance'].cummax()
    df['drawdown'] = (df['balance'] - df['peak']) / df['peak']
    max_dd = df['drawdown'].min() * 100
    
    # Profit Factor
    gross_profit = df[df['pnl'] > 0]['pnl'].sum()
    gross_loss = abs(df[df['pnl'] < 0]['pnl'].sum())
    profit_factor = gross_profit / gross_loss if gross_loss != 0 else np.inf

    print(f"--- QUANTITATIVE REPORT: {csv_path} ---")
    print(f"ROI: {roi:.2f}%")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Total Trades: {total_trades}")
    print(f"Profit Factor: {profit_factor:.2f}")
    print(f"Sharpe Ratio: {sharpe:.2f}")
    print(f"Sortino Ratio: {sortino:.2f}")
    print(f"Max Drawdown: {max_dd:.2f}%")
    
    print("\n--- RECENT TRADE LOG ---")
    print(df[['timestamp', 'side', 'entry', 'exit', 'outcome', 'pnl', 'balance']].tail(15).to_markdown(index=False))

if __name__ == "__main__":
    calculate_metrics(sys.argv[1])
