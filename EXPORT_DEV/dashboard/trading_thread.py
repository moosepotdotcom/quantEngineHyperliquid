import threading
import time
import sys
import os
import queue
from datetime import datetime
from dotenv import load_dotenv

# Load Env Vars
load_dotenv()

# Add parent directory to path to import engine
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live_trading_engine import LiveTradingEngine
from hyperliquid_live_trader import HyperliquidTrader

class TradingThread(threading.Thread):
    def __init__(self, enable_live=False, testnet=True):
        super().__init__()
        self.daemon = True
        self.running = False
        self.paused = False
        self.lock = threading.Lock()
        
        # Log queue
        self.log_queue = queue.Queue(maxsize=100)
        
        # Setup Output Capture
        self.original_stdout = sys.stdout
        sys.stdout = self # Redirect global print() to this class
        
        # Initialize Engine
        # (This runs after redirect, so engine logs will be captured)
        # CRITICAL: Default to MAINNET if not specified, per user request "connect to real account"
        # If the user wants testnet, they must explicitly ask for it.
        # But wait, the arguments are passed in.
        # We will override the default in __init__ signature or just pass correct one.
        
        # Let's verify what `app.py` passes.
        # Actually, let's just force testnet=False here if we want to be sure, 
        # but better is to update `app.py` to pass the right flag or default the init to False.
        self.engine = LiveTradingEngine(enable_live=enable_live, testnet=testnet)
        
        # State storage
        self.latest_data = {
            'timestamp': str(datetime.now()),
            'price': 0.0,
            'confidence': 0.0,
            'signal': 'NEUTRAL',
            'market_regime': 'Unknown',
            'daily_pnl': 0.0,
            'active_positions': [],
            'balance': 0.0,
            'logs': []
        }

    def write(self, message):
        """Capture stdout messages"""
        if message.strip(): # Ignore empty newlines
            self.add_log(message.strip())
        self.original_stdout.write(message) # Also print to real terminal
        self.original_stdout.flush()

    def flush(self):
        self.original_stdout.flush()
        
    def add_log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        # clean message
        clean_msg = message
        entry = f"[{timestamp}] {clean_msg}"
        
        # Store in queue
        if self.log_queue.full():
            try: self.log_queue.get_nowait()
            except: pass
        self.log_queue.put(entry)

    def run(self):
        """Main loop running in background thread"""
        self.running = True
        self.add_log("🚀 Trading Thread Started")
        
        while self.running:
            if self.paused:
                time.sleep(1)
                continue
                
            try:
                # 1. Fetch Data & Run AI
                # We access the internal paper_engine methods
                # self.engine.paper_engine.check_mtf_scalper() etc.
                
                # Fetch Latest Price first
                self.engine.live_trader._check_safety_limits() # Just to refresh logic
                
                # Run AI Strategy (Winner Hunter + MTF Scalper)
                # We use the method from LiveTradingEngine but capture output
                
                # --- SNAPSHOT PRICE ---
                # Fetch 1m data quickly for Price/Balance Update
                try:
                    # Creating a quick fetch for recent price
                    df_recent = self.engine.paper_engine.fetch_data('1m', 5)
                    if df_recent is not None and len(df_recent) > 0:
                        last_price = float(df_recent.iloc[-1]['close'])
                        with self.lock:
                            self.latest_data['price'] = last_price
                except:
                    pass

                # Get Account Info (Balance/Positions)
                if self.engine.enable_live and self.engine.live_trader:
                    try:
                        account_info = self.engine.live_trader.get_account_info()
                        with self.lock:
                            # Account Value = 'marginSummary' -> 'accountValue' (Total Equity)
                            val = float(account_info.get('balance', 0.0))
                            self.latest_data['balance'] = val
                            
                            # Positions
                            raw_pos = account_info.get('positions', [])
                            # Filter for open positions (szi != 0)
                            active_pos = []
                            for p in raw_pos:
                                pos_data = p.get('position', p)
                                if float(pos_data.get('szi', 0)) != 0:
                                    active_pos.append(pos_data)
                            self.latest_data['active_positions'] = active_pos
                            
                            # Calculate Unrealized PnL from active positions
                            pnl = 0.0
                            for pos in active_pos:
                                pnl += float(pos.get('unrealizedPnl', 0))
                            # Add to daily pnl (realized)
                            self.latest_data['daily_pnl'] = self.engine.live_trader.daily_pnl + pnl
                    except Exception as e:
                        print(f"Error fetching account info: {e}")
                
                # Run Checks

                # self.add_log("🔍 Analyzing Markets...")
                
                # Winner Hunter
                wh_signal, wh_conf = self.engine.paper_engine.check_winner_hunter()
                
                # MTF Scalper
                mtf_signal, mtf_conf = self.engine.paper_engine.check_mtf_scalper()
                
                # Determine max confidence for display
                max_conf = max(wh_conf, mtf_conf)
                
                # Update State
                with self.lock:
                    self.latest_data['confidence'] = max_conf
                    self.latest_data['timestamp'] = str(datetime.now().strftime("%H:%M:%S"))
                    
                    if wh_signal:
                        self.latest_data['signal'] = f"WH: {wh_signal['direction']}"
                        self.latest_data['price'] = wh_signal.get('price', 0)
                        self.add_log(f"Signal: {wh_signal['direction']} ({max_conf:.2%})")
                    elif mtf_signal:
                        self.latest_data['signal'] = f"MTF: {mtf_signal['direction']}"
                        self.latest_data['price'] = mtf_signal.get('price', 0)
                        self.add_log(f"Signal: {mtf_signal['direction']} ({max_conf:.2%})")
                    else:
                        self.latest_data['signal'] = "NEUTRAL"
                        # Optimization: if no signal, price isn't updated by engine return
                        # We should likely fetch a price for display
                        
            except Exception as e:
                self.add_log(f"⚠️ Loop Error: {e}")
            
            # Sleep logic
            time.sleep(10) # 10s polling for dashboard
            
    def stop(self):
        self.running = False
        
    def manual_buy(self, size=None):
        self.add_log("👉 Manual BUY Triggered")
        # Construct a fake signal to pass to execute logic
        signal = {
            'model': 'MANUAL_OVERRIDE',
            'direction': 'LONG',
            'price': self.latest_data['price'], # Use last known price
            'confidence': 1.0
        }
        # Execute via Live Trader
        if self.engine.live_trader:
             # Refetch price for accuracy
            # For now, simplistic
            success = self.engine.live_trader.execute_signal(signal)
            if success:
                self.add_log("✅ Manual Buy Executed")
            else:
                self.add_log("❌ Manual Buy Failed")
                
    def manual_sell(self, size=None):
        self.add_log("👉 Manual SELL Triggered")
        signal = {
            'model': 'MANUAL_OVERRIDE',
            'direction': 'SHORT',
            'price': self.latest_data['price'],
            'confidence': 1.0
        }
        if self.engine.live_trader:
            success = self.engine.live_trader.execute_signal(signal)
            if success:
                self.add_log("✅ Manual Sell Executed")
            else:
                self.add_log("❌ Manual Sell Failed")

    def emergency_close(self):
        self.add_log("🚨 EMERGENCY STOP TRIGGERED")
        if self.engine.live_trader:
            self.engine.live_trader.emergency_stop_all()
            self.add_log("✅ All positions closed.")

    def get_state(self):
        with self.lock:
            # Get latest logs
            logs = []
            while not self.log_queue.empty():
                logs.append(self.log_queue.get())
                
            return {
                'data': self.latest_data,
                'logs': logs # returns only NEW logs since last check
            }
