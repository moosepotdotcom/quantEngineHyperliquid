
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

# DATA_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'datasets', 'BTCUSD-1h-500wks-data.csv'))
# We will check for the file in the main block

class SQN(bt.Analyzer):
    """
    System Quality Number (SQN) Analyzer
    SQN = (Expectancy / StdDev(R)) * Sqrt(N)
    """
    def create_analysis(self):
        self.rets = {}
        self.vals = {}

    def stop(self):
        pass # Calculate in get_analysis if needed

def run_benchmark():
    # LOCATE DATA
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(curr_dir, '..', 'datasets')
    
    # Try different data files relative to priority
    files = [f for f in os.listdir(data_dir) if f.endswith('.csv') and 'BTC' in f]
    if not files:
        print("No Data found in datasets/")
        return
        
    # Prefer the 1h data
    data_file = next((f for f in files if '1h' in f), files[0])
    data_path = os.path.join(data_dir, data_file)

    print(f"Starting Grand Redesign Benchmark...")
    print(f"Strategies: {len(STRATEGIES)}")
    print(f"Data Source: {data_file}")
    print("-" * 100)
    print(f"{'Strategy':<35} | {'Return':<10} | {'WinRate':<8} | {'Trades':<8} | {'Drawdown':<10} | {'Sharpe':<8}")
    print("-" * 100)
    
    results = []
    strategy_names = list(STRATEGIES.keys())

    for name in strategy_names:
        strat_info = STRATEGIES[name]
        strat_class = strat_info['class']
        
        cerebro = bt.Cerebro()
        
        # Data
        # Data via Pandas (Safer for sorting)
        df = pd.read_csv(data_path)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime', ascending=True) # Force Ascending
        df.set_index('datetime', inplace=True)
        
        data = bt.feeds.PandasData(
            dataname=df,
            timeframe=bt.TimeFrame.Minutes,
            compression=60,
            openinterest=-1,
            fromdate=datetime.datetime(2023, 1, 1)
        )
        cerebro.adddata(data)
        
        # Strategy params
        default_params = {}
        if 'params' in strat_info:
            for p_name, p_meta in strat_info['params'].items():
                if isinstance(p_meta, dict) and 'default' in p_meta:
                    default_params[p_name] = p_meta['default']
        
        cerebro.addstrategy(strat_class, **default_params)
        
        # Capital
        cerebro.broker.setcash(100000.0) # Increased to 100k to allow 1 BTC purchase if fixed, but using sizer now
        cerebro.broker.setcommission(commission=0.001) 
        
        # Sizing - Critical for realistic results
        cerebro.addsizer(bt.sizers.PercentSizer, percents=95)
 
        
        # Analyzers
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')

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
            
            # SQN (Built-in or estimate)
            sqn = strat_inst.analyzers.sqn.get_analysis().get('sqn', 0)
            
            sharpe_str = f"{sharpe:.2f}" if sharpe is not None else "N/A"
            
            print(f"{name:<35} | {pnl_pct:>9.2f}% | {win_rate:>7.1f}% | {total_trades:>8} | {dd:>9.2f}% | {sharpe_str:>8}")
            
            results.append({
                'name': name,
                'return': pnl_pct,
                'sharpe': sharpe if sharpe is not None else -100,
                'drawdown': dd,
                'win_rate': win_rate,
                'total_trades': total_trades,
                'sqn': sqn
            })
            
        except Exception as e:
            # print(f"Error running {name}: {e}")
            print(f"{name:<35} | {'ERROR':>10} | {'-':>8} | {'-':>8} | {'-':>10} | {'-':>8}")

    # Generate Markdown Report
    results.sort(key=lambda x: x['return'], reverse=True)
    
    report = \
"""
# 🏆 Strategy Ranking Report (Redesign Phase)
**Objective**: Identify the single best strategy for reliable, actionable signals.
**Data Source**: 2023-Present (1-Hour Timeframe)
**Account**: $10k Start | 0.1% Comm

| Rank | Strategy | Net Profit | Win Rate | Trades | Max Drawdown | Sharpe |
|---|---|---|---|---|---|---|
"""
    for i, res in enumerate(results, 1):
        sharpe_val = f"{res['sharpe']:.2f}" if res['sharpe'] != -100 else "N/A"
        
        # Highlight the winner candidate (High Return + Reasonable Drawdown + >50 Trades)
        icon = ""
        if i == 1: icon = "🥇 "
        elif i == 2: icon = "🥈 "
        elif i == 3: icon = "🥉 "
        
        # Simple heuristic for "Best"
        # Must have profitable return and not insane drawdown
        
        row = f"| {i} | {icon}**{res['name']}** | {res['return']:.2f}% | {res['win_rate']:.1f}% | {res['total_trades']} | {res['drawdown']:.2f}% | {sharpe_val} |\n"
        report += row

    with open("STRATEGY_RANKING.md", "w") as f:
        f.write(report)
        
    print("\n✅ Benchmark Complete. Report saved to STRATEGY_RANKING.md")

if __name__ == "__main__":
    run_benchmark()
