
import backtrader as bt
import pandas as pd
import datetime
import sys
import os
import multiprocessing

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from strategies.ml_predictor import MLPredictorStrategy
from data.loader import DataLoader
from utils.logger import log_optimization

def run_optimization():
    cerebro = bt.Cerebro(optreturn=False)

    # 1. Parameter Grid (Genetic Search Space)
    cerebro.optstrategy(
        MLPredictorStrategy,
        train_len=[500],             # Fixed
        retrain_freq=[500],          # Fixed
        rsi_period=[10, 14, 21],     # Optimize
        roc_period=[5, 10],          # Optimize
        stop_loss_pct=[1.0, 2.0, 5.0, 10.0] # Optimize
    )

    # 2. Data Loading (Hardcoded for now, can be dynamic)
    # Using the 15m 2022 dataset for "Bear Market" Stress Test
    data_path = "Open-AI-Assistants for Bootcamp Members Only/BTC-USD-15m-2022-1-01.csv"
    
    # Handle CSV loading manually since we aren't using the dashboard engine
    df = pd.read_csv(data_path)
    if 'datetime' in df.columns:
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
    elif 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)

    # 3. Settings
    cerebro.broker.set_cash(10000)
    cerebro.broker.setcommission(commission=0.001)
    # Use Fixed Size to test Strategy Logic purely (avoid leverage blowups)
    cerebro.addsizer(bt.sizers.PercentSizer, percents=10) 

    # 4. Analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')

    print("🚀 Starting Optimization... This may take a while.")
    
    # Run Optimization
    # maxcpus=1 to avoid issues with ML inside multiprocessing (sklearn can deadlock)
    # If standard params, we could use more cpus.
    results = cerebro.run(maxcpus=1) 
    
    # 5. Process Results
    final_results_list = []
    
    for run in results:
        for strategy in run:
            profit = strategy.broker.get_value() - 10000
            
            # Extract Params
            params = {
                'rsi_period': strategy.params.rsi_period,
                'roc_period': strategy.params.roc_period,
                'stop_loss_pct': strategy.params.stop_loss_pct,
                'profit': profit,
                'sharpe': strategy.analyzers.sharpe.get_analysis().get('sharperatio', 0),
                'drawdown': strategy.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0)
            }
            final_results_list.append(params)

    # Sort and Save
    results_df = pd.DataFrame(final_results_list)
    results_df = results_df.sort_values(by='profit', ascending=False)
    
    print("\n🏆 OPTIMIZATION RESULTS (Top 5):")
    print(results_df.head(5))
    
    print(results_df.head(5))
    
    # Auto-Update Journal
    best = results_df.iloc[0]
    log_optimization(best)

    results_df.to_csv('optimization_results.csv', index=False)
    print("\n✅ Results saved to optimization_results.csv")

if __name__ == '__main__':
    run_optimization()
