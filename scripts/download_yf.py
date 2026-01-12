
import yfinance as yf
import pandas as pd
import sys

def download_yf_data():
    print("⬇️ Attempting download from Yahoo Finance (Internet)...")
    
    # Symbol for BTC
    # YF usually uses BTC-USD
    ticker = "BTC-USD"
    
    # Period: valid periods: 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max
    # Interval: valid intervals: 1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo
    # 5m data is limited to last 60 days.
    
    print(f"   Fetching 5m data for {ticker} (Last 60 Days limit)...")
    
    try:
        # Fetch max available 5m data
        # We can't specify start/end outside of 60 days for 5m.
        # So we just request period="60d"
        df = yf.download(ticker, period="60d", interval="5m", progress=True)
        
        if len(df) == 0:
            print("❌ No data returned from Yahoo Finance.")
            return
            
        print(f"✅ Downloaded {len(df)} rows.")
        print(f"   Range: {df.index.min()} to {df.index.max()}")
        
        # Flatten columns if MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # Rename to match our standard
        # YF: Open, High, Low, Close, Volume
        df.rename(columns={
            "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"
        }, inplace=True)
        
        # Save
        filename = "BTC_YF_5m.csv"
        df.to_csv(filename)
        print(f"💾 Saved to {filename}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    download_yf_data()
