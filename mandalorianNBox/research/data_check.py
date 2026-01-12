
import pandas as pd
import os

curr_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(curr_dir, '..', 'datasets')
files = [f for f in os.listdir(data_dir) if f.endswith('.csv') and 'BTC' in f]
data_file = next((f for f in files if '1h' in f), files[0])
data_path = os.path.join(data_dir, data_file)

print(f"Checking {data_path}...")
df = pd.read_csv(data_path)
df['datetime'] = pd.to_datetime(df['datetime'])
df = df.sort_values('datetime', ascending=True)

print(f"Rows: {len(df)}")
print(f"Min Price: {df['close'].min()}")
print(f"Max Price: {df['close'].max()}")
print(f"Start Date: {df['datetime'].iloc[0]}")
print(f"End Date: {df['datetime'].iloc[-1]}")
print("\nFirst 5 rows:")
print(df.head())
print("\nLast 5 rows:")
print(df.tail())
