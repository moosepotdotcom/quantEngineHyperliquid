
import time
import uuid

class PaperExecutionEngine:
    """
    Mock Execution Engine for Paper Trading.
    Simulates fills, PnL, and position management without API calls.
    """
    def __init__(self, initial_balance=10000.0):
        self.balance = initial_balance
        self.active_positions = {} # {coin: {entry, size, type, tp, sl, ts}}
        self.leverage = 3
        self.daily_pnl = 0.0
        self.emergency_stop = False
        
        # Logging Setup
        import logging
        logging.basicConfig(
            filename='paper_trading.log',
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger()
        
        self.log(f"📝 Paper Trading Engine Initialized. Balance: ${self.balance:.2f}")

        # Database Setup
        try:
            from auth import SessionLocal
            self.db = SessionLocal()
            self.log("✅ Connected to SQLite Database for History")
        except Exception as e:
            self.log(f"❌ Database Connection Failed: {e}")
            self.db = None

    def _save_to_db(self, record):
        if not self.db: return
        try:
            from auth import Trade
            trade = Trade(
                id=record['id'],
                coin=record['coin'],
                side=record['type'],
                entry_price=record['entry'],
                exit_price=record['exit'],
                size=record['size'],
                pnl_usd=record['pnl_usd'],
                reason=record['reason'],
                ts_entry=record['ts_entry'],
                ts_exit=record['ts_exit']
            )
            self.db.add(trade)
            self.db.commit()
            print(f"💾 Trade Saved to DB: {record['id']}")
        except Exception as e:
            print(f"❌ DB Save Error: {e}")

    def log(self, msg):
        print(msg)
        self.logger.info(msg)

    def get_account_info(self):
        """Mock account info in Hyperliquid format"""
        # We need current prices to calc unrealized PnL.
        # But this method is usually called by API which just wants list.
        # We can set PnL to 0 for now or fetch? Fetching slows down API.
        # Let's set PnL to 0 or estimates.
        
        hl_positions = []
        for coin, pos in self.active_positions.items():
            size = pos['size']
            if pos['type'] == 'SHORT': size = -size
            
            hl_positions.append({
                "coin": coin,
                "entryPx": str(pos['entry']),
                "szi": str(size),
                "unrealizedPnl": "0.0", # Todo: update with real price
                "returnOnEquity": "0.0",
                # Extra fields for Frontend
                "tp": pos.get('tp'),
                "sl": pos.get('sl')
            })
            
        return {
            'balance': self.balance,
            'positions': hl_positions 
        }

    def calculate_order_size(self, price):
        """Calculate size based on leverage"""
        buying_power = self.balance * self.leverage
        return buying_power / price

    def execute_trade(self, coin, is_long, size_usd, tp_price, sl_price):
        """Simulate trade execution"""
        if self.emergency_stop: 
            print("🛑 Paper Trade Rejected: Emergency Stop Active")
            return False

        print(f"\n📝 PAPER EXECUTION: {coin} {'LONG' if is_long else 'SHORT'}")
        print(f"   Size: ${size_usd:.2f}")
        print(f"   Entry: Market Price (Simulated)")
        
        # In a real scenario we'd fetch price, here we trust the logic passed logical entry?
        # NO, execute_trade DOES NOT receive entry price. It receives TP/SL.
        # We need the current price to record entry.
        # Let's assume the caller logic has fresh price or we fetch it?
        # The caller (live_trader) has the price from the signal.
        # But execute_trade signature in execution.py doesn't take entry price.
        # It fetches it inside.
        
        # We need a way to get current price. 
        # For simplicity, we can infer it from TP/SL or passing it would be better.
        # But we must match interface.
        # Let's assume the callee doesn't fetch, mock it? 
        # No, we need real price data to be realistic. 
        # WE can fetch it here using public API or just use the mid price logic from execution.py
        
        # FOR PAPER MODE: We will just use the TP/SL to reverse engineer entry 
        # OR better: Add `current_price` to argument if possible?
        # Changing interface breaks compatibility.
        # Let's just fetch it quickly using requests or similar? 
        # Actually `execution.py` fetches it.
        # Let's copy the fetch logic.
        
        entry_price = self._fetch_mock_price(coin)
        
        size_coins = size_usd / entry_price
        
        position = {
            'id': str(uuid.uuid4()),
            'coin': coin,
            'type': 'LONG' if is_long else 'SHORT',
            'entry': entry_price,
            'size': size_coins,
            'size_usd': size_usd,
            'tp': tp_price,
            'sl': sl_price,
            'ts': time.time()
        }
        
        self.active_positions[coin] = position
        print(f"✅ Paper Position Opened: {coin} @ ${entry_price:.4f}")
        return True

    def _fetch_mock_price(self, coin):
        """Fetch real price for paper fill"""
        import requests
        url = "https://api.hyperliquid.xyz/info"
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(url, json={"type": "allMids"}, headers=headers, timeout=5)
            data = response.json()
            return float(data.get(coin, 0))
        except:
            return 0.0

    def _record_close(self, coin, exit_price, reason):
        pos = self.active_positions[coin]
        
        # Calc PnL
        if pos['type'] == 'LONG':
            pnl_pct = (exit_price - pos['entry']) / pos['entry']
            points = exit_price - pos['entry']
        else:
            pnl_pct = (pos['entry'] - exit_price) / pos['entry']
            points = pos['entry'] - exit_price
            
        pnl_usd = pnl_pct * pos['size_usd'] * self.leverage
        
        record = {
            "id": pos.get('id', str(uuid.uuid4())),
            "coin": coin,
            "type": pos['type'],
            "entry": pos['entry'],
            "exit": exit_price,
            "size": pos['size'],
            "pnl_usd": pnl_usd,
            "pnl_points": points,
            "reason": reason,
            "ts_entry": pos['ts'],
            "ts_exit": time.time()
        }
        
        
        self._save_to_db(record)
        
        # Update Balance
        self.balance += pnl_usd
        self.daily_pnl += pnl_usd
        
        return pnl_usd

    def check_positions(self, current_price_map):
        """
        Check paper positions against current prices.
        Called by the strategy loop.
        """
        closed_coins = []
        for coin, pos in self.active_positions.items():
            current_price = current_price_map.get(coin)
            if not current_price: continue

            # Check TP/SL
            hit_tp = False
            hit_sl = False
            
            if pos['type'] == 'LONG':
                if current_price >= pos['tp']: hit_tp = True
                if current_price <= pos['sl']: hit_sl = True
            else:
                if current_price <= pos['tp']: hit_tp = True
                if current_price >= pos['sl']: hit_sl = True
                
            if hit_tp:
                pnl = self._record_close(coin, current_price, "TP")
                print(f"🎯 PAPER TP HIT: {coin} (+${pnl:.2f})")
                closed_coins.append(coin)
            elif hit_sl:
                pnl = self._record_close(coin, current_price, "SL")
                print(f"🛑 PAPER SL HIT: {coin} (-${abs(pnl):.2f})")
                closed_coins.append(coin)
        
        for c in closed_coins:
            del self.active_positions[c]

    def close_position(self, coin):
        """Manual close"""
        if coin in self.active_positions:
            # We need current price to calc PnL.
            # For Manual close, we fetch price.
            price = self._fetch_mock_price(coin)
            pnl = self._record_close(coin, price, "MANUAL")
            print(f"👋 Manual Close: {coin} PnL: ${pnl:.2f}")
            del self.active_positions[coin]
            return True
        return False

    def close_all(self):
        """Panic close"""
        coins = list(self.active_positions.keys())
        for c in coins:
            self.close_position(c)
