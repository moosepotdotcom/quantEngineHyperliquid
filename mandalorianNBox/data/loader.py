import yfinance as yf
try:
    import ccxt
except ImportError:
    ccxt = None

import pandas as pd
import time
import requests
import functools

class DataLoader:
    """
    Centralized Data Fetching Layer.
    Supports YFinance (Free, easy) and CCXT (Exchange direct).
    """
    
    @staticmethod
    def fetch_yfinance(symbol: str, period: str = '1y', interval: str = '1h', quiet: bool = False):
        """
        Fetch data from Yahoo Finance.
        """
        if not quiet:
            print(f"📥 Fetching {symbol} via YFinance...", end='\r')
        
        # Retry mechanism for YFinance
        max_retries = 3
        backoff = 2
        
        for attempt in range(max_retries):
            try:
                # Fetch data using Ticker (Standard)
                ticker = yf.Ticker(symbol)
                df = ticker.history(period=period, interval=interval, auto_adjust=True)
                
                if df.empty:
                    if attempt < max_retries - 1:
                        time.sleep(backoff)
                        backoff *= 2
                        continue
                    raise ValueError(f"No data found for {symbol}")
                
                 # Normalize columns (Lower case, remove MultiIndex if present)
                if isinstance(df.columns, pd.MultiIndex):
                     try:
                         df.columns = df.columns.droplevel(1)
                     except IndexError:
                         pass
                
                df.columns = [c.lower() for c in df.columns]
                
                # YFinance returns 'Adj Close', we usually want 'Close'
                if 'adj close' in df.columns:
                    df = df.rename(columns={'adj close': 'adj_close'})
                    
                return df
                
            except Exception as e:
                print(f"⚠️ YFinance attempt {attempt+1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    raise e

    @staticmethod
    def fetch_ccxt(exchange_id: str, symbol: str, timeframe: str = '1h', limit: int = 1000):
        """
        Fetch data from Crypto Exchanges via CCXT.
        Args:
            exchange_id (str): 'binance', 'bybit', 'coinbase'
            symbol (str): 'BTC/USDT'
            timeframe (str): '1m', '5m', '1h', '1d'
        """
        try:
            exchange_class = getattr(ccxt, exchange_id)
            exchange = exchange_class()
        except AttributeError:
            raise ValueError(f"Exchange {exchange_id} not found in CCXT")
            
        print(f"📥 Fetching {symbol} via CCXT ({exchange_id})...")
        
        # Fetch OHLCV
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        # Convert to DataFrame
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('datetime', inplace=True)
        # Drop raw timestamp
        df.drop('timestamp', axis=1, inplace=True)
        
        return df

if __name__ == "__main__":
    # Test
    try:
        data = DataLoader.fetch_yfinance("BTC-USD", period="1mo", interval="1h")
        print(data.tail())
    except Exception as e:
        print(e)
