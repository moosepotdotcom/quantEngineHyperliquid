import sys
import os
import json
import logging
from datetime import datetime
import pandas as pd
import backtrader as bt
from tabulate import tabulate

# Add relevant directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../dashboard'))

from strategies_complete import STRATEGIES

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StrategyFuzzer:
    def __init__(self, data_path, initial_cash=10000):
        self.data_path = data_path
        self.initial_cash = initial_cash
        self.results = []
        
    def run_fuzz(self, strategy_name):
        logger.info(f"🧪 Fuzzing Strategy: {strategy_name}")
        strat_info = STRATEGIES[strategy_name]
        strat_class = strat_info['class']
        
        # Prepare optimization parameters
        opt_params = {}
        for p_name, p_info in strat_info['params'].items():
            if p_info['type'] in ['int', 'float']:
                # Simple fuzz range: [default*0.5, default, default*1.5]
                # In a real fuzzer, we'd use a more granular range or genetic algo
                default = p_info['default']
                if p_info['type'] == 'int':
                    low = max(p_info['min'], int(default * 0.7))
                    high = min(p_info['max'], int(default * 1.3))
                    step = max(1, (high - low) // 3)
                    opt_params[p_name] = range(low, high + 1, step)
                else:
                    low = max(p_info['min'], default * 0.7)
                    high = min(p_info['max'], default * 1.3)
                    opt_params[p_name] = [low, default, high]

        cerebro = bt.Cerebro(optreturn=True)
        cerebro.optstrategy(strat_class, **opt_params)

        # Load Data
        df = pd.read_csv(self.data_path)
        
        # Check for column names
        time_col = 'timestamp' if 'timestamp' in df.columns else 'time'
        if time_col not in df.columns:
            # If neither found, use the first column as index
            time_col = df.columns[0]
            
        df[time_col] = pd.to_datetime(df[time_col])
        df.set_index(time_col, inplace=True)
        
        # EnsureOHLCV column naming for Backtrader
        rename_dict = {col: col.lower() for col in df.columns}
        df.rename(columns=rename_dict, inplace=True)
        
        data = bt.feeds.PandasData(dataname=df)
        cerebro.adddata(data)
        
        cerebro.broker.setcash(self.initial_cash)
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

        # Run optimization
        optimized_runs = cerebro.run()
        
        for run in optimized_runs:
            for strategy in run:
                p = strategy.params.__dict__
                sharpe = strategy.analyzers.sharpe.get_analysis().get('sharperatio', 0)
                drawdown = strategy.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0)
                trades = strategy.analyzers.trades.get_analysis()
                
                total_trades = trades.get('total', {}).get('total', 0)
                pnl = trades.get('pnl', {}).get('net', {}).get('total', 0)
                
                self.results.append({
                    'strategy': strategy_name,
                    'params': p,
                    'sharpe': sharpe if sharpe is not None else 0,
                    'max_drawdown': drawdown,
                    'total_trades': total_trades,
                    'net_profit': pnl,
                    'profit_pct': (pnl / self.initial_cash) * 100
                })

    def get_leaderboard(self):
        sorted_results = sorted(self.results, key=lambda x: x['net_profit'], reverse=True)
        return sorted_results

if __name__ == "__main__":
    # Full Optimization Sweep for BTC
    # Use relative path for portability
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_file = os.path.join(base_dir, "datasets", "BTCUSD-1h-500wks-data.csv")
    fuzzer = StrategyFuzzer(data_file)
    
    # Run sweep on ALL strategies in the registry
    logger.info("🚀 Starting Full Optimization Sweep on BTC Hourly...")
    for s in STRATEGIES.keys():
        try:
            fuzzer.run_fuzz(s)
        except Exception as e:
            logger.error(f"❌ Failed to fuzz {s}: {e}")
        
    leaderboard = fuzzer.get_leaderboard()
    print("\n🏆 BTC OPTIMIZATION LEADERBOARD (HOURLY) 🏆")
    
    # Save full results to JSON for the ML model to use
    with open('research/btc_leaderboard.json', 'w') as f:
        json.dump(leaderboard, f, indent=4)
        
    display_data = []
    for r in leaderboard[:15]:
        display_data.append([r['strategy'], f"{r['net_profit']:.2f}", f"{r['sharpe']:.2f}", f"{r['max_drawdown']:.2f}%"])
    
    print(tabulate(display_data, headers=['Strategy', 'Profit ($)', 'Sharpe', 'Max DD'], tablefmt='grid'))
    print(f"\n✅ Full sweep complete. Results saved to research/btc_leaderboard.json")
