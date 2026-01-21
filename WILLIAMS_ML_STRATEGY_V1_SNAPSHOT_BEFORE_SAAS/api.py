
import asyncio
from fastapi import FastAPI, BackgroundTasks
from contextlib import asynccontextmanager
from live_trader import WilliamsStrategy
import threading
import time

# Global Strategy Instance
strategy = None
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
    global strategy, is_running, background_thread
    print("🔌 Starting Quant Engine API...")
    strategy = WilliamsStrategy()
    
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

@app.get("/")
def read_root():
    return {"status": "online", "system": "Williams V1 Sanity Engine"}

@app.get("/status")
def get_market_status():
    """Get real-time market data and signals"""
    if not strategy: return {"error": "Strategy initializing"}
    return strategy.get_market_status()

@app.get("/positions")
def get_positions():
    """Get active trades"""
    if not strategy: return {"error": "Strategy initializing"}
    # Convert datetime objects to string for JSON serialization
    serialized_positions = {}
    for coin, pos in strategy.active_positions.items():
        pos_copy = pos.copy()
        if 'ts' in pos_copy:
            pos_copy['ts'] = pos_copy['ts'].isoformat()
        serialized_positions[coin] = pos_copy
    return serialized_positions

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

if __name__ == "__main__":
    import uvicorn
    # Run on 0.0.0.0 to be accessible
    uvicorn.run(app, host="0.0.0.0", port=8000)
