#!/usr/bin/env python3
"""
Simplified startup for Cloud Run - dashboard only
Trading engine runs in background thread within dashboard
"""

import sys
import os

# Set environment
os.environ['PYTHONUNBUFFERED'] = '1'

print("=" * 80)
print("🛡️ MANDALORIAN ENGINE - Cloud Run")
print("=" * 80)
print("\n🚀 Starting dashboard server...")

# Import and run dashboard directly
from dashboard_server import app, socketio, background_thread
import threading

# Start background thread for state updates
thread = threading.Thread(target=background_thread, daemon=True)
thread.start()

# Get port from environment
port = int(os.getenv('PORT', 5001))

print(f"\n📡 Dashboard starting on port {port}")
print("🔴 LIVE WebSocket Feed: Enabled\n")

# Run server
socketio.run(app, host='0.0.0.0', port=port, debug=False, use_reloader=False, log_output=True)
