
import ccxt
import pandas as pd
import os
import time

def fetch_deep_history(amount=5000):
    print(f"⬇️ Fetching {amount} bars of BTC/USDT 15m data...")
    exchange = ccxt.binance()
    symbol = 'BTC/USDT'
    timeframe = '15m'
    
    # Binance max limit is 1000
    # We need to fetch in chunks backwards? or forwards.
    # Easiest: Determine start time.
    # 15m * 5000 = 75000 mins ~ 52 days.
    
    since = exchange.milliseconds() - (amount * 15 * 60 * 1000)
    
    all_ohlcv = []
    
    while len(all_ohlcv) < amount:
        limit = min(1000, amount - len(all_ohlcv))
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
            if not ohlcv:
                break
            
            # Check if we got new data
            if len(all_ohlcv) > 0 and ohlcv[0][0] == all_ohlcv[-1][0]:
                 # Duplicate start
                 ohlcv = ohlcv[1:]
                 
            all_ohlcv.extend(ohlcv)
            
            # Update since to last timestamp + 1 timeframe (15m in ms)
            since = ohlcv[-1][0] + (15 * 60 * 1000)
            
            print(f"   Fetched {len(all_ohlcv)}...")
            time.sleep(0.5)
            
        except Exception as e:
            print(f"⚠️ Error: {e}")
            break

    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    
    # Save
    path = os.path.join(os.path.dirname(__file__), '..', 'data', f'BTC_15m.csv')
    df.to_csv(path)
    print(f"✅ Deep Data saved to {path} ({len(df)} rows)")

if __name__ == "__main__":
    fetch_deep_history(6000) # Fetch 6000 to be safe
