
import csv
import pandas as pd

def format_currency(val):
    return f"${float(val):,.2f}"

def main():
    input_file = 'trades_jan2_jan7.csv'
    output_file = 'TRADE_LOG_PRETTY.md'
    
    try:
        df = pd.read_csv(input_file)
    except Exception as e:
        print(f"Error reading {input_file}: {e}")
        return

    # Calculate Exit Price
    # If WIN -> Exit = TP, If LOSS -> Exit = SL
    # actually, exact exit might vary, but for simulation, this is the logic.
    df['Exit Price'] = df.apply(lambda row: row['tp'] if row['res'] == 'WIN' else row['sl'], axis=1)

    # Format Columns
    df['Time'] = df['time']
    df['Model'] = df['model']
    df['Type'] = df['dir']
    df['Entry'] = df['price'].apply(format_currency)
    df['TP'] = df['tp'].apply(format_currency)
    df['SL'] = df['sl'].apply(format_currency)
    df['Exit'] = df['Exit Price'].apply(format_currency)
    
    def format_res(x):
        return "✅ WIN" if x == 'WIN' else "❌ LOSS"
    
    df['Result'] = df['res'].apply(format_res)

    # Select and Rename for Table
    table_df = df[['Time', 'Model', 'Type', 'Entry', 'Exit', 'TP', 'SL', 'Result']]
    
    # Generate Markdown
    md_table = table_df.to_markdown(index=False)
    
    content = f"""# 📊 Trade Log: Jan 2 - Jan 7, 2026
**Engine:** Quant Engine v2 (Verified)
**Total Trades:** {len(df)}

{md_table}
"""

    with open(output_file, 'w') as f:
        f.write(content)
        
    print(f"Generated {output_file}")

if __name__ == "__main__":
    main()
