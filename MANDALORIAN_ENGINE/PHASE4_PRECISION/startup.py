#!/usr/bin/env python3
"""
Startup script for Cloud Run deployment
Runs both trading engine and dashboard server in parallel
"""

import subprocess
import sys
import time
import signal
import os

processes = []

def signal_handler(sig, frame):
    """Handle shutdown gracefully"""
    print("\n🛑 Shutting down Mandalorian Engine...")
    for p in processes:
        p.terminate()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def main():
    print("=" * 80)
    print("🛡️ MANDALORIAN ENGINE - Cloud Run Deployment")
    print("=" * 80)
    print("\n🚀 Starting services...")
    
    # Start trading engine
    print("\n📊 Starting Live Paper Trading Engine...")
    engine_process = subprocess.Popen(
        [sys.executable, "live_paper_trading.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )
    processes.append(engine_process)
    
    # Give engine time to initialize
    time.sleep(5)
    
    # Start dashboard server
    print("\n🌐 Starting Dashboard Server...")
    dashboard_process = subprocess.Popen(
        [sys.executable, "dashboard_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # Merge stderr into stdout
        universal_newlines=True,
        bufsize=1
    )
    processes.append(dashboard_process)
    
    print("\n✅ All services started!")
    print(f"📡 Dashboard available on port {os.getenv('PORT', 5001)}")
    print("\n🔴 LIVE WebSocket Feed: Enabled")
    print("=" * 80)
    
    # Stream logs from both processes
    try:
        while True:
            # Check if processes are still running
            for p in processes:
                if p.poll() is not None:
                    print(f"\n⚠️ Process {p.pid} exited with code {p.returncode}")
                    return p.returncode
            
            # Stream output
            for p in processes:
                line = p.stdout.readline()
                if line:
                    print(line.strip())
            
            time.sleep(0.1)
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    sys.exit(main())
