
import ccxt
import pandas as pd
import os
import time

def fetch_data():
    print("⬇️ Fetching BTC/USDT data via CCXT (Binance)...")
    exchange = ccxt.binance()
    symbol = 'BTC/USDT'
    timeframe = '1h'
    # Fetch last ~90 days
    limit = 1000
    
    # Get recent data
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    except Exception as e:
        print(f"⚠️ Error: {e}")
        return

    if not ohlcv:
        print("❌ No data fetched")
        return
        
    # Convert to DataFrame
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    
    # Save
    path = os.path.join(os.path.dirname(__file__), '..', 'data', 'BTC_1h.csv')
    df.to_csv(path)
    print(f"✅ Data saved to {path} ({len(df)} rows)")

if __name__ == "__main__":
    fetch_data()
