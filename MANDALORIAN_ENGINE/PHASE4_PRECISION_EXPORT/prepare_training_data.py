import pandas as pd
import os
import glob

# Correct order of months
FILES = [
    "jan2025_binance_data.csv",
    "feb2025_binance_data.csv",
    "march2025_binance_data.csv",
    "april2025_binance_data.csv",
    "may2025_binance_data.csv",
    "june2025_binance_data.csv",
    "july2025_binance_data.csv",
    "aug2025_binance_data.csv",
    "sept2025_binance_data.csv",
    "oct2025_binance_data.csv",
    "nov2025_binance_data.csv",
    "dec2025_binance_data.csv",
    "jan2026_binance_data.csv"
]

def merge_data():
    print("🚀 Merging Training Data...")
    
    master_df = pd.DataFrame()
    
    for f in FILES:
        if not os.path.exists(f):
            print(f"⚠️ Missing file: {f}")
            continue
            
        print(f"   📖 Reading {f}...")
        try:
            df = pd.read_csv(f)
            
            # Ensure timestamp is datetime
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            elif 'Datetime' in df.columns:
                 # Handle Yahoo Finance format just in case
                df.rename(columns={'Datetime': 'timestamp', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'}, inplace=True)
                df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize(None)
                
            # Standardize columns
            needed_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            df = df[needed_cols]
            
            master_df = pd.concat([master_df, df], axis=0)
            
        except Exception as e:
            print(f"   ❌ Error reading {f}: {e}")

    if len(master_df) == 0:
        print("❌ No data merged!")
        return

    print("🔧 Processing Master Dataset...")
    
    # Sort
    master_df.sort_values('timestamp', inplace=True)
    
    # Remove Duplicates
    initial_len = len(master_df)
    master_df.drop_duplicates(subset=['timestamp'], keep='first', inplace=True)
    final_len = len(master_df)
    print(f"   🧹 Removed {initial_len - final_len} duplicate rows")
    
    # Save
    output_file = "MASTER_TRAINING_DATA.csv"
    master_df.to_csv(output_file, index=False)
    
    print(f"\n✅ SUCCESS! Saved {final_len} rows to {output_file}")
    
    print("\n📊 Dataset Summary:")
    print(f"   Start: {master_df['timestamp'].iloc[0]}")
    print(f"   End:   {master_df['timestamp'].iloc[-1]}")
    print(f"   Rows:  {len(master_df)}")

if __name__ == "__main__":
    merge_data()
