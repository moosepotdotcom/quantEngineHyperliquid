import sys
import os
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import log_trade

print("🧪 Testing Trade Logging...")

# Simulate a trade with SL/TP
log_trade(
    symbol="BTC/USD",
    action="BUY (Test)",
    price=95000.0,
    size=0.1,
    reason="Manual Test | SL: $94000 | TP: $97000",
    sl=94000.0,
    tp=97000.0,
    engine="TestEngine"
)

# Check if JSON file exists
trades_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'trades.json')

if os.path.exists(trades_file):
    print(f"✅ Trades file created at: {trades_file}")
    with open(trades_file, 'r') as f:
        data = json.load(f)
        last_trade = data[-1]
        print(f"📄 Last Trade Data: {json.dumps(last_trade, indent=2)}")
        
        if last_trade['sl'] == 94000.0 and last_trade['tp'] == 97000.0:
            print("✅ SL/TP values correctly logged!")
        else:
            print("❌ SL/TP values mismatch!")
else:
    print("❌ Trades file NOT found!")
