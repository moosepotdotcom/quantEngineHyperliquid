#!/bin/bash
# Health Monitor Script
# Checks if bot is running and restarts if needed

BOT_URL="https://quant-engine-hl-live-mwgen67zoa-uc.a.run.app/health"
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID}"

check_health() {
    response=$(curl -s -o /dev/null -w "%{http_code}" "$BOT_URL" -m 10)
    echo "$response"
}

send_alert() {
    message="$1"
    if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${TELEGRAM_CHAT_ID}" \
            -d "text=🚨 Bot Alert: ${message}"
    fi
    echo "$(date): $message"
}

# Check health
status=$(check_health)

if [ "$status" != "200" ]; then
    send_alert "Live bot is DOWN! Status code: $status. Attempting restart..."
    
    # Trigger Cloud Run to restart by making a request
    curl -s "$BOT_URL" > /dev/null
    
    # Wait and check again
    sleep 10
    new_status=$(check_health)
    
    if [ "$new_status" == "200" ]; then
        send_alert "Live bot RECOVERED after restart. Status: OK"
    else
        send_alert "Live bot FAILED to recover. Manual intervention needed!"
    fi
else
    echo "$(date): Bot is healthy (Status: $status)"
fi
