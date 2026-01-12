#!/usr/bin/env python3
"""
MTF Scalper: Live Threshold Calibrator
Dynamically adjusts model confidence thresholds based on real-time trade outcomes
"""
import requests
import json
import time
import os
from datetime import datetime

# Configuration
WALLET_ADDRESS = "0xb01713a6fcdc9419f37db065f0274ea172e4689e"
API_URL = "https://api.hyperliquid.xyz"
MODEL_METADATA_PATH = 'training/models/mtf_scalper_5m_trio_metadata.json'

# Calibration Parameters
MIN_THRESHOLD = 0.55   # Don't go below this even if winning
MAX_THRESHOLD = 0.95   # Extreme selectivity
STEP_SIZE_UP = 0.05    # Increase threshold by this much on loss
STEP_SIZE_DOWN = 0.01  # Decrease threshold slowly on win
WIN_STREAK_REQUIREMENT = 3 # Need this many wins to decrease threshold once

class LiveCalibrator:
    def __init__(self):
        self.last_account_state = None
        self.win_streak = 0
        self.total_trades_monitored = 0
        
    def get_account_state(self):
        try:
            response = requests.post(
                f"{API_URL}/info",
                json={"type": "clearinghouseState", "user": WALLET_ADDRESS},
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"⚠️ Error fetching account state: {e}")
        return None

    def update_metadata_threshold(self, new_threshold):
        if not os.path.exists(MODEL_METADATA_PATH):
            print(f"❌ Metadata file not found: {MODEL_METADATA_PATH}")
            return
            
        with open(MODEL_METADATA_PATH, 'r') as f:
            metadata = json.load(f)
            
        old_threshold = metadata.get('target_precision_threshold', 0)
        metadata['target_precision_threshold'] = float(new_threshold)
        metadata['last_calibrated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        metadata['calibration_notes'] = f"Adjusted from {old_threshold:.4f} to {new_threshold:.4f}"
        
        with open(MODEL_METADATA_PATH, 'w') as f:
            json.dump(metadata, f, indent=4)
            
        print(f"✅ THRESHOLD UPDATED: {old_threshold:.4f} -> {new_threshold:.4f}")

    def get_last_fills(self):
        """Fetch recent trade fills from Hyperliquid"""
        try:
            response = requests.post(
                f"{API_URL}/info",
                json={"type": "userFills", "user": WALLET_ADDRESS},
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"⚠️ Error fetching fills: {e}")
        return []

    def run(self):
        print("🚀 Starting Live Threshold Calibrator...")
        print(f"📍 Monitoring Wallet: {WALLET_ADDRESS}")
        
        # Initial threshold from metadata
        with open(MODEL_METADATA_PATH, 'r') as f:
            metadata = json.load(f)
            current_threshold = metadata.get('target_precision_threshold', 0.85)

        last_fill_time = 0
        
        while True:
            fills = self.get_last_fills()
            if fills:
                # Find new closed trades (simplification: looking for most recent fill)
                latest_fill = fills[0] # Hyperliquid returns most recent first
                fill_time = latest_fill.get('time', 0)
                
                if fill_time > last_fill_time:
                    last_fill_time = fill_time
                    pnl = float(latest_fill.get('closedPnl', 0))
                    
                    if pnl < 0:
                        print(f"📉 LOSS DETECTED: ${pnl:.2f}. Increasing selectivity...")
                        current_threshold = min(MAX_THRESHOLD, current_threshold + STEP_SIZE_UP)
                        self.win_streak = 0
                    elif pnl > 0:
                        print(f"📈 WIN DETECTED: ${pnl:.2f}!")
                        self.win_streak += 1
                        if self.win_streak >= WIN_STREAK_REQUIREMENT:
                            current_threshold = max(MIN_THRESHOLD, current_threshold - STEP_SIZE_DOWN)
                            self.win_streak = 0
                    
                    self.update_metadata_threshold(current_threshold)

            time.sleep(30) # Poll every 30 seconds

if __name__ == "__main__":
    calibrator = LiveCalibrator()
    calibrator.run()
