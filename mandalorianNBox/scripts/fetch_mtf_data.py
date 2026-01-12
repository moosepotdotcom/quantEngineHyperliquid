
import ccxt
import pandas as pd
import os
import time

def fetch_data(timeframe, limit=1000):
    print(f"⬇️ Fetching BTC/USDT {timeframe} data via CCXT...")
    exchange = ccxt.binance()
    symbol = 'BTC/USDT'
    
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    except Exception as e:
        print(f"⚠️ Error: {e}")
        return

    if not ohlcv:
        print(f"❌ No data fetched for {timeframe}")
        return
        
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    
    # Save
    path = os.path.join(os.path.dirname(__file__), '..', 'data', f'BTC_{timeframe}.csv')
    df.to_csv(path)
    print(f"✅ Data saved to {path} ({len(df)} rows)")

if __name__ == "__main__":
    fetch_data('15m')
    fetch_data('1h')
    fetch_data('4h')
