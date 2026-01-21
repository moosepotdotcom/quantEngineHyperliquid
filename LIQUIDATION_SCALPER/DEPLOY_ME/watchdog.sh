#!/bin/bash
# Cloud Bot Watchdog - Ensures the bot stays running

BOT_DIR="/home/alifiyaa/bot"
LOG_FILE="$BOT_DIR/scalper.log"
PID_FILE="$BOT_DIR/bot.pid"

while true; do
    # Check if bot is running
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ! ps -p $PID > /dev/null 2>&1; then
            echo "$(date): Bot crashed (PID $PID not found). Restarting..." >> $BOT_DIR/watchdog.log
            rm -f "$PID_FILE"
        fi
    fi
    
    # Start bot if not running
    if [ ! -f "$PID_FILE" ]; then
        echo "$(date): Starting bot..." >> $BOT_DIR/watchdog.log
        cd "$BOT_DIR"
        nohup python3 main_cloud.py > "$LOG_FILE" 2>&1 &
        echo $! > "$PID_FILE"
        echo "$(date): Bot started with PID $(cat $PID_FILE)" >> $BOT_DIR/watchdog.log
    fi
    
    # Check every 30 seconds
    sleep 30
done
