
import sys
import os
import logging


# Add relevant directories to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../dashboard')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../optimization')))

from optimization.strategy_fuzzer import AdvancedStrategyFuzzer
from dashboard.strategies_complete import STRATEGIES, ConsolidationPopStrategy, SMAStrategy

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_fuzzing_jobs():
    jobs = [
        {
            'name': 'Swing Engine (Consolidation Pop)',
            'strategy_name': 'Consolidation Pop',
            'strategy_class': ConsolidationPopStrategy,
            'data_file': 'datasets/BTCUSD-6h-500wks-data.csv',
            'cash': 100000,
            'generations': 5,
            'size': 10
        },
        {
            'name': 'Investor Engine (Golden Cross)',
            'strategy_name': 'SMA Crossover',
            'strategy_class': SMAStrategy,
            'data_file': 'datasets/BTCUSD-1d-1000wks-data.csv', # Using the 1d file (note name check)
            'cash': 100000,
            'generations': 5,
            'size': 10
        }
    ]

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    print("\n" + "="*60)
    print("🚀 STARTING MULTI-ENGINE FUZZING MATRIX")
    print("="*60 + "\n")

    for job in jobs:
        print(f"\n🔍 FUZZING: {job['name']}")
        print(f"   Data: {job['data_file']}")
        print(f"   Strategy: {job['strategy_name']}")
        
        data_path = os.path.join(base_dir, job['data_file'])
        
        # Verify file exists
        if not os.path.exists(data_path):
            print(f"❌ ERROR: Data file not found: {data_path}")
            # Try alternative 1d file if necessary
            if '1d' in job['data_file']:
                 alt_path = os.path.join(base_dir, 'datasets/BTCUSD-1d-500wks-data.csv') # Guessing name from earlier "1d-500wks" vs "1d-1000wks"
                 print(f"   Trying alternative: {alt_path}")
                 if os.path.exists(alt_path):
                     data_path = alt_path
                 else:
                     continue
        
        fuzzer = AdvancedStrategyFuzzer(
            data_path=data_path,
            initial_cash=job['cash'],
            population_size=job['size'],
            generations=job['generations']
        )
        
        start_params = fuzzer.generate_random_params(job['strategy_name'])
        # For SMA, force reasonable defaults for first individual
        if job['strategy_name'] == 'SMA Crossover':
             start_params = {'fast_period': 50, 'slow_period': 200}

        best_result = fuzzer.fuzz_strategy_evolutionary(job['strategy_name'])
        
        print("\n🏆 WINNER FOR " + job['name'])
        print(f"   Sharpe: {best_result['sharpe']:.4f}")
        print(f"   Return: {best_result['profit_pct']:.2f}%")
        print(f"   Params: {best_result['params']}")
        print("-" * 40)

if __name__ == "__main__":
    run_fuzzing_jobs()
