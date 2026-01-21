#!/bin/bash
echo "Installing dependencies..."
pip install -r requirements.txt

echo "Starting Cloud Scalper in background..."
nohup python3 main_cloud.py > scalper.log 2>&1 &

echo "✅ Deployment Complete!"
echo "Main Logic: V2 Momentum ($500k Whale Threshold)"
echo "Logs: tail -f scalper.log"
