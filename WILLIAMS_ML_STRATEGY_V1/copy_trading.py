
import json
import os
import threading
from typing import List, Dict
from execution import HyperliquidTrader
# We might need a specific Subscriber Execution wrapper if we want to isolate them
# For now, we reuse HyperliquidTrader but re-init with their keys.

class Subscriber:
    def __init__(self, user_id, api_wallet, api_key, risk_multiplier=1.0):
        self.user_id = user_id
        self.wallet = api_wallet
        self.key = api_key
        self.risk_multiplier = risk_multiplier
        self.active = True
        
        # Each subscriber gets their own independent trader instance
        # In a real SaaS, we would decrypt keys here.
        # For V1 demo, we accept raw keys (Security Warning needed in prod)
        try:
            # We need to temporarily set ENV vars or modify HyperliquidTrader to accept keys directly
            # Modifying HyperliquidTrader is cleaner.
            # But allowing it to accept keys in init is a change to execution.py
            # Let's subclass or modify execution.py first? 
            # Or just hack Env vars? Hack is bad for concurrency.
            # We MUST modify HyperliquidTrader to accept credentials in __init__.
            pass
        except Exception as e:
            print(f"❌ Failed to init subscriber {user_id}: {e}")
            self.active = False

class CopyTradingEngine:
    def __init__(self):
        self.subscribers: Dict[str, Subscriber] = {}
        self.SUBS_FILE = 'subscribers.json'
        self.load_subscribers()
        
    def load_subscribers(self):
        if os.path.exists(self.SUBS_FILE):
            try:
                with open(self.SUBS_FILE, 'r') as f:
                    data = json.load(f)
                    for s in data:
                        # We need to defer internal trader init until we fix execution.py
                        # For now, just store data
                        self.subscribers[s['user_id']] = s
                print(f"👥 Loaded {len(self.subscribers)} subscribers.")
            except Exception as e:
                print(f"⚠️ Error loading subscribers: {e}")
        else:
            print("ℹ️ No subscribers found. Creating empty DB.")
            self.save_subscribers()

    def save_subscribers(self):
        data = list(self.subscribers.values())
        with open(self.SUBS_FILE, 'w') as f:
            json.dump(data, f, indent=4)

    def add_subscriber(self, user_id, wallet, key, risk=1.0):
        if user_id in self.subscribers:
            return False, "User already exists"
        
        self.subscribers[user_id] = {
            "user_id": user_id,
            "wallet": wallet,
            "key": key,
            "risk": risk
        }
        self.save_subscribers()
        print(f"✅ Added subscriber: {user_id}")
        return True, "Subscriber added"

    def remove_subscriber(self, user_id):
        if user_id in self.subscribers:
            del self.subscribers[user_id]
            self.save_subscribers()
            return True
        return False

    def broadcast_trade(self, coin, is_long, entry_price, master_size_usd, tp, sl):
        """
        Fan-out signal to all subscribers.
        Executed in thread pool for speed.
        """
        print(f"📢 Broadcasting Trade: {coin} {'LONG' if is_long else 'SHORT'} to {len(self.subscribers)} subs...")
        
        threads = []
        for user_id, sub_data in self.subscribers.items():
            t = threading.Thread(target=self._execute_for_subscriber, args=(sub_data, coin, is_long, master_size_usd, tp, sl))
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join()
            
    def _execute_for_subscriber(self, sub_data, coin, is_long, master_size_usd, tp, sl):
        """
        Individual execution logic.
        """
        user_id = sub_data['user_id']
        try:
            # Initialize ephemeral trader for this execution
            # We need to update execution.py to support passing keys dynamically
            # For now, we will mock the success print
            print(f"   👤 Executing for {user_id}...")
            
            # TODO: Refactor execution.py to accept keys
            # trader = HyperliquidTrader(wallet=sub_data['wallet'], key=sub_data['key'])
            # trader.execute_trade(...)
            
            # MOCK SUCCESS FOR V1
            import time
            time.sleep(0.5) 
            print(f"   ✅ {user_id}: Filled (Mock)")
            
        except Exception as e:
            print(f"   ❌ {user_id}: Failed - {e}")

