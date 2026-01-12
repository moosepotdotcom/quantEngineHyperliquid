
import yfinance as yf
import pandas as pd
import os

def fetch_15m_data():
    symbol = "BTC-USD"
    print(f"📥 Fetching 15m data for {symbol}...")
    
    # YFinance 15m data limit is usually 60 days
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="60d", interval="15m")
    
    if df.empty:
        print("⚠️ No data fetched. API might be limited.")
        return

    # Clean
    df = df.reset_index()
    df.columns = [c.lower() for c in df.columns]
    if 'date' in df.columns:
        df.rename(columns={'date': 'datetime'}, inplace=True)
    elif 'datetime' in df.columns:
        pass # Good
        
    # Ensure TZ-naive for Backtrader compatibility usually, but let's keep it clean
    # df['datetime'] = df['datetime'].dt.tz_localize(None)

    save_path = "datasets/BTCUSD-15m-max-data.csv"
    
    # Create dir if needed
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    df.to_csv(save_path, index=False)
    print(f"✅ Saved {len(df)} 15m candles to {save_path}")
    print(df.tail())

if __name__ == "__main__":
    fetch_15m_data()
