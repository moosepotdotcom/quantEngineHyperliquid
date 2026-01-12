
import threading
import time
import json
import os
from hyperliquid.info import Info
from hyperliquid.utils import constants
from utils.logger import log_to_journal

class HyperLiquidSpy(threading.Thread):
    def __init__(self, refresh_rate=60):
        super().__init__()
        # Use Official SDK
        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
        
        self.refresh_rate = refresh_rate
        self.running = True
        self.latest_spy_data = None
        self.previous_positions = {} # Map address_coin -> size
        self.targets = []
        self._load_targets()
        self.daemon = True

    def _load_targets(self):
        try:
            path = os.path.join(os.path.dirname(__file__), '..', 'data', 'whales.json')
            if os.path.exists(path):
                with open(path, 'r') as f:
                    self.targets = json.load(f)
                print(f"🕵️‍♂️ Spy Bot: Loaded {len(self.targets)} targets from {path}")
            else:
                print("⚠️ Spy Bot: whales.json not found!")
                self.targets = []
        except Exception as e:
            print(f"⚠️ Spy Bot Config Error: {e}")

    def run(self):
        print(f"🕵️‍♂️ Starting HyperLiquid Spy...")
        while self.running:
            try:
                self._spy_on_targets()
                
                # Sleep loop
                for _ in range(self.refresh_rate):
                    if not self.running: break
                    time.sleep(1)
            except Exception as e:
                print(f"⚠️ Spy Bot Error: {e}")
                time.sleep(60)

    def _spy_on_targets(self):
        # Reload Periodically? Maybe not for now, just on start.
        for whale in self.targets:
            if not self.running: break
            address = whale['address']
            name = whale.get('name', 'Unknown')
            
            if address == "0x0000000000000000000000000000000000000000": continue

            try:
                # SDK Call
                user_state = self.info.user_state(address)
                self._analyze_state(address, name, user_state)
            except Exception as e:
                # print(f"Failed to spy on {name}: {e}")
                continue

    def _analyze_state(self, address, name, state):
        positions = state.get('assetPositions', [])
        
        for pos in positions:
            p = pos['position']
            coin = p['coin']
            size = float(p['szi'])
            entry_px = float(p.get('entryPx', 0))
            
            # Key for tracking
            key = f"{address}_{coin}"
            
            # Previous State
            prev_size = self.previous_positions.get(key, 0.0)
            
            # Detect Change
            if size != prev_size:
                # Significant change? (Ignore dust)
                if abs(size - prev_size) > 0.01: # Filter tiny dust
                    self._log_change(name, address, coin, prev_size, size, entry_px)
                
                # Update memory
                self.previous_positions[key] = size

    def _log_change(self, name, address, coin, old_size, new_size, price):
        short_addr = f"{address[:6]}..."
        
        action = "HOLD"
        if new_size > old_size:
            action = "ACCUMULATING" if new_size > 0 else "COVERING SHORT"
        elif new_size < old_size:
            action = "DUMPING" if new_size >= 0 else "SHORTING LEVERAGE"
            
        change = new_size - old_size
            
        emoji = "🕵️‍♂️"
        title = "WHALE SPY REPORT"
        details = f"- **Name**: {name}\n- **Address**: {short_addr}\n- **Asset**: {coin}\n- **Action**: {action}\n- **Change**: {change:+.4f}\n- **New Size**: {new_size:.4f}\n- **Avg Entry**: ${price:.2f}"
        
        log_to_journal(title, details, emoji)
        
        # Store for Main Loop
        self.latest_spy_data = f"{name} {action} {coin} ({change:+.2f})"
        
        # Persist to History
        self._save_activity_event(name, coin, action, change, new_size, price)

    def _save_activity_event(self, name, coin, action, change, size, price):
        try:
            event = {
                "timestamp": int(time.time()),
                "name": name,
                "coin": coin,
                "action": action,
                "change": float(f"{change:.4f}"),
                "size": float(f"{size:.4f}"),
                "price": float(f"{price:.2f}")
            }
            
            path = os.path.join(os.path.dirname(__file__), '..', 'data', 'whale_activity.json')
            
            history = []
            if os.path.exists(path):
                with open(path, 'r') as f:
                    try:
                        history = json.load(f)
                    except:
                        history = []
            
            # Append and Keep Last 1000
            history.append(event)
            if len(history) > 1000:
                history = history[-1000:]
                
            with open(path, 'w') as f:
                json.dump(history, f, indent=2)
                
        except Exception as e:
            print(f"⚠️ Failed to save whale activity: {e}")

    def stop(self):
        self.running = False
