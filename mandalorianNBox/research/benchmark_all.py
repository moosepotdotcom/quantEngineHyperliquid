
import backtrader as bt
import pandas as pd
import sys
import os
import datetime

# Add dashboard to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'dashboard')))

try:
    from strategies_complete import STRATEGIES
except ImportError:
    print("Error: Could not import STRATEGIES from dashboard.strategies_complete")
    sys.exit(1)

DATA_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'datasets', 'BTCUSD-1h-500wks-data.csv'))

def run_benchmark():
    print(f"Starting Benchmark on {len(STRATEGIES)} strategies...")
    print(f"Data Source: {DATA_FILE}")
    print("-" * 80)
    print(f"{'Strategy':<35} | {'Return':<10} | {'Sharpe':<8} | {'Drawdown':<10}")
    print("-" * 80)
    
    results = []

    # Filter out strategies that might be problematic or require specific complex inputs
    # converting to list to avoid runtime dict change errors if any
    strategy_names = list(STRATEGIES.keys())

    for name in strategy_names:
        strat_info = STRATEGIES[name]
        strat_class = strat_info['class']
        
        cerebro = bt.Cerebro()
        
        # Data
        if not os.path.exists(DATA_FILE):
            print(f"Error: Data file not found at {DATA_FILE}")
            return

        print(f"Testing {name:<30}...", end='', flush=True)

        data = bt.feeds.GenericCSVData(
            dataname=DATA_FILE,
            dtformat='%Y-%m-%d %H:%M:%S',
            timeframe=bt.TimeFrame.Minutes,
            compression=60,
            openinterest=-1,
            fromdate=datetime.datetime(2023, 1, 1)
        )
        cerebro.adddata(data)
        
        # Strategy
        # Use default params defined in the strategy class or the dictionary
        # We pass no specific params to let defaults take over, or extract from 'params' dict if needed
        # The STRATEGIES dict has 'params' with metadata, we should extract default values
        default_params = {}
        if 'params' in strat_info:
            for p_name, p_meta in strat_info['params'].items():
                if isinstance(p_meta, dict) and 'default' in p_meta:
                    default_params[p_name] = p_meta['default']
        
        cerebro.addstrategy(strat_class, **default_params)
        
        # Cash
        cerebro.broker.setcash(10000.0)
        cerebro.broker.setcommission(commission=0.001) # 0.1%
        
        # Analyzers
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        
        try:
            strat_runs = cerebro.run()
            strat_inst = strat_runs[0]
            
            # Metrics
            final_val = cerebro.broker.getvalue()
            pnl_pct = ((final_val - 10000) / 10000) * 100
            
            # Sharpe
            sharpe = strat_inst.analyzers.sharpe.get_analysis().get('sharperatio', None)
            
            # Drawdown
            dd = strat_inst.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0.0)
            
            # Trades
            trade_analysis = strat_inst.analyzers.trades.get_analysis()
            total_trades = trade_analysis.get('total', {}).get('total', 0)
            won_trades = trade_analysis.get('won', {}).get('total', 0)
            win_rate = (won_trades / total_trades * 100) if total_trades > 0 else 0
            
            sharpe_str = f"{sharpe:.2f}" if sharpe is not None else "N/A"
            
            print(f"{name:<35} | {pnl_pct:>9.2f}% | {sharpe_str:>8} | {dd:>9.2f}%")
            
            results.append({
                'name': name,
                'return': pnl_pct,
                'sharpe': sharpe if sharpe is not None else -100,
                'drawdown': dd,
                'win_rate': win_rate,
                'total_trades': total_trades
            })
            
        except Exception as e:
            print(f"{name:<35} | {'ERROR':>10} | {str(e)[:20]}")

    # Generate Markdown Report
    print("\n" + "="*80)
    print("BENCHMARK REPORT (Sorted by Return)")
    print("="*80)
    
    results.sort(key=lambda x: x['return'], reverse=True)
    
    report = \
"""
# Strategy Arsenal Benchmark Report
**Data Source**: 1-Hour BTC/USD
**Capital**: $10,000 | **Commission**: 0.1%

| Rank | Strategy | Return | Win Rate | Trades | Drawdown | Sharpe |
|------|----------|--------|----------|--------|----------|--------|
"""
    for i, res in enumerate(results, 1):
        sharpe_val = f"{res['sharpe']:.2f}" if res['sharpe'] != -100 else "N/A"
        line = f"| {i} | **{res['name']}** | {res['return']:.2f}% | {res['win_rate']:.1f}% | {res['total_trades']} | {res['drawdown']:.2f}% | {sharpe_val} |\n"
        report += line
        
    with open("STRATEGY_LEADERBOARD.md", "w") as f:
        f.write(report)
        
    print("\nReport saved to STRATEGY_LEADERBOARD.md")

if __name__ == "__main__":
    run_benchmark()
