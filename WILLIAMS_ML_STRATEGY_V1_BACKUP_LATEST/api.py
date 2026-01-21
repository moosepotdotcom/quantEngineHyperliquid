
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
                    # Normalize Hyperliquid keys to Frontend keys
                    size_str = p.get('szi', '0')
                    size = float(size_str)
                    entry = float(p.get('entryPx', '0'))
                    
                    normalized = {
                        "coin": coin,
                        "entry": entry,
                        "size": abs(size),
                        "type": "LONG" if size > 0 else "SHORT",
                        "unrealized_pnl": float(p.get('unrealizedPnl', '0')),
                        # Pass through TP/SL if they exist (Paper Engine custom fields)
                        "tp": p.get('tp'), 
                        "sl": p.get('sl')
                    }
                    positions[coin] = normalized
                    
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

# --- AUTHENTICATION ---
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from auth import create_access_token, get_user, verify_password, get_db, SessionLocal, User
from sqlalchemy.orm import Session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    from jose import JWTError, jwt
    from auth import SECRET_KEY, ALGORITHM
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = get_user(db, username=username)
    if user is None:
        raise credentials_exception
    return user

def get_current_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = get_user(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer", "role": user.role}

# --- ENDPOINTS ---

@app.get("/")
def read_root():
    return {"status": "online", "system": "Williams V1 SaaS Platform"}

# ... (clean_data helper remains)

# --- PROTECTED CONTROL ENDPOINTS ---

@app.post("/control/start")
def start_bot(current_user: User = Depends(get_current_admin)):
    global is_running, background_thread
    if is_running:
        return {"message": "Bot is already running"}
    
    is_running = True
    background_thread = threading.Thread(target=strategy_loop, daemon=True)
    background_thread.start()
    return {"message": "Bot started"}

@app.post("/control/stop")
def stop_bot(current_user: User = Depends(get_current_admin)):
    global is_running
    is_running = False
    return {"message": "Bot stopping (wait 60s max)"}

# --- SETTINGS ENDPOINTS (ADMIN) ---

from pydantic import BaseModel

class ModeSettings(BaseModel):
    mode: str # 'LIVE' or 'PAPER'

class LeverageSettings(BaseModel):
    leverage: int

@app.post("/settings/mode")
def set_mode(settings: ModeSettings, current_user: User = Depends(get_current_admin)):
    if not strategy: return {"error": "Strategy initializing"}
    success = strategy.set_mode(settings.mode)
    if success:
        return {"status": "ok", "mode": strategy.mode}
    return {"status": "error", "message": "Invalid mode"}

@app.post("/settings/leverage")
def set_leverage(settings: LeverageSettings, current_user: User = Depends(get_current_admin)):
    if not strategy: return {"error": "Strategy initializing"}
    success = strategy.set_leverage(settings.leverage)
    return {"status": "ok", "leverage": strategy.leverage}

@app.post("/trade/close/{coin}")
def close_trade(coin: str, current_user: User = Depends(get_current_admin)):
    if not strategy: return {"error": "Strategy initializing"}
    success = strategy.manual_close(coin)
    if success:
        return {"status": "ok", "message": f"Closed {coin}"}
    return {"status": "error", "message": "Position not found or failed"}

@app.post("/trade/close-all")
def close_all(current_user: User = Depends(get_current_admin)):
    if not strategy: return {"error": "Strategy initializing"}
    strategy.manual_close_all()
    return {"status": "ok", "message": "Panic close triggered"}

# --- SAAS ENDPOINTS (ADMIN & SUBSCRIBER) ---

class SubscriberRequest(BaseModel):
    user_id: str
    wallet_address: str
    api_key: str
    risk_multiplier: float = 1.0

# Only Admin can manually add subscribers (or a Billing Webhook)
@app.post("/saas/subscribe")
def add_subscriber(sub: SubscriberRequest, current_user: User = Depends(get_current_admin)):
    if not copy_engine: return {"error": "SaaS Engine initializing"}
    success, msg = copy_engine.add_subscriber(sub.user_id, sub.wallet_address, sub.api_key, sub.risk_multiplier)
    if success:
        return {"status": "ok", "message": f"Welcome {sub.user_id}!"}
    return {"status": "error", "message": msg}

class ConfigureRequest(BaseModel):
    wallet_address: str
    api_key: str
    risk_multiplier: float = 1.0

@app.post("/saas/configure")
def configure_subscriber(config: ConfigureRequest, current_user: User = Depends(get_current_user)):
    """Self-Service configuration for logged-in users"""
    if not copy_engine: return {"error": "SaaS Engine initializing"}
    
    # Check if user exists in copy engine, if not add, else update
    if current_user.username in copy_engine.subscribers:
        success, msg = copy_engine.update_subscriber(
            current_user.username, 
            config.wallet_address, 
            config.api_key, 
            config.risk_multiplier
        )
    else:
        # First time setup
        success, msg = copy_engine.add_subscriber(
            current_user.username, 
            config.wallet_address, 
            config.api_key, 
            config.risk_multiplier
        )
        
    if success:
        return {"status": "ok", "message": "Configuration saved"}
    return {"status": "error", "message": msg}

# Admin views all, User views self (Todo: filter for user)
@app.get("/saas/subscribers")
def list_subscribers(current_user: User = Depends(get_current_admin)):
    if not copy_engine: return []
    safe_list = []
    for uid, data in copy_engine.subscribers.items():
        safe_list.append({"user_id": uid, "wallet": data['wallet'], "risk": data['risk']})
    return safe_list

@app.delete("/saas/subscriber/{user_id}")
def remove_subscriber(user_id: str, current_user: User = Depends(get_current_admin)):
    if not copy_engine: return {"error": "SaaS Engine initializing"}
    success = copy_engine.remove_subscriber(user_id)
    if success:
        return {"status": "ok", "message": f"Removed {user_id}"}
    return {"status": "error", "message": "User not found"}

if __name__ == "__main__":
    import uvicorn
    # Run on 0.0.0.0 to be accessible
    uvicorn.run(app, host="0.0.0.0", port=8000)
