# Cloud Scheduler Configuration for Health Monitoring

## Create Cloud Scheduler Job

```bash
# Create scheduler job to ping bot every 5 minutes
gcloud scheduler jobs create http bot-health-check \
    --location=us-central1 \
    --schedule="*/5 * * * *" \
    --uri="https://quant-engine-hl-live-mwgen67zoa-uc.a.run.app/health" \
    --http-method=GET \
    --attempt-deadline=30s \
    --max-retry-attempts=3 \
    --project=graphical-fort-427204-t3
```

## Update Cloud Run for Auto-Restart

```bash
# Update live bot with health check and auto-restart
gcloud run services update quant-engine-hl-live \
    --region=us-central1 \
    --project=graphical-fort-427204-t3 \
    --min-instances=1 \
    --max-instances=1 \
    --cpu-boost \
    --no-cpu-throttling
```

## Set Up Uptime Monitoring

```bash
# Create uptime check
gcloud monitoring uptime create bot-uptime-check \
    --display-name="Live Bot Uptime" \
    --resource-type=uptime-url \
    --monitored-resource=https://quant-engine-hl-live-mwgen67zoa-uc.a.run.app/health \
    --check-interval=5m \
    --timeout=10s \
    --project=graphical-fort-427204-t3
```

## Alert Policy

```bash
# Create alert when bot is down
gcloud alpha monitoring policies create \
    --notification-channels=CHANNEL_ID \
    --display-name="Bot Down Alert" \
    --condition-display-name="Bot Health Check Failed" \
    --condition-threshold-value=1 \
    --condition-threshold-duration=300s \
    --project=graphical-fort-427204-t3
```

## Telegram Alerts (Optional)

Set environment variables:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

---

## What This Does

1. **Health Check Every 5 Minutes** - Cloud Scheduler pings bot
2. **Min 1 Instance** - Bot always running (no cold starts)
3. **Uptime Monitoring** - Google Cloud tracks availability
4. **Auto-Restart** - Cloud Run restarts on failure
5. **Alerts** - Telegram notifications when bot is down

---

## Manual Commands

### Check if bot is running
```bash
curl https://quant-engine-hl-live-mwgen67zoa-uc.a.run.app/health
```

### Force restart
```bash
gcloud run services update quant-engine-hl-live \
    --region=us-central1 \
    --project=graphical-fort-427204-t3
```

### View logs
```bash
gcloud run services logs read quant-engine-hl-live \
    --region=us-central1 \
    --limit=100 \
    --project=graphical-fort-427204-t3
```
