"""
Backtesting Engine - Run strategies and get results
"""

import backtrader as bt
import backtrader.analyzers as btanalyzers
import os
from datetime import datetime
from strategies_complete import STRATEGIES

def run_backtest(strategy_name, params, data_file, start_date, end_date, initial_cash=10000, commission=0.001):
    """
    Run a backtest for a strategy
    
    Returns:
        dict with results
    """
    # Get strategy class
    if strategy_name not in STRATEGIES:
        return {'error': f'Strategy {strategy_name} not found'}
    
    strategy_class = STRATEGIES[strategy_name]['class']
    
    # Create cerebro
    cerebro = bt.Cerebro()
    
    # Add strategy with params
    cerebro.addstrategy(strategy_class, **params)
    
    # Load data - check multiple locations
    base_dir = os.path.dirname(os.path.dirname(__file__))
    
    # Try datasets folder first
    data_path = os.path.join(base_dir, 'datasets', data_file)
    
    # If not found, try Open-AI-Assistants folder
    if not os.path.exists(data_path):
        ai_folder = os.path.join(base_dir, 'Open-AI-Assistants for Bootcamp Members Only', data_file)
        if os.path.exists(ai_folder):
            data_path = ai_folder
        else:
            return {'error': f'Data file {data_file} not found in datasets/ or Open-AI-Assistants folder'}
    
    # Try to load data - handle different CSV formats
    try:
        # First try YahooFinance format (datasets folder)
        data = bt.feeds.YahooFinanceCSVData(
            dataname=data_path,
            fromdate=datetime.strptime(start_date, '%Y-%m-%d'),
            todate=datetime.strptime(end_date, '%Y-%m-%d'),
            reverse=False
        )
    except:
        # If that fails, try generic CSV format (Open-AI-Assistants folder)
        try:
            import pandas as pd
            df = pd.read_csv(data_path)
            
            # Handle different column name formats
            if 'datetime' in df.columns:
                df['datetime'] = pd.to_datetime(df['datetime'])
                df.set_index('datetime', inplace=True)
            elif 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
            
            # Normalize column names to lowercase
            df.columns = df.columns.str.lower()
            
            # Ensure we have required columns
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            if all(col in df.columns for col in required_cols):
                # Filter by date range
                df = df[(df.index >= pd.to_datetime(start_date)) & (df.index <= pd.to_datetime(end_date))]
                
                # Create backtrader data feed
                data = bt.feeds.PandasData(
                    dataname=df,
                    datetime=None,  # Use index
                    open='open',
                    high='high',
                    low='low',
                    close='close',
                    volume='volume',
                    openinterest=-1
                )
            else:
                return {'error': f'CSV file missing required columns. Found: {list(df.columns)}'}
        except Exception as e:
            return {'error': f'Error loading data file: {str(e)}'}
    
    # Set broker
    cerebro.broker.set_cash(initial_cash)
    cerebro.broker.setcommission(commission=commission)
    cerebro.adddata(data)
    cerebro.addsizer(bt.sizers.PercentSizer, percents=20)
    
    # Add analyzers
    cerebro.addanalyzer(btanalyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(btanalyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(btanalyzers.Returns, _name='returns')
    cerebro.addanalyzer(btanalyzers.DrawDown, _name='drawdown')
    
    # Run backtest
    try:
        results = cerebro.run()
        strategy_result = results[0]
        
        # Get results
        end_value = cerebro.broker.getvalue()
        profit = end_value - initial_cash
        profit_pct = (profit / initial_cash) * 100
        
        sharpe = strategy_result.analyzers.sharpe.get_analysis()
        trades = strategy_result.analyzers.trades.get_analysis()
        returns = strategy_result.analyzers.returns.get_analysis()
        drawdown = strategy_result.analyzers.drawdown.get_analysis()
        
        # Format results
        result = {
            'strategy': strategy_name,
            'params': params,
            'start_cash': initial_cash,
            'end_cash': end_value,
            'profit': profit,
            'profit_pct': profit_pct,
            'total_trades': trades.get('total', {}).get('total', 0) if trades else 0,
            'won': trades.get('won', {}).get('total', 0) if trades else 0,
            'lost': trades.get('lost', {}).get('total', 0) if trades else 0,
            'win_rate': 0,
            'sharpe_ratio': sharpe.get('sharperatio', 0) if sharpe else 0,
            'max_drawdown': drawdown.get('max', {}).get('drawdown', 0) if drawdown else 0,
            'total_return': returns.get('rtot', 0) if returns else 0,
        }
        
        # Calculate win rate
        if result['total_trades'] > 0:
            result['win_rate'] = (result['won'] / result['total_trades']) * 100
        
        return result
        
    except Exception as e:
        return {'error': str(e)}

