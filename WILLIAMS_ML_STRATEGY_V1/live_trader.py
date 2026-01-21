
import os
import time
import pandas as pd
import numpy as np
import xgboost as xgb
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()

# --- CONFIG ---
# Hyperliquid Info
API_URL = "https://api.hyperliquid.xyz" # Mainnet
WALLET_ADDRESS = os.getenv('HYPERLIQUID_WALLET_ADDRESS')
PRIVATE_KEY = os.getenv('HYPERLIQUID_API_SECRET')

# Strategy Config (V1 Sanity)
PERIOD = 21
TP_PCT = 0.007
SL_PCT = 0.015
CONF_THRESH = 0.65
FEE_PCT = 0.00035

# Risk Management ($53 Account)
# Max Risk per trade = 2% of $53 = $1.06
# SL is 1.5%. Size = $1.06 / 0.015 = ~$70 USD.
# Leverage = $70 / $53 = ~1.3x.
# Let's be aggressive but safe: Max 3x leverage ($150 USD size).
LEVERAGE = 3 
MAX_POSITION_SIZE_USD = 150.0 

# Active Positions Tracker
active_positions = {}

def get_price(coin):
    url = "https://api.hyperliquid.xyz/info"
    payload = {"type": "metaAndAssetCtxs"}
    try:
        resp = requests.post(url, json=payload, timeout=5)
        data = resp.json()
        for asset in data[1]:
            if asset['coin'] == coin:
                return float(asset['ctx']['midPx'])
    except Exception as e:
        print(f"❌ Error fetching price: {e}")
    return 0.0

def fetch_candles(coin):
    end_ts = int(time.time() * 1000)
    start_ts = end_ts - (1000 * 5 * 60 * 300) # Last 300 candles (5m)
    
    url = "https://api.hyperliquid.xyz/info"
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": coin,
            "interval": "5m",
            "startTime": start_ts,
            "endTime": end_ts
        }
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=5)
        data = resp.json()
        if not data: return pd.DataFrame()
        
        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
        df['open'] = df['o'].astype(float)
        df['high'] = df['h'].astype(float)
        df['low'] = df['l'].astype(float)
        df['close'] = df['c'].astype(float)
        df['volume'] = df['v'].astype(float)
        df.sort_values('timestamp', inplace=True)
        return df
    except Exception as e:
        print(f"❌ Error fetching candles: {e}")
        return pd.DataFrame()

def add_features(df):
    df = df.copy()
    high = df['high'].rolling(PERIOD).max()
    low = df['low'].rolling(PERIOD).min()
    denom = (high - low).replace(0, np.nan)
    df['williams_r'] = -100 * (high - df['close']) / denom
    df['williams_r_prev'] = df['williams_r'].shift(1)
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi_14'] = 100 - (100 / (1 + rs))
    
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift(1)).abs()
    tr3 = (df['low'] - df['close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr_14'] = tr.rolling(14).mean()
    
    df['vol_change'] = df['volume'].pct_change()
    
    ema = df['close'].ewm(span=200, adjust=False).mean()
    df['ema_200_dist'] = (df['close'] - ema) / ema
    
    return df.dropna()

# Import Execution Engine
try:
    from execution import HyperliquidTrader
    TRADER = HyperliquidTrader(testnet=False) # Mainnet
    print("✅ Execution Engine Connected.")
except Exception as e:
    print(f"⚠️ Execution Engine NOT found or configuration error: {e}")
    TRADER = None

def place_order(coin, is_buy, size_usd, tp=None, sl=None):
    if TRADER:
        print(f"\n🚀 EXECUTING AUTOMATED TRADE via Hyperliquid SDK...")
        success = TRADER.execute_trade(coin, is_buy, size_usd, tp, sl)
        if success:
            print(f"✅ Trade Executed Successfully for {coin}")
        else:
            print(f"❌ Trade Execution FAILED for {coin}")
    else:
        # Fallback to Manual Instructions
        print(f"\n🚀 EXECUTE TRADE (Manual Action Required):")
        print(f"   Coin: {coin}")
        print(f"   Side: {'BUY (Long)' if is_buy else 'SELL (Short)'}")
        print(f"   Size: ${size_usd} (Leverage {LEVERAGE}x)")
        
        if tp and sl:
            print(f"   Take Profit: {tp:.4f}")
            print(f"   Stop Loss:   {sl:.4f}")

# ... (Imports remain the same)

class WilliamsStrategy:
    def __init__(self):
        print("🤖 Initializing Strategy Engine...")
        self.active_positions = {}
        self.coins = ['BTC', 'ETH', 'SOL', 'AVAX', 'SUI']
        self.features = ['williams_r', 'rsi_14', 'atr_14', 'vol_change', 'ema_200_dist']
        
        # Load Model
        self.model = xgb.XGBClassifier()
        try:
            # Fix: Use specific absolute path based on script location
            base_path = os.path.dirname(os.path.abspath(__file__))
            model_path = os.path.join(base_path, 'model_v1.json')
            
            self.model.load_model(model_path)
            print("✅ Model Loaded Successfully.")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            raise e
            
    def get_market_status(self):
        """Fetch latest data and return detailed status for all coins"""
        status = []
        
        for coin in self.coins:
            try:
                # 1. Fetch Data
                df = fetch_candles(coin)
                if df.empty: 
                    status.append({'coin': coin, 'price': 0, 'conf': 0, 'wr': 0, 'signal': None, 'error': 'No Data'})
                    continue
                
                # 2. Features
                df = add_features(df)
                if df.empty: 
                    status.append({'coin': coin, 'price': 0, 'conf': 0, 'wr': 0, 'signal': None, 'error': 'Not enough data'})
                    continue
                
                last_row = df.iloc[-1]
                price = last_row['close']
                
                # 3. Model Prediction
                X = last_row[self.features].to_frame().T.replace([np.inf, -np.inf], np.nan).fillna(0)
                prob = self.model.predict_proba(X)[0][1]
                
                # 4. Signal Logic
                curr_wr = last_row['williams_r']
                prev_wr = last_row['williams_r_prev']
                
                signal = None
                
                # Momentum Breakout (Long)
                if (prev_wr < -20 and curr_wr >= -20):
                    if prob >= CONF_THRESH:
                        signal = 'LONG'
                # Momentum Breakdown (Short)
                elif (prev_wr > -80 and curr_wr <= -80):
                    if prob >= CONF_THRESH:
                        signal = 'SHORT'
                        
                status.append({
                    'coin': coin,
                    'price': price,
                    'conf': prob,
                    'wr': curr_wr,
                    'signal': signal,
                    'error': None
                })
                
                # 5. Execute Auto-Trade
                if signal:
                    self.execute_signal(coin, signal, price)
                        
            except Exception as e:
                status.append({'coin': coin, 'price': 0, 'conf': 0, 'wr': 0, 'signal': None, 'error': str(e)})
                
        return status

    def execute_signal(self, coin, signal, price):
        if coin in self.active_positions: return # Debounce
        
        print(f"   🚨 SIGNAL FOUND: {coin} {signal}")
        
        if signal == 'LONG':
            tp = price * (1 + TP_PCT)
            sl = price * (1 - SL_PCT)
            place_order(coin, True, MAX_POSITION_SIZE_USD, tp, sl)
        else:
            tp = price * (1 - TP_PCT)
            sl = price * (1 + SL_PCT)
            place_order(coin, False, MAX_POSITION_SIZE_USD, tp, sl)
            
        self.active_positions[coin] = {'entry': price, 'type': signal, 'ts': datetime.now()}

def run_bot():
    print("🤖 WILLIAMS %R V1 LIVE TRADER (Sanity One)")
    print(f"   Account: ~$53 (Assumed)")
    print(f"   Leverage: {LEVERAGE}x (Aggressive Growth)")
    print("--------------------------------------------------")
    
    strategy = WilliamsStrategy()
    
    while True:
        print(f"\n⏳ Loop Start: {datetime.now().strftime('%H:%M:%S')}")
        status = strategy.get_market_status()
        
        for s in status:
            symbol = "🟢" if s['conf'] > 0.5 else "⚪"
            if s['conf'] > CONF_THRESH: symbol = "🔥"
            
            error_msg = f" ({s['error']})" if s['error'] else ""
            print(f"   {s['coin']:<4} | WR: {s['wr']:>6.1f} | Conf: {s['conf']:.2f} {symbol}{error_msg}")
            
        print("   Sleeping 60s...")
        time.sleep(60)

if __name__ == "__main__":
    run_bot()
