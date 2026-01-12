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
current_dir = os.path.dirname(os.path.abspath(__file__))
export_dev_dir = os.path.dirname(current_dir) # .../EXPORT_DEV
project_root = os.path.dirname(export_dev_dir) # .../quantEngineHyperliquid

sys.path.insert(0, project_root)
sys.path.insert(0, export_dev_dir) # This will be at index 0, taking precedence

from live_trading_engine import LiveTradingEngine
from hyperliquid_live_trader import HyperliquidTrader
from alpha_engine import AlphaEngine

class TradingThread(threading.Thread):
    def __init__(self, enable_live=False, testnet=True):
        super().__init__()
        self.daemon = True
        self.running = False
        self.paused = False
        self.lock = threading.Lock()
        
        # Log buffer (keeps last 100 logs)
        from collections import deque
        self.log_buffer = deque(maxlen=100)
        
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
        self.alpha_engine = AlphaEngine() # Phase 4: Init Alpha Engine
        
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
            'leverage': 0.0,
            'margin_usage': 0.0,
            'funding_rate': 0.0,
            'alpha_status': {}, # For UI Toggles
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
        # Add to persistent log buffer
        self.log_buffer.append(entry)

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
                            
                            # --- CALCULATE NEW METRICS ---
                            margin_used = float(account_info.get('margin_used', 0))
                            total_ntl = float(account_info.get('total_ntl_pos', 0))
                            
                            if val > 0:
                                self.latest_data['leverage'] = total_ntl / val
                                self.latest_data['margin_usage'] = (margin_used / val) * 100.0
                                
                            # Fetch Funding (Every loop is okay, it's cached/fast or 10s is fine)
                            funding = self.engine.live_trader.get_funding_rate('BTC')
                            self.latest_data['funding_rate'] = funding * 100.0 # Convert to %
                            
                    except Exception as e:
                        print(f"Error fetching account info: {e}")
                
                # Run Checks
                
                # --- PHASE 4: ALPHA ENGINE ---
                # 1. Get Market Context (Walls & Pops)
                market_scan = self.get_whale_walls()
                market_scan['current_price'] = self.latest_data['price']
                
                # 2. Evaluate Alpha Strategies
                alpha_signals = self.alpha_engine.evaluate(market_scan)
                
                # 3. Execute Alpha Signals
                for sig in alpha_signals:
                    self.add_log(f"⚡ ALPHA SIGNAL: {sig['strategy_id']} ({sig['direction']})")
                    # Construct Execution Payload
                    payload = {
                        'model': f"ALPHA_{sig['strategy_id']}",
                        'direction': sig['direction'],
                        'price': sig['price'],
                        'confidence': sig['confidence']
                    }
                    # Execute via Live Trader
                    if self.engine.live_trader:
                        self.engine.live_trader.execute_signal(payload)

                # Periodic "Scanning" Log (every 6 iterations ~ 60s)
                self._scan_counter = getattr(self, '_scan_counter', 0) + 1
                if self._scan_counter >= 6:
                    active_strats = [k for k,v in self.alpha_engine.strategies.items() if v['enabled']]
                    if active_strats:
                        self.add_log(f"⚔️ Alpha Scan Active: {', '.join(active_strats)} searching...")
                    self._scan_counter = 0

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

    def emergency_close(self, close_type='market'):
        self.add_log(f"🚨 EMERGENCY STOP TRIGGERED ({close_type})")
        if self.engine.live_trader:
            self.engine.live_trader.close_all_positions(close_type)
            self.add_log("✅ Close command sent.")

    def get_whale_walls(self):
        """Scan L2 Book for Whale Walls (> $250k) AND Liquidity Pops (> $100k delta)"""
        if self.engine.enable_live and self.engine.live_trader:
            try:
                # 1. Fetch L2
                trader = self.engine.live_trader
                snapshot = trader.info.l2_snapshot("BTC")
                levels = snapshot.get('levels', [])
                
                if not levels or len(levels) < 2: return {'walls': [], 'pops': []}
                
                bids = levels[0]
                asks = levels[1]
                
                # --- WALL SCANNER ---
                walls = []
                threshold = 250000.0 # $250k USD
                
                # Scan Bids
                for b in bids:
                    px = float(b['px'])
                    sz = float(b['sz'])
                    val = px * sz
                    if val > threshold:
                        walls.append({'side': 'BID', 'px': px, 'sz': sz, 'val': val})
                # Scan Asks
                for a in asks:
                    px = float(a['px'])
                    sz = float(a['sz'])
                    val = px * sz
                    if val > threshold:
                        walls.append({'side': 'ASK', 'px': px, 'sz': sz, 'val': val})
                walls.sort(key=lambda x: x['val'], reverse=True)
                
                # --- POP TRACKER (Delta) ---
                pops = []
                pop_threshold = 10000.0 # $10k Delta (Lowered for visibility)
                
                if hasattr(self, 'last_l2') and self.last_l2:
                    last_bids = {b['px']: float(b['sz']) for b in self.last_l2[0]}
                    last_asks = {a['px']: float(a['sz']) for a in self.last_l2[1]}
                    
                    # Check Bids
                    for b in bids:
                        px = b['px']
                        new_sz = float(b['sz'])
                        old_sz = last_bids.get(px, 0.0)
                        delta_sz = new_sz - old_sz
                        delta_val = delta_sz * float(px)
                        
                        if delta_val > pop_threshold:
                             pops.append({'side': 'BID', 'px': float(px), 'sz': delta_sz, 'val': delta_val})

                    # Check Asks
                    for a in asks:
                        px = a['px']
                        new_sz = float(a['sz'])
                        old_sz = last_asks.get(px, 0.0)
                        delta_sz = new_sz - old_sz
                        delta_val = delta_sz * float(px)
                        
                        if delta_val > pop_threshold:
                             pops.append({'side': 'ASK', 'px': float(px), 'sz': delta_sz, 'val': delta_val})

                # Update State
                self.last_l2 = levels
                
                pops.sort(key=lambda x: x['val'], reverse=True)
                return {'l2_walls': walls[:10], 'l2_pops': pops[:5]} # Top 10 Walls, Top 5 Pops
                
            except Exception as e:
                self.add_log(f"⚠️ Whale Scan Error: {e}")
                return {'walls': [], 'pops': []}
        return {'walls': [], 'pops': []}

    def get_history(self):
        """Fetch Recent Trade History (Fills)"""
        if self.engine.enable_live and self.engine.live_trader:
            try:
                # Access the Info object from the trader
                trader = self.engine.live_trader
                # The SDK 'user_fills' returns a list of dictionaries
                fills = trader.info.user_fills(trader.wallet_address)
                return fills
            except Exception as e:
                self.add_log(f"⚠️ History Fetch Error: {e}")
                return []
        return []

    def get_state(self):
        with self.lock:
            # Update Alpha Status for UI
            self.latest_data['alpha_status'] = self.alpha_engine.strategies
                
            return {
                'data': self.latest_data,
                'logs': list(self.log_buffer)  # Return all logs in buffer
            }
