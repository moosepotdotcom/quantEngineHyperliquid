'''
Bollinger band bot WITH Dashboard Integration
Connects to HyperLiquid and sends real-time data to dashboard
'''

import dontshare as d 
import nice_funcs as n 
from eth_account.signers.local import LocalAccount
import eth_account 
import json 
import time 
from hyperliquid.info import Info 
from hyperliquid.exchange import Exchange 
from hyperliquid.utils import constants 
import ccxt 
import pandas as pd 
import datetime 
import schedule 
import requests 

# Dashboard integration
DASHBOARD_URL = "http://127.0.0.1:5000"

def send_to_dashboard(log_type, symbol, price=None, size=None, message=""):
    """Send data to dashboard"""
    try:
        requests.post(
            f"{DASHBOARD_URL}/api/add-log",
            json={
                'type': log_type,
                'symbol': symbol,
                'price': price,
                'size': size,
                'message': message
            },
            timeout=1
        )
    except:
        pass  # Dashboard might not be running

def send_liquidation(symbol, side, amount):
    """Send liquidation to dashboard"""
    try:
        requests.post(
            f"{DASHBOARD_URL}/api/add-liquidation",
            json={'symbol': symbol, 'side': side, 'amount': amount},
            timeout=1
        )
    except:
        pass

def send_price_update(symbol, price):
    """Send price update to dashboard"""
    try:
        requests.post(
            f"{DASHBOARD_URL}/api/update-price",
            json={'symbol': symbol, 'price': price, 'change': 0},
            timeout=1
        )
    except:
        pass

symbol = 'WIF'
timeframe = '15m'
sma_window = 20
lookback_days = 1 
size = 1 
target = 5
max_loss = -10
leverage = 3
max_positions = 1 

secret = d.private_key

def bot():

    account1 = LocalAccount = eth_account.Account.from_key(secret)

    positions1, im_in_pos, mypos_size, pos_sym1, entry_px1, pnl_perc1, long1, num_of_pos = n.get_position_andmaxpos(symbol, account1, max_positions)

    # SEND POSITION INFO TO DASHBOARD
    if im_in_pos:
        send_to_dashboard('INFO', symbol, price=entry_px1, size=mypos_size, 
                         message=f'Position: {mypos_size} @ ${entry_px1} | PnL: {pnl_perc1:.2f}%')
    else:
        send_to_dashboard('INFO', symbol, message='No position')

    print(f'these are positions for {symbol} {positions1}')

    lev, pos_size = n.adjust_leverage_size_signal(symbol, leverage, account1)

    # dividing position by 2 
    pos_size = pos_size / 2 

    if im_in_pos:
        n.cancel_all_orders(account1)
        print('in position so check pnl close')
        n.pnl_close(symbol, target, max_loss, account1)
        send_to_dashboard('INFO', symbol, message=f'Checking PnL close: Target {target}% | Max Loss {max_loss}%')
    else:
        print('not in position so no pnl close')

    # get price FROM HYPERLIQUID
    ask, bid, l2_data = n.ask_bid(symbol)

    # SEND REAL PRICE TO DASHBOARD
    send_price_update(symbol, float(ask))
    send_to_dashboard('INFO', symbol, price=float(ask), message=f'Price update: Ask ${ask} | Bid ${bid}')

    print(f'ask: {ask} bid: {bid}')

    bid11 = float(l2_data[0][10]['px'])
    ask11 = float(l2_data[1][10]['px'])

    print(f'ask11: {ask11} bid11: {bid11}')

    snapshot_data = n.get_ohlcv2('BTC', '1m', 500)
    df = n.process_data_to_df(snapshot_data)
    bbdf = n.calculate_bollinger_bands(df)
    bollinger_bands_tight = n.calculate_bollinger_bands(df)[1]

    print(f'bollinger bands are tight: {bollinger_bands_tight}')

    # ONLY ENTERS IF BOLLINGER BANDS ARE TIGHT
    if not im_in_pos and bollinger_bands_tight:
        print('bollinger bands are tight and we dont have a position so entering')
        print(f'not in position we are quoteing a sell @ {ask} and buy @ {bid}')
        
        # SEND TO DASHBOARD
        send_to_dashboard('INFO', symbol, message='Bollinger bands tight - Entering position')
        
        # cancel all open orser
        n.cancel_all_orders(account1)

        print('just canceled all orders')

        # ENTER BUY ORDER ON HYPERLIQUID
        n.limit_order(symbol, True, pos_size, bid11, False, account1)
        print(f'just placed an order for {pos_size} at {bid}')
        
        # SEND BUY ORDER TO DASHBOARD
        send_to_dashboard('BUY', symbol, price=float(bid11), size=pos_size)

        # ENTER SELL ORDER ON HYPERLIQUID
        n.limit_order(symbol, False, pos_size, ask11, False, account1)
        print(f'just placed an order for {pos_size} as {ask}')
        
        # SEND SELL ORDER TO DASHBOARD
        send_to_dashboard('SELL', symbol, price=float(ask11), size=pos_size)

    elif bollinger_bands_tight == False:
        n.cancel_all_orders(account1)
        n.close_all_positions(account1)
        send_to_dashboard('INFO', symbol, message='Bollinger bands not tight - Closing positions')
    else:
        print(f'our position is {im_in_pos} bollinger bands may not be tight')

# Send startup message
send_to_dashboard('INFO', symbol, message='Bot started - Connecting to HyperLiquid...')

bot()
schedule.every(30).seconds.do(bot)

while True:
    try:
        schedule.run_pending()
        time.sleep(10)
    except Exception as e:
        send_to_dashboard('ERROR', symbol, message=f'Error: {str(e)}')
        print('*** maybe internet connection lost... sleeping 30 and retrying')
        print(e)
        time.sleep(30)

