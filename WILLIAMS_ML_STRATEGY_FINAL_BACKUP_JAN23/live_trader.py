
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
from paper_execution import PaperExecutionEngine
# Try import HyperliquidTrader, handle failure if not present
try:
    from execution import HyperliquidTrader
except ImportError:
    HyperliquidTrader = None
    print("⚠️ HyperliquidTrader not found, LIVE mode might fail.")

from trend_filter import get_market_regime, should_trade

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
LEVERAGE = 3 
MAX_POSITION_SIZE_USD = 150.0 

# Active Positions Tracker
active_positions = {}

def get_price(coin):
    url = "https://api.hyperliquid.xyz/info"
    payload = {"type": "metaAndAssetCtxs"}
    try:
        resp = requests.post(url, json=payload, timeout=15)
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
        # print(f"DEBUG: Fetching {coin}...") 
        resp = requests.post(url, json=payload, timeout=15)
        data = resp.json()
        if not data: 
            print(f"⚠️ Empty Data for {coin}")
            return pd.DataFrame()
        
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
        print(f"❌ Error fetching candles for {coin}: {e}")
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

class WilliamsStrategy:
    def __init__(self, mode='PAPER'):
        self.mode = mode
        print(f"🤖 Initializing Strategy Engine ({self.mode} Mode)...")
        
        # Initialize Execution Engine
        if self.mode == 'LIVE':
             try:
                if HyperliquidTrader:
                    self.execution = HyperliquidTrader(testnet=False)
                    self.market_open = True
                else:
                    self.execution = None
                    self.market_open = False
             except Exception as e:
                print(f"❌ Live Execution Failed: {e}")
                self.execution = None
                self.market_open = False
        else:
             self.execution = PaperExecutionEngine(initial_balance=10000.0)
             self.market_open = True

        self.leverage = 3
        self.use_regime_filter = True # Default: ON
        self.copy_engine = None # Injected by API
        self.coins = ['BTC', 'ETH', 'SOL', 'AVAX', 'SUI']
        self.features = ['williams_r', 'rsi_14', 'atr_14', 'vol_change', 'ema_200_dist']
        
        # Load Model
        self.model = xgb.XGBClassifier()
        try:
            # Fix: Use specific absolute path based on script location
            base_path = os.path.dirname(os.path.abspath(__file__))
            model_path = os.path.join(base_path, 'model_v1.json')
            
            self.model.load_model(model_path)
            print(f"✅ Model Loaded Successfully ({model_path})")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            self.model = None

    def set_regime_filter(self, enabled: bool):
        self.use_regime_filter = enabled
        print(f"🛡️ Regime Filter Set to: {'ON' if enabled else 'OFF'}")
        return True

    def get_market_status(self):
        """Fetch latest data and return detailed status for all coins"""
        status = []
        
        # Valid Model Check
        if not self.model:
            return [{'coin': 'SYS', 'price': 0, 'conf': 0, 'wr': 0, 'regime': 'ERR', 'signal': None, 'error': 'Model Not Loaded'}]

        for coin in self.coins:
            time.sleep(0.2) # Rate limit protection
            try:
                # 1. Fetch Data
                df = fetch_candles(coin)
                if df.empty: 
                    status.append({'coin': coin, 'price': 0, 'conf': 0, 'wr': 0, 'regime': 'ERR', 'signal': None, 'error': 'No Data'})
                    continue
                
                # 2. Features
                df = add_features(df)
                if df.empty: 
                    status.append({'coin': coin, 'price': 0, 'conf': 0, 'wr': 0, 'regime': 'ERR', 'signal': None, 'error': 'Not enough data'})
                    continue
                
                last_row = df.iloc[-1]
                price = last_row['close']
                
                # 3. Model Prediction
                X = last_row[self.features].to_frame().T.replace([np.inf, -np.inf], np.nan).fillna(0)
                prob = self.model.predict_proba(X)[0][1]
                
                # 4. Signal Logic
                curr_wr = last_row['williams_r']
                prev_wr = last_row.get('williams_r_prev', 0) # Handle potential missing column if shift failed (unlikely)
                # Recalculate WR Prev to be safe or use what's in DF
                if 'williams_r_prev' not in df.columns:
                     prev_wr = df['williams_r'].iloc[-2]
                else:
                     prev_wr = last_row['williams_r_prev']

                
                # A. Regime Detection
                regime = get_market_regime(df)
                
                raw_signal = None
                
                # Momentum Breakout (Long)
                if (prev_wr < -20 and curr_wr >= -20):
                    if prob >= CONF_THRESH:
                        raw_signal = 'LONG'
                # Momentum Breakdown (Short)
                elif (prev_wr > -80 and curr_wr <= -80):
                    if prob >= CONF_THRESH:
                        raw_signal = 'SHORT'
                
                # B. Regime Filtering
                final_signal = None
                reject_reason = None
                
                if raw_signal:
                    if self.use_regime_filter:
                        is_valid, reason = should_trade(raw_signal, regime)
                        if is_valid:
                            final_signal = raw_signal
                        else:
                            reject_reason = reason
                    else:
                        # Filter Disabled: Take all raw signals
                        final_signal = raw_signal
                        reject_reason = "Filter Disabled"
                        
                status.append({
                    'coin': coin,
                    'price': price,
                    'conf': prob,
                    'wr': curr_wr,
                    'regime': regime,
                    'signal': final_signal,
                    'error': reject_reason # Show rejection reason as error/info
                })
                
                # 5. Execute Auto-Trade
                if final_signal:
                    self.execute_signal(coin, final_signal, price)
                        
            except Exception as e:
                print(f"Error processing {coin}: {e}")
                status.append({'coin': coin, 'price': 0, 'conf': 0, 'wr': 0, 'regime': 'ERR', 'signal': None, 'error': str(e)})
        
        # AUTOMATED PAPER POSITION MANAGEMENT
        if self.mode == 'PAPER' and self.execution:
            current_prices = {s['coin']: s['price'] for s in status if isinstance(s, dict) and s.get('price', 0) > 0}
            self.execution.check_positions(current_prices)
                
        return status

    def execute_signal(self, coin, signal, price):
        # SINGLE SOURCE OF TRUTH DEBOUNCE
        if self.execution:
            info = self.execution.get_account_info()
            positions = info.get('positions', [])
            active_coins = {p.get('coin') for p in positions}
            
            if coin in active_coins:
                return 
        
        print(f"   🚨 SIGNAL FOUND: {coin} {signal}")
        
        if signal == 'LONG':
            tp = price * (1 + TP_PCT)
            sl = price * (1 - SL_PCT)
            self.place_order(coin, True, MAX_POSITION_SIZE_USD, tp, sl)
            if self.copy_engine:
                 self.copy_engine.broadcast_trade(coin, True, price, MAX_POSITION_SIZE_USD, tp, sl)
        else:
            tp = price * (1 - TP_PCT)
            sl = price * (1 + SL_PCT)
            self.place_order(coin, False, MAX_POSITION_SIZE_USD, tp, sl)
            if self.copy_engine:
                 self.copy_engine.broadcast_trade(coin, False, price, MAX_POSITION_SIZE_USD, tp, sl)

    def place_order(self, coin, is_buy, size_usd, tp=None, sl=None):
        if self.execution:
            if self.mode == 'PAPER':
                self.execution.leverage = self.leverage
            print(f"\n🚀 EXECUTING AUTOMATED TRADE via {self.mode} Engine...")
            success = self.execution.execute_trade(coin, is_buy, size_usd, tp, sl)
            return success
        else:
            print("❌ No Execution Engine Active")
            return False

    def set_mode(self, new_mode):
        if new_mode not in ['LIVE', 'PAPER']: return False
        if new_mode == self.mode: return True
        
        print(f"🔄 Switching Mode: {self.mode} -> {new_mode}")
        self.mode = new_mode
        self.active_positions = {} 
        
        if self.mode == 'LIVE':
             try:
                self.execution = HyperliquidTrader(testnet=False)
                self.market_open = True
             except:
                self.execution = None
        else:
             self.execution = PaperExecutionEngine(initial_balance=10000.0)
             self.market_open = True
             
        return True

    def set_leverage(self, lev):
        self.leverage = lev
        if self.mode == 'PAPER':
            self.execution.leverage = lev
        global LEVERAGE 
        LEVERAGE = lev
        return True

    def manual_close(self, coin):
        if self.execution:
            if self.mode == 'PAPER':
                return self.execution.close_position(coin)
            # Add live manual close if needed
            pass
        return False

    def manual_close_all(self):
        if self.execution:
            if self.mode == 'PAPER':
                return self.execution.close_all()
            if self.mode == 'LIVE':
                self.execution.emergency_stop_all()
                return True
        return False

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
            
            # Show Regime
            regime_icon = "🌫️"
            if s['regime'] == 'BULLISH': regime_icon = "🐂"
            elif s['regime'] == 'BEARISH': regime_icon = "🐻"
            elif s['regime'] == 'RANGING': regime_icon = "🦀"
            
            # Error/Filter Msg
            msg = ""
            if s['signal']: msg = f"🚀 {s['signal']}"
            elif s.get('error'): msg = f"🛡️ {s['error']}"
            
            print(f"   {s['coin']:<4} | WR: {s['wr']:>6.1f} | Conf: {s['conf']:.2f} {symbol} | {regime_icon} {s['regime']:<8} | {msg}")
            
        print("   Sleeping 60s...")
        time.sleep(60)

if __name__ == "__main__":
    run_bot()
