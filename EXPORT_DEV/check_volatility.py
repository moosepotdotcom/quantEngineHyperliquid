
import requests
import pandas as pd
import numpy as np
from datetime import datetime

def get_volatility():
    url = "https://api.hyperliquid.xyz/info"
    headers = {"Content-Type": "application/json"}
    
    # Fetch last 30 minutes of 1m data
    body = {
        "type": "candleSnapshot",
        "req": {
            "coin": "BTC",
            "interval": "1m",
            "startTime": int((datetime.now().timestamp() - 1800) * 1000) 
        }
    }
    
    try:
        response = requests.post(url, json=body, headers=headers)
        data = response.json()
        
        if not data:
            print("No data returned")
            return

        df = pd.DataFrame(data)
        df['c'] = df['c'].astype(float) # Close
        df['h'] = df['h'].astype(float) # High
        df['l'] = df['l'].astype(float) # Low
        df['t'] = pd.to_datetime(df['t'], unit='ms')
        
        # Calculate volatility (High - Low)
        df['range'] = df['h'] - df['l']
        df['range_pct'] = (df['range'] / df['c']) * 100
        
        print(f"\n--- BTC Volatility Report (Last {len(df)} mins) ---")
        print(f"Current Price: ${df['c'].iloc[-1]:,.2f}")
        print(f"Average Range (1m): ${df['range'].mean():.2f} ({df['range_pct'].mean():.3f}%)")
        print(f"Max Range (1m): ${df['range'].max():.2f} at {df.loc[df['range'].idxmax()]['t'].strftime('%H:%M:%S')}")
        
        # Recent 5 min trend
        recent = df.tail(5)
        print("\n--- Last 5 Minutes ---")
        for i, row in recent.iterrows():
            print(f"{row['t'].strftime('%H:%M:%S')} | Open: {row['o']} | Close: {row['c']} | Range: ${row['range']:.1f}")
            
        # Interpretation
        avg_range = df['range'].mean()
        if avg_range > 50:
            print("\nVERDICT: YES, HIGH VOLATILITY. Candles are large.")
        elif avg_range > 20:
            print("\nVERDICT: MODERATE. Normal movement.")
        else:
            print("\nVERDICT: NO. Very low volatility (chop).")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_volatility()
