import sys
import os
import json
import logging
import random
import numpy as np
import pandas as pd
import backtrader as bt
from datetime import datetime
# from tabulate import tabulate # Removed to avoid dependency issue

# Add relevant directories to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../dashboard')))

from dashboard.strategies_complete import STRATEGIES
from utils.logger import log_optimization, log_agent_action

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdvancedStrategyFuzzer:
    def __init__(self, data_path, initial_cash=10000, population_size=10, generations=5):
        self.data_path = data_path
        self.initial_cash = initial_cash
        self.population_size = population_size
        self.generations = generations
        self.results = []
        
        # Load Data once to save time
        self.df = pd.read_csv(self.data_path)
        time_col = 'timestamp' if 'timestamp' in self.df.columns else 'time'
        if time_col not in self.df.columns:
            time_col = self.df.columns[0]
        self.df[time_col] = pd.to_datetime(self.df[time_col])
        self.df.set_index(time_col, inplace=True)
        self.df.sort_index(ascending=True, inplace=True) # CRITICAL FIX: Ensure chrono order
        rename_dict = {col: col.lower() for col in self.df.columns}
        self.df.rename(columns=rename_dict, inplace=True)
        
        logger.info(f"📁 Loaded dataset. Timeframe: {self.df.index.min()} to {self.df.index.max()}")

    def generate_random_params(self, strategy_name):
        strat_info = STRATEGIES[strategy_name]
        params = {}
        for p_name, p_info in strat_info['params'].items():
            if p_info['type'] == 'int':
                params[p_name] = random.randint(p_info['min'], p_info['max'])
            elif p_info['type'] == 'float':
                params[p_name] = round(random.uniform(p_info['min'], p_info['max']), 4)
        return params

    def mutate(self, params, strategy_name):
        strat_info = STRATEGIES[strategy_name]
        mutated_params = params.copy()
        p_to_mutate = random.choice(list(mutated_params.keys()))
        p_info = strat_info['params'][p_to_mutate]
        
        if p_info['type'] == 'int':
            change = random.randint(-5, 5)
            mutated_params[p_to_mutate] = max(p_info['min'], min(p_info['max'], mutated_params[p_to_mutate] + change))
        elif p_info['type'] == 'float':
            change = random.uniform(-0.1, 0.1)
            mutated_params[p_to_mutate] = max(p_info['min'], min(p_info['max'], round(mutated_params[p_to_mutate] + change, 4)))
            
        return mutated_params

    def crossover(self, parent1, parent2):
        child = {}
        for k in parent1.keys():
            child[k] = random.choice([parent1[k], parent2[k]])
        return child

    def run_backtest(self, strategy_class, params):
        cerebro = bt.Cerebro()
        cerebro.addstrategy(strategy_class, **params)
        
        data = bt.feeds.PandasData(dataname=self.df)
        cerebro.adddata(data)
        
        cerebro.broker.setcash(self.initial_cash)
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

        try:
            strat_runs = cerebro.run()
            strat = strat_runs[0]
            
            sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0)
            drawdown = strat.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0)
            trades = strat.analyzers.trades.get_analysis()
            
            total_trades = trades.get('total', {}).get('total', 0)
            pnl = trades.get('pnl', {}).get('net', {}).get('total', 0)
            
            return {
                'params': params,
                'sharpe': sharpe if (sharpe is not None and not np.isnan(sharpe)) else -1,
                'max_drawdown': drawdown,
                'total_trades': total_trades,
                'net_profit': pnl,
                'profit_pct': (pnl / self.initial_cash) * 100
            }
        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            return None

    def fuzz_strategy_evolutionary(self, strategy_name):
        logger.info(f"🧬 Starting Evolutionary Fuzzing for {strategy_name}")
        strat_info = STRATEGIES[strategy_name]
        strat_class = strat_info['class']
        
        # Initial Population
        population = [self.generate_random_params(strategy_name) for _ in range(self.population_size)]
        
        for gen in range(self.generations):
            logger.info(f"  Generation {gen+1}/{self.generations}")
            scored_population = []
            
            for params in population:
                res = self.run_backtest(strat_class, params)
                if res:
                    scored_population.append(res)
            
            if not scored_population:
                logger.warning(f"No successful runs in generation {gen+1}")
                break
                
            # Sort by Profit (Fitness)
            scored_population.sort(key=lambda x: x['net_profit'], reverse=True)
            
            # Keep top 50%
            survivors = scored_population[:self.population_size // 2]
            
            # New Population: Survivors + Crossovers + Mutations
            new_population = [s['params'] for s in survivors]
            
            while len(new_population) < self.population_size:
                if len(survivors) >= 2 and random.random() < 0.7: # Crossover
                    p1, p2 = random.sample(survivors, 2)
                    new_population.append(self.crossover(p1['params'], p2['params']))
                else: # Mutation
                    p = random.choice(survivors)
                    new_population.append(self.mutate(p['params'], strategy_name))
            
            population = new_population
            
            # Log best of generation
            best = scored_population[0]
            logger.info(f"  Best so far: Profit ${best['net_profit']:.2f} | Sharpe: {best['sharpe']:.2f}")

        # Final Best
        if scored_population:
            best_overall = scored_population[0]
            best_overall['strategy'] = strategy_name
            self.results.append(best_overall)
            
            # Log to Journal
            log_optimization({
                'profit': best_overall['profit_pct'],
                'sharpe': best_overall['sharpe'],
                'params': best_overall['params']
            })
            return best_overall
        return None

    def run_all_strategies(self):
        log_agent_action("Fuzzer Sweep", f"Starting advanced fuzzy optimization on {len(STRATEGIES)} strategies.")
        for s in STRATEGIES.keys():
            try:
                self.fuzz_strategy_evolutionary(s)
            except Exception as e:
                logger.error(f"❌ Failed to fuzz {s}: {e}")
        
        # Save results
        with open('research/optimization_leaderboard.json', 'w') as f:
            json.dump(self.results, f, indent=4)
            
    def display_results(self):
        sorted_results = sorted(self.results, key=lambda x: x['net_profit'], reverse=True)
        display_data = []
        for r in sorted_results[:10]:
            display_data.append([r['strategy'], f"${r['net_profit']:.2f}", f"{r['sharpe']:.2f}", f"{r['max_drawdown']:.2f}%"])
        
        print("\n🏆 ADVANCED FUZZER LEADERBOARD 🏆")
        print(f"{'Strategy':<30} | {'Profit ($)':<12} | {'Sharpe':<8} | {'Max DD':<10}")
        print("-" * 65)
        for r in sorted_results[:10]:
            print(f"{r['strategy']:<30} | ${r['net_profit']:<11.2f} | {r['sharpe']:<8.2f} | {r['max_drawdown']:<10.2f}%")

if __name__ == "__main__":
    # Use relative path for portability
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_file = os.path.join(base_dir, "datasets", "BTCUSD-1h-500wks-data.csv")
    if not os.path.exists(data_file):
        # Autodetect any csv in datasets
        datasets = os.listdir('datasets')
        csvs = [d for d in datasets if d.endswith('.csv')]
        if csvs:
            data_file = os.path.join('datasets', csvs[0])
            
    fuzzer = AdvancedStrategyFuzzer(data_file, population_size=12, generations=3)
    # Targeted sweep for God Mode Benchmark
    targeted_list = ['SMA Crossover', 'RSI Strategy', 'SMA + ADX + Bollinger + Volume', 'Mean Reversion', 'Turtle Trading']
    for s in targeted_list:
        try:
            fuzzer.fuzz_strategy_evolutionary(s)
        except Exception as e:
            logger.error(f"❌ Failed to fuzz {s}: {e}")
    fuzzer.display_results()
