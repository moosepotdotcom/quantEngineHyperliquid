
import asyncio
from fastapi import FastAPI, BackgroundTasks
from contextlib import asynccontextmanager
from live_trader import WilliamsStrategy
from copy_trading import CopyTradingEngine
import threading
import time

# Global Strategy Instance
strategy = None
copy_engine = None
is_running = False
background_thread = None

def strategy_loop():
    """Background loop to keep the strategy running (scanning & executing)"""
    global is_running
    print("🚀 API Strategy Loop Started.")
    while is_running:
        try:
            # Re-use the get_market_status method which fetches data AND executes trades
            # This keeps the logic centralized in the strategy class
            strategy.get_market_status()
        except Exception as e:
            print(f"❌ Strategy Loop Error: {e}")
        
        # Sleep 60s
        time.sleep(60)
    print("🛑 API Strategy Loop Stopped.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global strategy, is_running, background_thread, copy_engine
    print("🔌 Starting Quant Engine API...")
    strategy = WilliamsStrategy()
    copy_engine = CopyTradingEngine()
    
    # Link Strategy to Copy Engine
    # We need to inject the copy engine into the strategy or hook it up
    # For now, let's just make it available globally.
    # Ideally, strategy should call copy_engine.broadcast_trade()
    strategy.copy_engine = copy_engine
    
    # Auto-start the bot loop on server launch? 
    # Let's make it manual via /start to be safe, or auto.
    # User might want it auto. Let's default to auto for now.
    is_running = True
    background_thread = threading.Thread(target=strategy_loop, daemon=True)
    background_thread.start()
    
    yield
    
    # Shutdown
    print("🔌 Shutting down Quant Engine API...")
    is_running = False
    if background_thread:
        background_thread.join(timeout=2)

app = FastAPI(title="Williams V1 Quant API", lifespan=lifespan)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for dev, restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "online", "system": "Williams V1 Sanity Engine"}

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import numpy as np
import math

def clean_data(data):
    """Recursively convert numpy types to native python types"""
    if isinstance(data, dict):
        return {k: clean_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_data(v) for v in data]
    elif isinstance(data, (np.integer, int)):
        return int(data)
    elif isinstance(data, (np.floating, float)):
        val = float(data)
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    elif isinstance(data, (np.bool_, bool)):
        return bool(data)
    elif isinstance(data, (np.ndarray,)): 
        return clean_data(data.tolist())
    return data

@app.get("/status")
def get_market_status():
    """Get real-time market data and signals"""
    if not strategy: return {"error": "Strategy initializing"}
    try:
        raw_status = strategy.get_market_status()
        
        # Dedup logic: Keep only the first occurrence of each coin
        # This handles potential race conditions or list accumulation bugs
        unique_status = []
        seen_coins = set()
        for item in raw_status:
            if item['coin'] not in seen_coins:
                unique_status.append(item)
                seen_coins.add(item['coin'])
                
        data = clean_data(unique_status)
        
        # Enrich with Account Info
        account_info = {
            "mode": strategy.mode,
            "leverage": strategy.leverage,
            "balance": 0.0
        }
        
        if strategy.execution:
            info = strategy.execution.get_account_info()
            account_info['balance'] = info.get('balance', 0)
            
        return {"market": data, "account": account_info}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

@app.get("/positions")
def get_positions():
    """Get active trades from the Execution Engine (Source of Truth)"""
    if not strategy: return {"error": "Strategy initializing"}
    
    positions = {}
    
    # Preferred: Get from Execution Engine (Live or Paper)
    if strategy.execution:
        try:
            info = strategy.execution.get_account_info()
            raw_positions = info.get('positions', [])
            
            # Normalize to dictionary format expected by frontend {coin: { ... }}
            for p in raw_positions:
                coin = p.get('coin')
                if coin:
                    positions[coin] = p
                    
            return positions
        except Exception as e:
            print(f"Error fetching positions from execution: {e}")
            
    # Fallback (Legacy)
    # Convert datetime objects to string for JSON serialization
    for coin, pos in strategy.active_positions.items():
        pos_copy = pos.copy()
        if 'ts' in pos_copy:
            pos_copy['ts'] = pos_copy['ts'].isoformat()
        positions[coin] = pos_copy
        
    return positions

@app.post("/control/start")
def start_bot():
    global is_running, background_thread
    if is_running:
        return {"message": "Bot is already running"}
    
    is_running = True
    background_thread = threading.Thread(target=strategy_loop, daemon=True)
    background_thread.start()
    return {"message": "Bot started"}

@app.post("/control/stop")
def stop_bot():
    global is_running
    is_running = False
    return {"message": "Bot stopping (wait 60s max)"}

from pydantic import BaseModel

class ModeSettings(BaseModel):
    mode: str # 'LIVE' or 'PAPER'

class LeverageSettings(BaseModel):
    leverage: int

@app.post("/settings/mode")
def set_mode(settings: ModeSettings):
    if not strategy: return {"error": "Strategy initializing"}
    success = strategy.set_mode(settings.mode)
    if success:
        return {"status": "ok", "mode": strategy.mode}
    return {"status": "error", "message": "Invalid mode"}

@app.post("/settings/leverage")
def set_leverage(settings: LeverageSettings):
    if not strategy: return {"error": "Strategy initializing"}
    success = strategy.set_leverage(settings.leverage)
    return {"status": "ok", "leverage": strategy.leverage}

@app.post("/trade/close/{coin}")
def close_trade(coin: str):
    if not strategy: return {"error": "Strategy initializing"}
    success = strategy.manual_close(coin)
    if success:
        return {"status": "ok", "message": f"Closed {coin}"}
    return {"status": "error", "message": "Position not found or failed"}

@app.post("/trade/close-all")
def close_all():
    if not strategy: return {"error": "Strategy initializing"}
    strategy.manual_close_all()
    return {"status": "ok", "message": "Panic close triggered"}

# --- SAAS ENDPOINTS ---

class SubscriberRequest(BaseModel):
    user_id: str
    wallet_address: str
    api_key: str
    risk_multiplier: float = 1.0

@app.post("/saas/subscribe")
def add_subscriber(sub: SubscriberRequest):
    if not copy_engine: return {"error": "SaaS Engine initializing"}
    success, msg = copy_engine.add_subscriber(sub.user_id, sub.wallet_address, sub.api_key, sub.risk_multiplier)
    if success:
        return {"status": "ok", "message": f"Welcome {sub.user_id}!"}
    return {"status": "error", "message": msg}

@app.get("/saas/subscribers")
def list_subscribers():
    if not copy_engine: return []
    # Return safe list (no keys)
    safe_list = []
    for uid, data in copy_engine.subscribers.items():
        safe_list.append({"user_id": uid, "wallet": data['wallet'], "risk": data['risk']})
    return safe_list

if __name__ == "__main__":
    import uvicorn
    # Run on 0.0.0.0 to be accessible
    uvicorn.run(app, host="0.0.0.0", port=8000)
