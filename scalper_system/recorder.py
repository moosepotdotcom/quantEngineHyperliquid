"""
💾 CSV RECORDER
Persists live feed events to disk for backtesting.
"""
import csv
import os
import logging
from scalper_system import config

logger = logging.getLogger("RECORDER")

class CSVRecorder:
    def __init__(self):
        self.filepath = config.LIQ_DATA_FILE
        self._init_file()
        
    def _init_file(self):
        # Create dir if needed
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        
        # Write header if new
        if not os.path.exists(self.filepath):
            with open(self.filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'symbol', 'type', 'price', 'size', 'usd', 'user'])
                
    def on_event(self, event):
        try:
            with open(self.filepath, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    event['timestamp'].isoformat(),
                    event['symbol'],
                    event['type'],
                    event['price'],
                    event['size'],
                    event['usd'],
                    event['user']
                ])
        except Exception as e:
            logger.error(f"Write Error: {e}")
