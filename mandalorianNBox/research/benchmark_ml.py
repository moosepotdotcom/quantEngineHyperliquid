import sys
import os
import json
import logging
import pandas as pd
from datetime import datetime

# Add dashboard to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../dashboard'))

from backtest_engine import run_backtest

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_benchmarks():
    data_file = "BTCUSD-1h-500wks-data.csv"
    results = []

    # 1. Run Quantum ML Strategy
    logger.info("🧪 Running Quantum ML Strategy Benchmark...")
    quantum_res = run_backtest(
        "Quantum ML Strategy",
        {}, # Defaults
        data_file,
        '2022-01-01',
        '2024-12-31'
    )
    results.append(quantum_res)

    # 2. Run Top Strategy from Fuzzer (if available)
    if os.path.exists('research/btc_leaderboard.json'):
        with open('research/btc_leaderboard.json', 'r') as f:
            leaderboard = json.load(f)
            if leaderboard:
                top_strat = leaderboard[0]
                logger.info(f"🏆 Running Fuzzer Champion: {top_strat['strategy']}...")
                top_res = run_backtest(
                    top_strat['strategy'],
                    top_strat['params'],
                    data_file,
                    '2022-01-01',
                    '2024-12-31'
                )
                results.append(top_res)

    # 3. Simple Benchmark (SMA Crossover)
    logger.info("📉 Running Baseline SMA Benchmark...")
    baseline_res = run_backtest(
        "SMA Crossover",
        {'fast_period': 10, 'slow_period': 20},
        data_file,
        '2022-01-01',
        '2024-12-31'
    )
    results.append(baseline_res)

    print("\n📊 BENCHMARK COMPARISON 📊")
    for res in results:
        if 'error' in res:
            print(f"❌ {res.get('strategy', 'Unknown')}: {res['error']}")
        else:
            print(f"✅ {res['strategy']}: Profit: ${res['profit']:.2f} ({res['profit_pct']:.2f}%) | Sharpe: {res['sharpe_ratio']:.2f}")

if __name__ == "__main__":
    run_benchmarks()
