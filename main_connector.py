#!/usr/bin/env python3
"""
🔌 MAIN CONNECTOR - Logic Bridge & Orchestrator
Connects isolated model engines to the market data feed and execution layer.
"""

import os
import sys
import time
import importlib
import pandas as pd
from datetime import datetime
from typing import Dict, List

# Ensure we can import from core and utils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))

from core.base_engine import BaseModelEngine
from utils.fetch_data import fetch_live_data
from utils.trade_logger import get_logger
from model_engines.mtf_scalper_v2.engine import MTFScalperV2Engine
from model_engines.winner_hunter_1h.engine import WinnerHunter1HEngine
from model_engines.mtf_scalper_v3.engine import MTFScalperV3Engine

class MainConnector:
    def __init__(self):
        self.models = []
        self._register_models()
        self.data_store = {}
        self.logger = get_logger()
        self.is_running = False
        
    def _register_models(self):
        """Register all available model engines."""
        # 1. MTF Scalper V2
        self.models.append(MTFScalperV2Engine())
        
        # 2. Winner Hunter (Benchmark)
        self.models.append(WinnerHunter1HEngine())
        
        # 3. MTF Scalper V3 (New Production)
        self.models.append(MTFScalperV3Engine())
        
        print(f"🔌 Connector: Registered {len(self.models)} engines")
        
        # Shared State
        self.required_timeframes = set()
        
        # Initialize Hyperliquid Info (if needed globally)
        try:
            from hyperliquid.info import Info
            from hyperliquid.utils import constants
            self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
            print("   ✅ Hyperliquid Info initialized", flush=True)
        except Exception:
            self.info = None

    def discover_and_load_models(self):
        """Dynamically finds and initializes model engines from /model_engines"""
        engines_dir = os.path.join(os.path.dirname(__file__), 'model_engines')
        
        print("\n🔎 Discovering Model Engines...")
        
        if not os.path.exists(engines_dir):
            print(f"   ⚠️ Directory not found: {engines_dir}")
            return

        # Simple directory walk
        for item in os.listdir(engines_dir):
            model_path = os.path.join(engines_dir, item)
            if os.path.isdir(model_path) and not item.startswith('__'):
                # Try to import engine.py
                try:
                    # Construct module path: model_engines.folder_name.engine
                    module_name = f"model_engines.{item}.engine"
                    module = importlib.import_module(module_name)
                    
                    # Look for a class that inherits from BaseModelEngine
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, BaseModelEngine) and 
                            attr is not BaseModelEngine):
                            
                            # Instantiate and initialize
                            engine_instance = attr()
                            print(f"   🚀 Initializing {engine_instance.name}...")
                            
                            if engine_instance.initialize():
                                self.models.append(engine_instance)
                                self.required_timeframes.update(engine_instance.get_required_timeframes())
                                print(f"      ✅ Loaded successfully")
                            else:
                                print(f"      ❌ Initialization failed")
                            break
                except ImportError as e:
                    print(f"   ⚠️ Could not load {item}: {e}")
                except Exception as e:
                    print(f"   ❌ Error loading {item}: {e}")

        print(f"\n✅ Total Models Loaded: {len(self.models)}")
        print(f"   🕒 Required Timeframes: {self.required_timeframes}\n")

    def fetch_market_data(self) -> Dict[str, pd.DataFrame]:
        """Fetches all required dataframes"""
        data = {}
        # Simple fetching loop (could be async in future)
        # Using the existing quant_engine.py fetch logic logic adapted to utils
        # Note: utils/fetch_data.py has fetch_live_data, but quant_engine had a class method with caching.
        # For now, we will verify if utils/fetch_data.py is sufficient or if we need a DataProvider class.
        
        # Temporarily instantiating utils.fetch_data logic or reusing a helper
        # Since quant_engine.py had a specific caching implementation, 
        # let's assume valid util exists or we use a simple wrapper here for now.
        
        # We will use the fetch_live_data from utils if compatible, otherwise we reimplement simple fetch
        # The prompt implies we should assume standard utils. 
        # Let's import fetch_live_data from utils.fetch_data
        
        from utils.fetch_data import fetch_live_data
        
        for tf in self.required_timeframes:
            # We assume a standard limit of 500 candles is sufficient for most
            # Some models might need more, but let's start standard.
            df = fetch_live_data(symbol="BTC", interval=tf, limit=500)
            if df is not None and not df.empty:
                data[tf] = df
            else:
                print(f"   ⚠️ Failed to fetch {tf} data")
        
        return data

    def run_sandbox_loop(self):
        """Main execution loop (Sandbox Mode)"""
        print("🎢 Starting Sandbox Loop...")
        self.is_running = True
        
        while self.is_running:
            try:
                print(f"\n⏰ Tick: {datetime.now().strftime('%H:%M:%S')}")
                
                # 1. Fetch Data
                market_data = self.fetch_market_data()
                
                # Check if we have all needed data
                if len(market_data) < len(self.required_timeframes):
                    print("   ⚠️ Incomplete data, skipping tick")
                    time.sleep(10)
                    continue

                # 2. Query Models
                signals = []
                for model in self.models:
                    try:
                        sig = model.analyze(market_data)
                        if sig:
                            signals.append(sig)
                            print(f"   ✨ {model.name} Signal: {sig.get('direction')} ({sig.get('confidence'):.2f})")
                        else:
                            # print(f"   💤 {model.name}: Neutral")
                            pass
                    except Exception as e:
                        print(f"   ❌ Error in {model.name}: {e}")

                # 3. Aggregation & Execution (Simple Pass-through for now)
                for sig in signals:
                    self.execute_trade_sandbox(sig)
                
                # Wait
                print("   💤 Sleeping 60s...")
                time.sleep(60)

            except KeyboardInterrupt:
                print("\n🛑 Stopping...")
                self.is_running = False
            except Exception as e:
                print(f"   ❌ Loop Error: {e}")
                time.sleep(10)

    def execute_trade_sandbox(self, signal):
        """Simulate trade execution"""
        print(f"\n{'='*60}")
        print(f"🚀 EXECUTING TRADE ({signal['direction']})")
        print(f"   Model: {signal['model']}")
        print(f"   Price: {signal['price']}")
        print(f"   Conf : {signal['confidence']:.2%}")
        print(f"{'='*60}\n")
        
        # Feedback loop simulation
        # In real engine, this would happen after trade close
        pass

if __name__ == "__main__":
    connector = MainConnector()
    connector.discover_and_load_models()
    connector.run_sandbox_loop()
