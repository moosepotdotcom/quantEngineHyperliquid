import pandas as pd
import os
import re
from datetime import datetime

def check_timestamp_overlap():
    print("🔍 1. TIMESTAMP INTEGRITY CHECK")
    print("-" * 30)
    
    # 1. Load Training Data Max Timestamp
    train_path = 'training/data/BTC_5m_mtf_labeled.csv'
    if not os.path.exists(train_path):
        print("❌ Training data not found!")
        return
    
    # Read only timestamp column to be fast
    df_train = pd.read_csv(train_path, usecols=['timestamp'])
    df_train['timestamp'] = pd.to_datetime(df_train['timestamp'])
    last_train_ts = df_train['timestamp'].max()
    print(f"   📅 Last Training Data Point:   {last_train_ts}")
    
    # 2. Parsing Trades Log for First Simulation Timestamp
    trade_log_path = 'ULTIMATE_TRADES.md'
    if not os.path.exists(trade_log_path):
        print("❌ Trade log not found!")
        return
        
    first_trade_ts = None
    with open(trade_log_path, 'r') as f:
        for line in f:
            # Look for lines starting with date like | 2026-01-02
            match = re.search(r"\|\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2})", line)
            if match:
                first_trade_ts = pd.to_datetime(match.group(1))
                break
    
    if first_trade_ts:
        print(f"   🚀 First Simulated Trade:      {first_trade_ts}")
        
        gap = first_trade_ts - last_train_ts
        print(f"   ⏱️  Gap Duration:              {gap}")
        
        if gap.total_seconds() > 0:
            print("   ✅ RESULT: POSITIVE GAP. No overlap detected.")
        else:
            print("   ❌ RESULT: NEGATIVE GAP! Overlap detected.")
    else:
        print("   ⚠️ Could not parse first trade timestamp.")

def check_feature_code_peeking():
    print("\n🔍 2. CODE 'PEEKING' AUDIT")
    print("-" * 30)
    
    files_to_check = ['utils/feature_engineer.py', 'utils/advanced_features.py']
    suspicious_patterns = ['shift(-', 'shift( -', 'future', 'lead(']
    
    for filepath in files_to_check:
        if not os.path.exists(filepath):
            continue
            
        print(f"   Checking {filepath}...")
        found_suspicious = False
        with open(filepath, 'r') as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                for pattern in suspicious_patterns:
                    if pattern in line and '#' not in line: # Ignore comments
                        print(f"      ⚠️  Suspicious pattern '{pattern}' found on line {i+1}:")
                        print(f"          {line.strip()}")
                        found_suspicious = True
        
        if not found_suspicious:
            print("      ✅ Clean. No forward-looking shifts found.")

if __name__ == "__main__":
    check_timestamp_overlap()
    check_feature_code_peeking()
