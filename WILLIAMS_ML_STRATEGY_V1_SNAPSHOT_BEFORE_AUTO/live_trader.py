
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

def place_order(coin, is_buy, size_usd, tp=None, sl=None):
    # This is a PLACEHOLDER for real execution logic.
    # User needs to interact with the official SDK or `hyperliquid_live_trader.py`.
    # For now, we print exact instructions.
    
    print(f"\n🚀 EXECUTE TRADE (Action Required):")
    print(f"   Coin: {coin}")
    print(f"   Side: {'BUY (Long)' if is_buy else 'SELL (Short)'}")
    print(f"   Size: ${size_usd} (Leverage {LEVERAGE}x)")
    
    if tp and sl:
        print(f"   Take Profit: {tp:.4f}")
        print(f"   Stop Loss:   {sl:.4f}")
        
    # In a full implementation, we'd import HyperliquidTrader here
    # from hyperliquid_live_trader import HyperliquidTrader
    # trader = HyperliquidTrader(testnet=False)
    # trader.execute_signal(...)

def run_bot():
    print("🤖 WILLIAMS %R V1 LIVE TRADER (Sanity One)")
    print(f"   Account: ~$53 (Assumed)")
    print(f"   Leverage: {LEVERAGE}x (Aggressive Growth)")
    print(f"   Trading: BTC, ETH, SOL, AVAX, SUI")
    print("--------------------------------------------------")
    
    # Load Model
    model = xgb.XGBClassifier()
    try:
        model.load_model('model_v1.json')
        print("✅ Model Loaded Successfully.")
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return

    coins = ['BTC', 'ETH', 'SOL', 'AVAX', 'SUI']
    features = ['williams_r', 'rsi_14', 'atr_14', 'vol_change', 'ema_200_dist']
    
    while True:
        print(f"\n⏳ Loop Start: {datetime.now().strftime('%H:%M:%S')}")
        
        for coin in coins:
            try:
                # 1. Fetch Data
                df = fetch_candles(coin)
                if df.empty: continue
                
                # 2. Features
                df = add_features(df)
                if df.empty: continue
                
                last_row = df.iloc[-1]
                
                # 3. Model Prediction
                X = last_row[features].to_frame().T.replace([np.inf, -np.inf], np.nan).fillna(0)
                prob = model.predict_proba(X)[0][1]
                
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
                
                # Log Status
                symbol = "🟢" if prob > 0.5 else "⚪"
                if prob > CONF_THRESH: symbol = "🔥"
                print(f"   {coin:<4} | WR: {curr_wr:>6.1f} | Conf: {prob:.2f} {symbol}")
                
                # 5. Execute
                if signal:
                    print(f"   🚨 SIGNAL FOUND: {coin} {signal} (Conf {prob:.2f})")
                    price = last_row['close']
                    
                    if coin not in active_positions:
                        if signal == 'LONG':
                            tp = price * (1 + TP_PCT)
                            sl = price * (1 - SL_PCT)
                            place_order(coin, True, MAX_POSITION_SIZE_USD, tp, sl)
                        else:
                            tp = price * (1 - TP_PCT)
                            sl = price * (1 + SL_PCT)
                            place_order(coin, False, MAX_POSITION_SIZE_USD, tp, sl)
                            
                        active_positions[coin] = {'entry': price, 'type': signal}
                        
            except Exception as e:
                print(f"   ❌ Error processing {coin}: {e}")
                
        print("   Sleeping 60s...")
        time.sleep(60)

if __name__ == "__main__":
    run_bot()
