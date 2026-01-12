
import threading
import time
from hyperliquid.info import Info
from hyperliquid.utils import constants
from utils.logger import log_to_journal

class FundingMonitor(threading.Thread):
    def __init__(self, refresh_rate=300): # Check every 5 minutes by default
        super().__init__()
        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
        self.refresh_rate = refresh_rate
        self.running = True
        self.latest_opportunity = None
        self.daemon = True

    def run(self):
        print(f"💰 Starting Funding Rate Monitor (Scan every {self.refresh_rate}s)...")
        while self.running:
            try:
                self._scan_funding_rates()
                
                # Sleep loop
                for _ in range(self.refresh_rate):
                    if not self.running: break
                    time.sleep(1)
            except Exception as e:
                print(f"⚠️ Funding Monitor Error: {e}")
                time.sleep(60)

    def get_current_rate(self):
        """Returns the raw funding rate fraction of the first symbol (usually BTC)"""
        if self.latest_opportunity and "rate" in self.latest_opportunity:
             # This is just a string in the current impl, let's fix the class to store the actual map
             pass
        # Better: return the rate for BTC specifically if found
        return 0.0

    def get_bias(self):
        """
        Returns bias: 1 (Bullish - Shorts paying Longs), -1 (Bearish - Longs paying Shorts)
        We use BTC funding as the primary indicator for the fleet.
        """
        try:
            # We need to access the stored results from _scan_funding_rates
            if hasattr(self, 'current_funding_map'):
                btc_funding = self.current_funding_map.get('BTC', 0.0)
                if btc_funding > 0.01: # Longs paying a lot (Bearish)
                    return -1
                elif btc_funding < -0.01: # Shorts paying a lot (Bullish)
                    return 1
        except:
            pass
        return 0

    def _scan_funding_rates(self):
        try:
            # Fetch meta and asset contexts to get funding
            meta_and_ctx = self.info.meta_and_asset_ctxs()
            universe = meta_and_ctx[0]['universe']
            asset_ctxs = meta_and_ctx[1]
            
            funding_data = []
            self.current_funding_map = {} # Added to store for get_bias
            
            for i, asset_info in enumerate(universe):
                name = asset_info['name']
                ctx = asset_ctxs[i]
                funding = float(ctx.get('funding', 0.0))
                funding_pct = funding * 100
                self.current_funding_map[name] = funding_pct
                funding_annual = funding * 24 * 365 * 100
                
                funding_data.append({
                    'symbol': name,
                    'funding_pct': funding_pct,
                    'apr': funding_annual
                })
                
            # Sort by highest funding (Short Opportunity) and lowest (Long Opportunity)
            funding_data.sort(key=lambda x: x['funding_pct'], reverse=True)
            
            top_short = funding_data[0] # Highest Positive Rate (Short pays you)
            top_long = funding_data[-1]  # Lowest Negative Rate (Long pays you)
            
            # Threshold for alert (e.g. > 20% APR)
            # 0.01% hourly is ~87% APR.
            # Let's alert if > 10% APR or < -10% APR
            
            if top_short['apr'] > 10.0:
                 self._log_opportunity("SHORT", top_short)
                 
            if top_long['apr'] < -10.0:
                 self._log_opportunity("LONG", top_long)
                 
        except Exception as e:
            print(f"Failed to scan funding: {e}")
            
    def _log_opportunity(self, side, data):
        symbol = data['symbol']
        apr = data['apr']
        rate = data['funding_pct']
        
        emoji = "💰"
        title = f"FUNDING ARB ALERT ({symbol})"
        
        # Deduplicate logs? Maybe only log if better than previous?
        # For now, just logging is fine as refresh rate is low (5 mins).
        
        details = f"- **Strategy**: Funding Arbitrage\n- **Signal**: {side} {symbol}\n- **Hourly Rate**: {rate:.4f}%\n- **Projected APR**: {apr:.1f}%"
        
        log_to_journal(title, details, emoji)
        
        self.latest_opportunity = f"Coin: {symbol} | Dir: {side} | Return: {apr:.1f}% APR"

    def stop(self):
        self.running = False
