"""
Strategy Deployer - Deploy backtested strategies to live trading
"""

import os
import sys
import json
from datetime import datetime

# Add parent directory to path to import bot functions
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

def create_live_bot(strategy_name, strategy_params, symbol, size, target, max_loss):
    """
    Create a live trading bot from a strategy
    
    This generates a bot file that can be run live
    """
    
    bot_template = f'''"""
Live Trading Bot - {strategy_name}
Deployed from dashboard backtest results
Generated: {datetime.now().isoformat()}
"""

import dontshare as d 
import nice_funcs as n 
from eth_account.signers.local import LocalAccount
import eth_account 
import time 
from hyperliquid.info import Info 
from hyperliquid.exchange import Exchange 
from hyperliquid.utils import constants 
import schedule 
import requests 

# Dashboard integration
DASHBOARD_URL = "http://127.0.0.1:5000"

def send_to_dashboard(log_type, symbol, price=None, size=None, message=""):
    try:
        requests.post(
            f"{{DASHBOARD_URL}}/api/add-log",
            json={{'type': log_type, 'symbol': symbol, 'price': price, 'size': size, 'message': message}},
            timeout=1
        )
    except:
        pass

# Strategy parameters
STRATEGY_PARAMS = {json.dumps(strategy_params, indent=4)}

symbol = '{symbol}'
size = {size}
target = {target}
max_loss = {max_loss}
leverage = 3
max_positions = 1 

secret = d.private_key

def bot():
    account1 = LocalAccount = eth_account.Account.from_key(secret)
    
    # Get position info
    positions1, im_in_pos, mypos_size, pos_sym1, entry_px1, pnl_perc1, long1, num_of_pos = n.get_position_andmaxpos(symbol, account1, max_positions)
    
    send_to_dashboard('INFO', symbol, message=f'Checking position: {{im_in_pos}}')
    
    # Get current price
    ask, bid, l2_data = n.ask_bid(symbol)
    send_to_dashboard('INFO', symbol, price=float(ask), message=f'Price: ${{ask}}')
    
    # TODO: Implement {strategy_name} logic here
    # This is where your strategy logic goes based on the backtest
    
    if im_in_pos:
        n.cancel_all_orders(account1)
        n.pnl_close(symbol, target, max_loss, account1)
        send_to_dashboard('INFO', symbol, message=f'Checking PnL: {{pnl_perc1:.2f}}%')
    else:
        # Strategy entry logic here
        # Example: Check indicators and enter if conditions met
        pass

send_to_dashboard('INFO', symbol, message='Live bot started - {strategy_name}')
bot()
schedule.every(30).seconds.do(bot)

while True:
    try:
        schedule.run_pending()
        time.sleep(10)
    except Exception as e:
        send_to_dashboard('ERROR', symbol, message=f'Error: {{str(e)}}')
        time.sleep(30)
'''
    
    # Save bot file
    bot_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'live_bots')
    os.makedirs(bot_dir, exist_ok=True)
    
    bot_filename = f"live_{strategy_name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
    bot_path = os.path.join(bot_dir, bot_filename)
    
    with open(bot_path, 'w') as f:
        f.write(bot_template)
    
    return bot_path

