"""
⚙️ SCALPER SYSTEM CONFIGURATION
"""
import os

# --- CONNECTION ---
WS_URL = "wss://api.hyperliquid.xyz/ws"
API_URL = "https://api.hyperliquid.xyz"
SYMBOL = "BTC"

# --- STRATEGY: LIQUIDATION REVERSAL ---
LIQ_WINDOW_SECONDS = 60
LIQ_THRESHOLD_USD = 100.0  # $100 (Capture smallest liquidations for observation)
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

# --- EXECUTION ---
LEVERAGE = 15
MAX_POSITION_SIZE_USD = 1000.0 # Safety cap
TP_PCT = 0.003 # 0.3%
SL_PCT = 0.005 # 0.5%
COOLDOWN_SECONDS = 300

# Credentials (loaded from ENV or empty for dry-run)
# Found in .env.live_trading
WALLET_ADDRESS = os.getenv("HYPERLIQUID_WALLET_ADDRESS", "0xC09589118faBf232f2aCb9d62a6467e3E584D170")
PRIVATE_KEY = os.getenv("HYPERLIQUID_API_SECRET", "0xf06f4fd2a7516373cc4c8e99afd8c7445b4db0735de0fbe860cfa2b343bfc086")

# --- LOGGING ---
LOG_DIR = "logs"
DATA_DIR = "data"
LIVE_LOG_FILE = f"{LOG_DIR}/system_live.log"
LIQ_DATA_FILE = f"{DATA_DIR}/liquidations_master.csv"
