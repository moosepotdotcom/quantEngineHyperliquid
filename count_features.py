
import sys
import os

# Mock dependencies to load quant_engine.py partially
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'utils')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'monitoring')))

with open('/Users/alifiyaa/Downloads/quantEngineHyperliquid/quant_engine.py', 'r') as f:
    lines = f.readlines()

list_start = -1
list_end = -1
for i, line in enumerate(lines):
    if 'MTF_FEATURE_LIST = [' in line:
        list_start = i
    if list_start != -1 and ']' in line:
        list_end = i
        break

if list_start != -1 and list_end != -1:
    list_str = "".join(lines[list_start:list_end+1])
    list_str = list_str.split('=')[1].strip()
    # Evaluate the list
    import ast
    features = ast.literal_eval(list_str)
    print(f"Total features: {len(features)}")
    
    # Analyze by timeframe
    f5m = [f for f in features if not f.endswith('_15m') and not f.endswith('_1h') and f not in ['hurst', 'atr', 'atr_ratio', 'wick_ratio_upper', 'wick_ratio_lower', 'rsi', 'rsi_slope', 'price_slope']]
    f15m = [f for f in features if f.endswith('_15m')]
    f1h = [f for f in features if f.endswith('_1h')]
    extra = [f for f in features if f in ['hurst', 'atr', 'atr_ratio', 'wick_ratio_upper', 'wick_ratio_lower', 'rsi', 'rsi_slope', 'price_slope']]
    
    print(f"5m features: {len(f5m)}")
    print(f"15m features: {len(f15m)}")
    print(f"1h/30m features: {len(f1h)}")
    print(f"Global features: {len(extra)}")
else:
    print("Could not find MTF_FEATURE_LIST")
