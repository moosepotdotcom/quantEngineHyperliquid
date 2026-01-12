
from hyperliquid_live_trader import HyperliquidTrader
from dotenv import load_dotenv
import time

load_dotenv()

print("🚨 EMERGENCY CLOSE: Flattening BTC Position")
trader = HyperliquidTrader(testnet=False)

# Check position
info = trader.get_account_info()
positions = info.get('positions', [])
btc_pos_size = 0

for p in positions:
    if p['position']['coin'] == 'BTC':
        btc_pos_size = float(p['position']['szi'])
        break

print(f"Current BTC Size: {btc_pos_size}")

if btc_pos_size != 0:
    print(f"Flattening {btc_pos_size}...")
    is_buy = (btc_pos_size < 0) # Buy to close short, Sell to close long
    
    res = trader.place_market_order('BTC', is_buy, abs(btc_pos_size))
    print(f"Result: {res}")
else:
    print("✅ No open position found.")
