#!/usr/bin/env python3
"""
☁️ CLOUD BOT MONITOR (JSON EDITION)
Streams live logs using robust JSON parsing to prevent formatting errors.
"""
import subprocess
import os
import sys
import time
import json

SERVICE_NAME = "quant-engine-hl"
REGION = "us-central1"
PROJECT = "graphical-fort-427204-t3"

def stream_logs():
    print("\n" + "☁️"*35)
    print(f"CONNECTING TO CLOUD RUN: {SERVICE_NAME}")
    print("☁️"*35 + "\n")
    print("Fetching live logs... (Press Ctrl+C to stop)\n")
    
    seen_ids = set()
    
    try:
        while True:
            # Run gcloud command with JSON output
            cmd = [
                "gcloud", "run", "services", "logs", "read", SERVICE_NAME,
                "--region", REGION,
                "--project", PROJECT,
                "--limit", "30",
                "--format", "json"
            ]
            
            result = subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True,
                env=dict(os.environ, CLOUDSDK_CORE_DISABLE_PROMPTS='1')
            )
            
            if result.returncode != 0:
                time.sleep(3)
                continue

            try:
                # Gcloud returns a JSON array
                logs = json.loads(result.stdout)
            except json.JSONDecodeError:
                time.sleep(1)
                continue
                
            # Process logs (they come in reverse chronological order usually, but we sort to be safe)
            # Create a list of (timestamp, text_payload)
            clean_logs = []
            
            for log in logs:
                try:
                    ts = log.get('timestamp', '')
                    msg = log.get('textPayload', '')
                    
                    if not msg: continue # Skip empty messages
                    
                    # 🛡️ NOISE FILTER (Aggressive)
                    # Filter out low-level library noise
                    if any(x in msg for x in ["limit=", "length:", "[AR]", "127.0.0.1", "169.254", "6 cols", "gcloud"]):
                        continue
                    
                    clean_logs.append((ts, msg))
                except:
                    continue

            # Sort by timestamp
            clean_logs.sort(key=lambda x: x[0])

            # Display
            for ts, msg in clean_logs:
                unique_id = f"{ts}-{msg}"
                if unique_id in seen_ids:
                    continue
                
                seen_ids.add(unique_id)
                if len(seen_ids) > 2000: seen_ids.clear()

                # Format Time (H:M:S)
                try:
                    time_part = ts.split('T')[1][:8]
                except:
                    time_part = "LIVE"

                # 🎨 FORMATTING
                if "GET /health" in msg:
                    print(f"[{time_part}] 💓 Pulse Check: OK")
                elif "Quant Engine" in msg:
                    print(f"\n[{time_part}] 🚀 {msg}")
                elif "Traceback" in msg or "Error" in msg:
                    print(f"[{time_part}] ❌ {msg}")
                elif "Confidence:" in msg:
                     # e.g. Confidence: 0.65 (Target: 0.65)
                    print(f"[{time_part}] 📈 {msg}")
                elif "MTF SCALPER" in msg or "WINNER HUNTER" in msg:
                    print(f"[{time_part}] 🧠 {msg}")
                elif "Trade" in msg or "SIGNAL" in msg or "orders" in msg:
                    print(f"[{time_part}] 💰 {msg}")
                elif any(c.isalpha() for c in msg):
                    print(f"[{time_part}] {msg}")

            time.sleep(3)

    except KeyboardInterrupt:
        print("\n\n🔌 Disconnected.")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    stream_logs()
