import time
import json
import os
import sys
import requests
import pandas as pd
from datetime import datetime

# Import collectors for API access (Assuming these exist and work based on previous steps)
# In a real deployment, we would import the authenticated client. 
# For this artifact, we will implement the Logic Loop that *would* call the API.

# CONFIG
SYMBOL = 'BTC'
LEVERAGE = 50
SIZE_USD = 1000  # Target size
MAX_CHASE_SEC = 60 # How long to chase before giving up
REBATE = 0.0001 # 0.01%

class MakerStrategy:
    def __init__(self):
        self.position = None
        self.active_order = None
        self.api_url = "https://api.hyperliquid.xyz/info"
        self.wallet = "0x..." # Placeholder
        
    def get_market_data(self):
        # Fetch L2 Data
        try:
            r = requests.post(self.api_url, json={'type': 'l2Book', 'coin': SYMBOL}, timeout=5)
            data = r.json()
            levels = data['levels']
            return {
                'bid': float(levels[0][0]['px']),
                'ask': float(levels[1][0]['px']),
                'bid_sz': float(levels[0][0]['sz']),
                'ask_sz': float(levels[1][0]['sz'])
            }
        except:
            return None

    def get_imbalance(self):
        # Calculate Signal
        try:
            r = requests.post(self.api_url, json={'type': 'l2Book', 'coin': SYMBOL}, timeout=5)
            data = r.json()
            bids = data['levels'][0][:10]
            asks = data['levels'][1][:10]
            bid_vol = sum([float(x['sz']) for x in bids])
            ask_vol = sum([float(x['sz']) for x in asks])
            return (bid_vol - ask_vol) / (bid_vol + ask_vol)
        except:
            return 0

    def run(self):
        print(f"🤖 MAKER STRATEGY ENGAGED [{SYMBOL}]")
        print("   Mode: Post-Only (Rebate Farming)")
        
        while True:
            # 1. Get Data
            data = self.get_market_data()
            if not data: 
                time.sleep(1)
                continue
                
            imb = self.get_imbalance()
            print(f"\rPrice: {data['bid']}/{data['ask']} | Imb: {imb:+.3f} | Pos: {self.position}", end="")
            
            # 2. Manage Active Order (Chase Logic)
            if self.active_order:
                # Check if filled
                # is_filled = check_order_status(self.active_order['oid'])
                # Simulated Fill Logic for this script:
                is_filled = False 
                if self.active_order['side'] == 'BUY' and data['ask'] <= self.active_order['price']:
                    is_filled = True
                elif self.active_order['side'] == 'SELL' and data['bid'] >= self.active_order['price']:
                    is_filled = True
                    
                if is_filled:
                    print(f"\n✅ ORDER FILLED @ {self.active_order['price']}")
                    if self.active_order['type'] == 'ENTRY':
                        self.position = {
                            'side': self.active_order['side'], 
                            'price': self.active_order['price'],
                            'size': SIZE_USD
                        }
                    else:
                        print(f"💰 TRADE CLOSED. PnL captured with REBATES.")
                        self.position = None
                    self.active_order = None
                    continue
                
                # Chase Logic (Update Price)
                # If we are buying and Best Bid moved UP, we need to move up to stay at front
                if self.active_order['side'] == 'BUY' and data['bid'] > self.active_order['price']:
                    # cancel_order(...)
                    # place_order(...)
                    self.active_order['price'] = data['bid']
                    # print(f"\n⚠️ CHASING: Moved Bid to {data['bid']}")
                    
                # If we are selling and Best Ask moved DOWN
                if self.active_order['side'] == 'SELL' and data['ask'] < self.active_order['price']:
                    self.active_order['price'] = data['ask']
                    # print(f"\n⚠️ CHASING: Moved Ask to {data['ask']}")

            # 3. Entry Logic
            if not self.position and not self.active_order:
                # LONG Signal
                if imb > 0.4:
                    print(f"\n🟢 SIGNAL: BUY (Imb {imb:.2f})")
                    # Place Limit Buy at Best Bid
                    price = data['bid']
                    self.active_order = {'side': 'BUY', 'price': price, 'type': 'ENTRY'}
                    print(f"   Posting Limit Buy @ {price}")
                    
                # SHORT Signal
                elif imb < -0.4:
                    print(f"\n🔴 SIGNAL: SELL (Imb {imb:.2f})")
                    # Place Limit Sell at Best Ask
                    price = data['ask']
                    self.active_order = {'side': 'SELL', 'price': price, 'type': 'ENTRY'}
                    print(f"   Posting Limit Sell @ {price}")

            # 4. Exit Logic
            if self.position and not self.active_order:
                # Dynamic Exit or Profit Target
                pnl = 0
                if self.position['side'] == 'BUY':
                    pnl = (data['bid'] - self.position['price']) / self.position['price']
                    # Exit if Imbalance drops or Target hit
                    if imb < 0 or pnl > 0.01: 
                        print(f"\n🔻 EXIT TRIGGER (PnL {pnl*100:.2f}%)")
                        price = data['ask'] # Try to sell at Ask (Maker)
                        self.active_order = {'side': 'SELL', 'price': price, 'type': 'EXIT'}
                        print(f"   Posting Limit Sell @ {price}")
                        
                elif self.position['side'] == 'SELL':
                    pnl = (self.position['price'] - data['ask']) / self.position['price']
                    if imb > 0 or pnl > 0.01:
                        print(f"\n🔺 EXIT TRIGGER (PnL {pnl*100:.2f}%)")
                        price = data['bid'] # Try to buy at Bid (Maker)
                        self.active_order = {'side': 'BUY', 'price': price, 'type': 'EXIT'}
                        print(f"   Posting Limit Buy @ {price}")

            time.sleep(0.5)

if __name__ == "__main__":
    bot = MakerStrategy()
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\nStopping...")
